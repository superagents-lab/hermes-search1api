---
name: search1api
description: When and how to use the Search1API tools (search, news, crawl, sitemap, trending) for live web data.
---

# Search1API

Five tools backed by the Search1API API (https://s1.dev). All require
`SEARCH1API_KEY` (or `SEARCH1API_API_KEY`) in the environment; each call costs
1 credit.

## Tool selection

- `search1api_search` — default for anything needing current web facts:
  documentation, people, companies, products, prices, error messages. Returns
  `{results: [{title, link, snippet}]}` plus optional full `content` when
  `crawl_results > 0`.
- `search1api_news` — current events, announcements, "latest" questions.
  Same parameters as search; `time_range` is especially useful here
  (`day`/`week`/`month`/`year`).
- `search1api_crawl` — read one public URL as clean Markdown. Use this after
  `search1api_search` when a result's snippet is promising but too short, or
  when the user hands you a URL to read.
- `search1api_sitemap` — enumerate a site's URLs. Use when the user asks to
  explore a domain or find pages on a site.
- `search1api_trending` — what's hot on GitHub or Hacker News right now.

## Practical guidance

- Start broad, then narrow with `include_sites` / `exclude_sites` rather than
  stuffing operators into the query.
- `time_range` filters server-side — prefer it over date words in the query
  when freshness matters.
- `crawl_results` fetches full page content for the top N results in the same
  call; use a small number (1–3) to save credits when you only need one good
  source.
- Prefer `search1api_crawl` over re-searching when you already have the URL.

## Errors

Tool responses are JSON. On failure they contain
`{"success": false, "error": {...}}` — check `error.status_code`:
- 401 → the API key is missing or invalid; ask the user to set
  `SEARCH1API_KEY`.
- 402 → credits exhausted; point the user to https://s1.dev to top up.
- 429 → rate limited; retry after a short wait.
