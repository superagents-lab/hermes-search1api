# Changelog

## 0.2.1 - 2026-10-14

- Read `SEARCH1API_KEY` / `SEARCH1API_API_KEY` through Hermes's profile-scoped `agent.secret_scope.get_secret`, so each profile uses its own key under multiplexing (plugin catalog rule 11). Older Hermes builds still read the environment.

## 0.2.0 - 2026-10-12

- Add the default query-only Ask tool (Agentic Search in n8n), with a 5-credit cost disclosure.
- Add Bing China, Yandex, and Grokipedia and remove Sogou. Support `week` in search/news and native search pagination.
- Preserve nested engine metadata, zero counters, and optional top-level publication dates; preserve Ask routing, source, relevance, and errors.
