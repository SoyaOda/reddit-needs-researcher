# Reddit Data API Access Request Draft

Current official route checked on 2026-06-09:

- Form: `https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164`
- Role: `I’m a developer`
- Inquiry: `I’m a developer and want to build a Reddit App that does not work in the Devvit ecosystem.`

## Fields To Provide From User

- Email address:
- Reddit account name:
- Source code or platform URL:
- Bot/App operating username, if any:

## Suggested Form Values

### Subject of inquiry

Data API access request for external local Reddit needs researcher prototype

### Details of inquiry

I am requesting Reddit Data API access for an external local prototype named `reddit-needs-researcher`.

The app is a read-only, low-volume local developer tool that collects public Reddit posts and comments from a small, explicitly configured set of subreddits and search queries. The purpose is product-discovery analysis: identifying recurring user pain points, unmet needs, and follow-up discovery questions from public discussions.

The app does not post, comment, vote, send messages, modify Reddit content, access private messages, access private subreddits, or automate any user interaction on Reddit. It will use OAuth, a unique descriptive User-Agent, and will monitor Reddit's `X-Ratelimit-*` response headers. The default collection plan is intentionally small and below the free-access 100 QPM limit.

The current prototype stores collected evidence locally in SQLite and exports a JSONL snapshot for analysis. It does not store author names by default. It is designed to avoid retaining deleted or account-identifying data, and the retention policy can be configured to purge stored evidence routinely.

The app does not train a machine learning or AI model on Reddit data. It may pass a small evidence snapshot to an agent such as Codex or Claude Code to summarize pain-point clusters and generate follow-up search queries, but this is analysis of a bounded local dataset, not model training.

### Reddit account name

`<USER_PROVIDED_REDDIT_USERNAME_WITHOUT_U_SLASH>`

### What benefit/purpose will the bot/app have for Redditors?

The app is read-only and does not interact with Redditors on-platform. Its purpose is to help a developer understand recurring user needs and product friction from public Reddit discussions without scraping or using unidentified traffic. By using Reddit's Data API and respecting OAuth, rate limits, user-agent requirements, and deletion/retention constraints, the app avoids abusive collection patterns and keeps analysis scoped to small, relevant public discussions.

### Provide a detailed description of what the Bot/App will be doing on the Reddit platform.

The app will:

1. Use an approved OAuth client and a unique descriptive User-Agent.
2. Search a small list of configured subreddits for problem-intent phrases such as "I wish", "does anyone know", "frustrated", "hard to", "alternative to", and "too expensive".
3. Retrieve a limited number of matching public posts and public comments.
4. Store normalized evidence locally in SQLite for analysis.
5. Score evidence locally for user-need signals such as explicit wishes, frustration, solution-seeking, switching behavior, cost complaints, and quality/trust issues.
6. Export a bounded JSONL snapshot for a structured analysis report.

Initial target subreddits are `loseit`, `CICO`, and `MealPrepSunday`, with low limits such as 8 posts per query and 10 comments per post. The app will not expand into broad bulk export and will not attempt to bypass rate limits or access controls.

### What is missing from Devvit that prevents building on that platform?

Devvit is designed for apps that run on Reddit and provide on-platform experiences, moderation workflows, event triggers, UI, and community-specific functionality.

This prototype is an external local analysis pipeline. It needs to run as a developer-owned local CLI, write to a local SQLite database, export JSONL reports, and optionally invoke local Codex/Claude Code CLI workflows for structured analysis. It does not need to create an on-platform Reddit app experience, and it does not post or interact with users. Because the workflow is off-platform, local, and analysis/report-oriented, the Data API is the appropriate technical interface.

### Provide a link to source code or platform that will access the API.

`<USER_PROVIDED_SOURCE_URL_OR_PLATFORM_URL>`

### What subreddits do you intend to use the bot/app in?

Initial technical validation: `loseit`, `CICO`, `MealPrepSunday`.

Future additions would remain explicitly configured, low-volume, and topic-scoped.

### If applicable, what username will you be operating this Bot/App under?

`<OPTIONAL_USER_PROVIDED_BOT_OR_APP_USERNAME>`

