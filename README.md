# Search1API — Hermes Plugin

Give your [Hermes Agent](https://github.com/NousResearch/hermes-agent) live web
search, news, page reading, sitemap discovery, and trending topics through
[Search1API](https://s1.dev).

## Install

```bash
hermes plugins install superagents-lab/hermes-search1api --enable
export SEARCH1API_KEY="your-key"   # https://s1.dev — 100 free credits
```

`SEARCH1API_API_KEY` is also accepted. No other dependencies: the official
[`search1api` Python SDK](https://pypi.org/project/search1api/) is vendored
into this repo, and its only requirement (`httpx`) is already a Hermes core
dependency.

## Tools

| Tool | What it does |
|---|---|
| `search1api_search` | Live web search — freshness (`time_range`), domain filters (`include_sites`/`exclude_sites`), engine choice (`search_service`), optional full-page retrieval (`crawl_results`) |
| `search1api_news` | News search with the same filters |
| `search1api_crawl` | Read one public URL as clean Markdown |
| `search1api_sitemap` | Enumerate a site's URLs |
| `search1api_trending` | Trending GitHub repos / Hacker News stories |

All tools return JSON. Errors come back as
`{"success": false, "error": {"type", "message", "status_code?"}}`.

A bundled skill (`plugin:search1api`) teaches the agent when to pick each tool;
load it with `skill_view("plugin:search1api")`.

## Repository layout

- `__init__.py` — plugin entry point (`register(ctx)`), tool handlers
- `search1api/` — vendored SDK (synced from PyPI via `scripts/sync_sdk.sh`)
- `skills/search1api/SKILL.md` — bundled skill
- `plugin.yaml` — Hermes plugin manifest

## Links

- Search1API: https://s1.dev · Terms: https://blog.s1.dev/pages/terms ·
  Privacy: https://s1.dev/privacy
- Maintained by [SuperAgents, LLC](https://github.com/superagents-lab)

## License

MIT
