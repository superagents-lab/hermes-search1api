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
| `search1api_ask` | Natural-language search with automatic routing and relevance ranking (5 credits) |
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


## Current API capabilities

Search supports `bingcn`, `yandex`, and `grokipedia`; `sogou` is removed.
Search and news support `day`, `week`, `month`, and `year`. Search accepts
`page` on engines with native pagination.

The default Ask tool accepts only a natural-language `query`. The server
chooses engines and a time window and returns `query`, `intent`, ranked
`results`, and `errors`. Ask results include `source` and `relevance`; this
endpoint returns search results rather than a generated answer. Each call
costs **5 credits**. Use ordinary search when the engine and keywords are known.

Engine-specific search/news attributes stay inside optional per-result
`metadata`: GitHub uses `kind`, `stars`, `language`, and `num_comments`;
Hacker News news results use `story_url`, `points`, and `num_comments`.
`published_date` stays optional at the result top level. Zero counts are
preserved and unavailable fields are omitted. Credit Grokipedia results as
"Powered by xAI".

`search1api_ask` is registered by default. The vendored SDK is the exact
published Python SDK 0.4.0; no extra pip installation is needed.
