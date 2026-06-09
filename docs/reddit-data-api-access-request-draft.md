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

Data API access request for external local community FAQ insight tool

### Details of inquiry

I am requesting Reddit Data API access for an external local prototype named `community-faq-insight-tool`.

The app is a read-only, low-volume local developer tool that collects public Reddit posts and comments from a small, explicitly configured set of subreddits and search queries. The purpose is community support improvement: helping moderators or community operators identify recurring beginner questions, rule confusion, onboarding friction, and gaps in wiki or FAQ guidance.

The app does not post, comment, vote, send messages, modify Reddit content, access private messages, access private subreddits, perform moderation actions, or automate any user interaction on Reddit. It will use OAuth, a unique descriptive User-Agent, and will monitor Reddit's `X-Ratelimit-*` response headers. The default collection plan is intentionally small and below the free-access 100 QPM limit.

The current prototype stores collected evidence locally in SQLite and exports a bounded JSONL snapshot for local summarization. It does not store author names by default. It is designed to avoid retaining deleted or account-identifying data, and the retention policy can be configured to purge stored evidence routinely, with a target of deleting stored Reddit content within 48 hours unless a shorter operational review window is used.

The app does not train a machine learning or AI model on Reddit data. It may summarize a small evidence snapshot locally to suggest FAQ topics or moderator review items, but this is bounded operational summarization, not model training, data resale, advertising, user profiling, or commercial data mining.

### Reddit account name

`<USER_PROVIDED_REDDIT_USERNAME_WITHOUT_U_SLASH>`

### What benefit/purpose will the bot/app have for Redditors?

The app is read-only and does not interact with Redditors on-platform. Its purpose is to help moderators or community operators improve community documentation by identifying recurring questions, ambiguous rules, onboarding friction, and FAQ gaps in public discussions. By using Reddit's Data API and respecting OAuth, rate limits, user-agent requirements, and deletion/retention constraints, the app avoids scraping and keeps analysis scoped to small, relevant public community-support workflows.

### Provide a detailed description of what the Bot/App will be doing on the Reddit platform.

The app will:

1. Use an approved OAuth client and a unique descriptive User-Agent.
2. Search a small list of configured subreddits for community-support phrases such as "does anyone know", "where can I find", "confused", "new here", and "how do I".
3. Retrieve a limited number of matching public posts and public comments.
4. Store normalized evidence locally in SQLite for operational review.
5. Score evidence locally for community-support signals such as repeated beginner questions, rule confusion, wiki gaps, requests for clarification, and recurring moderator edge cases.
6. Export a bounded JSONL snapshot for a private FAQ/moderator insight report.

Initial target subreddits are `test` and `learnprogramming`, with low limits such as 8 posts per query and 10 comments per post. The app will not expand into broad bulk export and will not attempt to bypass rate limits or access controls. Any live moderator-support use will be limited to communities where the operator has moderator approval or an equivalent community-operator role.

### What is missing from Devvit that prevents building on that platform?

Devvit is designed for apps that run on Reddit and provide on-platform experiences, moderation workflows, event triggers, UI, and community-specific functionality.

This prototype is an external local audit and reporting pipeline. It needs to run as a developer-owned local CLI, write to a local SQLite evidence log, verify rate-limit and deletion/retention behavior, and export private operational reports that a human moderator or community operator can review before updating wiki, FAQ, or rule guidance.

Devvit is the preferred path for on-platform apps, but this prototype does not need on-platform UI, event triggers, realtime interactions, custom posts, or automated moderation. It does not perform actions on Reddit. Because the workflow is off-platform, local, read-only, and audit/report-oriented, the Data API is the appropriate technical interface for this initial prototype.

### Provide a link to source code or platform that will access the API.

`<USER_PROVIDED_SOURCE_URL_OR_PLATFORM_URL>`

### What subreddits do you intend to use the bot/app in?

Initial technical validation: `test`, `learnprogramming`.

Future additions would remain explicitly configured, low-volume, community-support scoped, and subject to moderator/community approval where appropriate.

### If applicable, what username will you be operating this Bot/App under?

`<OPTIONAL_USER_PROVIDED_BOT_OR_APP_USERNAME>`
