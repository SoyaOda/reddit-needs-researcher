from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import base64
import json
import os
import time

from .models import JsonValue, SearchSort, TimeFilter


TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_BASE_URL = "https://oauth.reddit.com"
REDDIT_BASE_URL = "https://www.reddit.com"
TOKEN_EXPIRY_SAFETY_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 30
LOW_REMAINING_REQUEST_THRESHOLD = 1.0
MAX_AUTOMATIC_SLEEP_SECONDS = 120.0


class RedditApiError(RuntimeError):
    """Raised when Reddit API access fails."""


@dataclass
class RateLimitState:
    used: float | None = None
    remaining: float | None = None
    reset_seconds: float | None = None


@dataclass
class OAuthToken:
    access_token: str
    expires_at_monotonic: float


class RedditClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        user_agent: str,
        min_seconds_between_requests: float,
    ) -> None:
        if not client_id:
            raise ValueError("client_id is required")
        if not client_secret:
            raise ValueError("client_secret is required")
        if not user_agent:
            raise ValueError("user_agent is required")
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_agent = user_agent
        self._min_seconds_between_requests = min_seconds_between_requests
        self._token: OAuthToken | None = None
        self._last_request_at = 0.0
        self.rate_limit = RateLimitState()

    @classmethod
    def from_env(cls, *, min_seconds_between_requests: float) -> "RedditClient":
        client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
        user_agent = os.environ.get("REDDIT_USER_AGENT", "").strip()
        missing = [
            name
            for name, value in (
                ("REDDIT_CLIENT_ID", client_id),
                ("REDDIT_CLIENT_SECRET", client_secret),
                ("REDDIT_USER_AGENT", user_agent),
            )
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise RedditApiError(f"missing required environment variables: {joined}")
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            min_seconds_between_requests=min_seconds_between_requests,
        )

    def search_subreddit(
        self,
        *,
        subreddit: str,
        query: str,
        sort: SearchSort,
        time_filter: TimeFilter,
        limit: int,
        after: str | None = None,
    ) -> dict[str, JsonValue]:
        params: dict[str, str | int] = {
            "q": query,
            "restrict_sr": "1",
            "sort": sort,
            "t": time_filter,
            "limit": limit,
            "raw_json": "1",
        }
        if after is not None:
            params["after"] = after
        return self.get_json(f"/r/{subreddit}/search", params=params)

    def subreddit_listing(
        self,
        *,
        subreddit: str,
        sort: str,
        time_filter: TimeFilter,
        limit: int,
        after: str | None = None,
    ) -> dict[str, JsonValue]:
        params: dict[str, str | int] = {
            "limit": limit,
            "raw_json": "1",
        }
        if sort in {"top", "controversial"}:
            params["t"] = time_filter
        if after is not None:
            params["after"] = after
        return self.get_json(f"/r/{subreddit}/{sort}", params=params)

    def comments(
        self,
        *,
        subreddit: str,
        submission_id: str,
        limit: int,
        sort: str,
        depth: int,
    ) -> list[JsonValue]:
        params: dict[str, str | int] = {
            "limit": limit,
            "sort": sort,
            "depth": depth,
            "raw_json": "1",
        }
        value = self.get_json_value(
            f"/r/{subreddit}/comments/{submission_id}",
            params=params,
        )
        if not isinstance(value, list):
            raise RedditApiError("comments response must be a list")
        return value

    def get_json(self, path: str, *, params: Mapping[str, str | int]) -> dict[str, JsonValue]:
        value = self.get_json_value(path, params=params)
        if not isinstance(value, dict):
            raise RedditApiError(f"expected object response for {path}")
        return value

    def get_json_value(self, path: str, *, params: Mapping[str, str | int]) -> JsonValue:
        token = self._get_access_token()
        query = urlencode(params)
        url = f"{OAUTH_BASE_URL}{path}.json"
        if query:
            url = f"{url}?{query}"
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self._user_agent,
            "Accept": "application/json",
        }
        body, response_headers = self._request("GET", url, headers=headers, body=None)
        self._update_rate_limit(response_headers)
        self._sleep_if_rate_limit_low()
        return decode_json(body)

    def _get_access_token(self) -> str:
        current = time.monotonic()
        if self._token is not None and self._token.expires_at_monotonic > current:
            return self._token.access_token

        credentials = f"{self._client_id}:{self._client_secret}".encode("utf-8")
        encoded_credentials = base64.b64encode(credentials).decode("ascii")
        body = urlencode({"grant_type": "client_credentials"}).encode("utf-8")
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "User-Agent": self._user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        response_body, _headers = self._request("POST", TOKEN_URL, headers=headers, body=body)
        payload = decode_json(response_body)
        if not isinstance(payload, dict):
            raise RedditApiError("token response must be an object")
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not isinstance(access_token, str) or not access_token:
            raise RedditApiError("token response did not include access_token")
        if not isinstance(expires_in, int | float):
            raise RedditApiError("token response did not include numeric expires_in")
        expires_at = time.monotonic() + float(expires_in) - TOKEN_EXPIRY_SAFETY_SECONDS
        self._token = OAuthToken(access_token=access_token, expires_at_monotonic=expires_at)
        return access_token

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
    ) -> tuple[bytes, Mapping[str, str]]:
        self._enforce_min_interval()
        request = Request(url, data=body, method=method, headers=dict(headers))
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                self._last_request_at = time.monotonic()
                return response.read(), response.headers
        except HTTPError as error:
            self._last_request_at = time.monotonic()
            detail = error.read().decode("utf-8", errors="replace")
            if error.code == 429:
                raise RedditApiError(f"reddit rate limit exceeded: HTTP 429 {detail}") from error
            raise RedditApiError(f"reddit api request failed: HTTP {error.code} {detail}") from error
        except URLError as error:
            self._last_request_at = time.monotonic()
            raise RedditApiError(f"reddit api request failed: {error.reason}") from error

    def _enforce_min_interval(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait_seconds = self._min_seconds_between_requests - elapsed
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def _update_rate_limit(self, headers: Mapping[str, str]) -> None:
        self.rate_limit = RateLimitState(
            used=parse_float_header(headers, "X-Ratelimit-Used"),
            remaining=parse_float_header(headers, "X-Ratelimit-Remaining"),
            reset_seconds=parse_float_header(headers, "X-Ratelimit-Reset"),
        )

    def _sleep_if_rate_limit_low(self) -> None:
        remaining = self.rate_limit.remaining
        reset_seconds = self.rate_limit.reset_seconds
        if remaining is None or reset_seconds is None:
            return
        if remaining > LOW_REMAINING_REQUEST_THRESHOLD or reset_seconds <= 0:
            return
        if reset_seconds > MAX_AUTOMATIC_SLEEP_SECONDS:
            raise RedditApiError(
                "reddit rate limit remaining is low and reset window is too long "
                f"for automatic sleep: {reset_seconds:.1f}s"
            )
        time.sleep(reset_seconds + 1.0)


def parse_float_header(headers: Mapping[str, str], name: str) -> float | None:
    raw_value = headers.get(name)
    if raw_value is None:
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def decode_json(body: bytes) -> JsonValue:
    try:
        decoded = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise RedditApiError("reddit response was not valid JSON") from error
    return normalize_json(decoded)


def normalize_json(value: object) -> JsonValue:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list):
        return [normalize_json(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, JsonValue] = {}
        for key, item in value.items():
            if isinstance(key, str):
                normalized[key] = normalize_json(item)
        return normalized
    return str(value)

