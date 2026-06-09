# Codex Sites Setup Notes

Checked on 2026-06-09.

## Current Local State

- Codex CLI was updated from `0.133.0` to `0.138.0`.
- Configured plugin marketplaces were refreshed.
- `openai-bundled` now points at the app-bundled marketplace:
  `/Applications/Codex.app/Contents/Resources/plugins/openai-bundled`.
- `sites@openai-bundled` is installed and enabled at version `0.1.12`.
- `apps` and `enable_mcp_apps` are enabled in `~/.codex/config.toml`.
- Root cause found after restart: the Sites app connector was explicitly disabled in
  `~/.codex/config.toml`:
  `disabled_tools = [{ type = "connector", id = "connector_20205bf7d4e99a89d7154bb849718324" }]`.
- That disabled-tool entry has been removed.
- After removing the disabled-tool entry and restarting, Codex can suggest the raw
  connector id, but the install confirmation opens a ChatGPT 404 page. The local
  app directory cache also does not contain `connector_20205bf7d4e99a89d7154bb849718324`.
  This indicates the connector is not currently accessible to this account/workspace,
  even though the bundled Sites plugin references it.

The current environment still cannot expose Sites hosting tools until the Sites connector
becomes accessible to the account/workspace.

## GitHub Pages Fallback

Codex Sites was unavailable, so the review site was published with GitHub Pages.

- Public site: https://soyaoda.github.io/reddit-needs-researcher/
- Public repository: https://github.com/SoyaOda/reddit-needs-researcher
- Pages source: `gh-pages` branch, root path `/`
- Main source branch: `main`

Expected plugin/app mapping:

```text
sites@openai-bundled
connector_20205bf7d4e99a89d7154bb849718324
```

## Project Prepared For Sites

The review site is under `site/`.

```bash
cd site
npm run build
```

Build output:

- Static files: `site/public/`
- Worker-compatible artifact: `site/dist/worker.mjs`

The project includes `.openai/hosting.json` with no storage bindings:

```json
{
  "d1": null,
  "r2": null
}
```

`project_id` is intentionally absent until Sites provisions the remote project.

## Suggested Sites Prompt After Restart

Use this prompt in Codex after Sites is visible:

```text
Use Codex Sites for /Users/odasoya/reddit-needs-researcher. Create or connect a Sites project for the static review site in site/public. Save a version first without deploying. Build command is `npm run build` in `site`; the deployable static content is `site/public`, and `site/dist/worker.mjs` is available if a Worker-compatible artifact is preferred. Keep access owner/admins only until I review the saved version.
```

After review:

```text
Deploy the saved Sites version publicly and give me the production URL so I can use it as the Reddit Data API access request source/platform URL.
```
