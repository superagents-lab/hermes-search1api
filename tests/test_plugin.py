"""Plugin tests: load via a mock PluginContext and exercise handlers with a
mocked httpx transport. Run: python3 -m pytest tests/ -q (needs httpx, pytest).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

PLUGIN_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_DIR))
sys.path.insert(0, str(PLUGIN_DIR.parent))

import hermes_search1api_pkg as plugin  # noqa: E402  (set up by conftest alias)


class MockCtx:
    def __init__(self) -> None:
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.skills: List[Dict[str, Any]] = []

    def register_tool(self, *, name, toolset, schema, handler, check_fn=None,
                      requires_env=None, description="", emoji=""):
        self.tools[name] = {
            "toolset": toolset, "schema": schema, "handler": handler,
            "check_fn": check_fn, "requires_env": requires_env,
            "description": description, "emoji": emoji,
        }

    def register_skill(self, *, name, path, description="", frontmatter=None):
        assert Path(path).exists(), f"SKILL.md missing: {path}"
        self.skills.append({"name": name, "path": path})


@pytest.fixture()
def ctx():
    c = MockCtx()
    plugin.register(c)
    return c


@pytest.fixture()
def api(monkeypatch):
    """Point the vendored SDK's httpx.Client at a mock transport."""
    calls: List[Dict[str, Any]] = []
    responses: List[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({
            "path": request.url.path,
            "body": json.loads(request.content) if request.content else {},
            "auth": request.headers.get("authorization", ""),
        })
        return responses.pop(0)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: real_client(transport=transport))
    monkeypatch.setenv("SEARCH1API_KEY", "test-key")
    return calls, responses


def _json_response(payload, status=200):
    return httpx.Response(status, json=payload)


def test_registers_six_tools_and_skill(ctx):
    assert set(ctx.tools) == {
        "search1api_search", "search1api_news", "search1api_crawl",
        "search1api_sitemap", "search1api_trending", "search1api_ask",
    }
    assert all(t["toolset"] == "search1api" for t in ctx.tools.values())
    assert ctx.skills and ctx.skills[0]["name"] == "search1api"


def test_check_fn_gated_on_key(ctx, monkeypatch):
    monkeypatch.delenv("SEARCH1API_KEY", raising=False)
    monkeypatch.delenv("SEARCH1API_API_KEY", raising=False)
    assert ctx.tools["search1api_search"]["check_fn"]() is False
    monkeypatch.setenv("SEARCH1API_KEY", "k")
    assert ctx.tools["search1api_search"]["check_fn"]() is True


def test_search_maps_params(ctx, api):
    calls, responses = api
    responses.append(_json_response({"results": [{"title": "t", "link": "https://a", "snippet": "s"}]}))
    out = json.loads(ctx.tools["search1api_search"]["handler"]({
        "query": "q", "max_results": 5, "time_range": "week",
        "include_sites": ["a.com"], "exclude_sites": ["b.com"],
    }))
    assert out["results"][0]["link"] == "https://a"
    body = calls[0]["body"]
    assert calls[0]["path"] == "/search"
    assert body["query"] == "q" and body["max_results"] == 5
    assert body["time_range"] == "week"
    assert body["include_sites"] == ["a.com"] and body["exclude_sites"] == ["b.com"]
    assert calls[0]["auth"] == "Bearer test-key"


def test_news_hits_news_endpoint(ctx, api):
    calls, responses = api
    payload = {"results": [{"title": "News", "link": "https://example.com", "metadata": {"points": 0, "num_comments": 0}}]}
    responses.append(_json_response(payload))
    assert json.loads(ctx.tools["search1api_news"]["handler"]({"query": "nvidia"})) == payload
    assert calls[0]["path"] == "/news"


def test_crawl_sitemap_trending(ctx, api):
    calls, responses = api
    responses.append(_json_response({"results": {"title": "t", "link": "u", "content": "md"}}))
    responses.append(_json_response({"links": ["https://a/1"]}))
    responses.append(_json_response({"results": [{"title": "repo", "url": "u"}]}))
    assert json.loads(ctx.tools["search1api_crawl"]["handler"]({"url": "https://a"}))["results"]["content"] == "md"
    assert json.loads(ctx.tools["search1api_sitemap"]["handler"]({"url": "a.com"}))["links"] == ["https://a/1"]
    ctx.tools["search1api_trending"]["handler"]({"service": "github", "max_results": 3})
    assert [c["path"] for c in calls] == ["/crawl", "/sitemap", "/trending"]
    assert calls[2]["body"]["search_service"] == "github"


def test_missing_key_returns_structured_error(ctx, monkeypatch):
    monkeypatch.delenv("SEARCH1API_KEY", raising=False)
    monkeypatch.delenv("SEARCH1API_API_KEY", raising=False)
    out = json.loads(ctx.tools["search1api_search"]["handler"]({"query": "q"}))
    assert out["success"] is False
    assert out["error"]["type"] == "Search1APIConfigurationError"
    assert "SEARCH1API_KEY" in out["error"]["hint"]


def test_http_error_surfaces_status(ctx, api):
    _, responses = api
    responses.append(_json_response({"message": "invalid key"}, status=401))
    out = json.loads(ctx.tools["search1api_search"]["handler"]({"query": "q"}))
    assert out["success"] is False
    assert out["error"]["status_code"] == 401
    assert out["error"]["type"] == "AuthenticationError"


def test_bad_params_fail_fast(ctx, api):
    calls, _ = api
    assert json.loads(ctx.tools["search1api_search"]["handler"]({}))["success"] is False
    assert json.loads(ctx.tools["search1api_crawl"]["handler"]({}))["success"] is False
    assert json.loads(ctx.tools["search1api_trending"]["handler"]({"service": "x"}))["success"] is False
    assert calls == []


@pytest.mark.parametrize("engine", ["bingcn", "yandex", "grokipedia"])
def test_current_engines_pagination_and_metadata(ctx, api, engine):
    calls, responses = api
    payload = {"results": [{"title": "t", "link": "https://example.com", "snippet": "s", "published_date": "2026-10-12", "metadata": {"stars": 0}}]}
    responses.append(_json_response(payload))
    output = json.loads(ctx.tools["search1api_search"]["handler"]({"query": "q", "search_service": engine, "time_range": "week", "page": 2}))
    assert output == payload
    assert calls[0]["body"]["search_service"] == engine
    assert calls[0]["body"]["page"] == 2
    assert calls[0]["body"]["time_range"] == "week"
    assert engine in ctx.tools["search1api_search"]["schema"]["parameters"]["properties"]["search_service"]["enum"]
    assert "sogou" not in plugin._SEARCH_ENGINES


def test_ask_query_only_and_response(ctx, api):
    calls, responses = api
    payload = {"query": "Bun this week", "intent": {"search_query": "Bun", "sources": ["github"], "time_range": "week"}, "results": [{"title": "Bun", "link": "https://github.com/oven-sh/bun", "snippet": "Runtime", "source": "github", "relevance": 0.9}], "errors": []}
    responses.append(_json_response(payload))
    output = json.loads(ctx.tools["search1api_ask"]["handler"]({"query": " Bun this week ", "max_results": 2, "search_service": "google"}))
    assert output == payload
    assert calls[0]["path"] == "/ask"
    assert calls[0]["body"] == {"query": "Bun this week"}
    assert set(ctx.tools["search1api_ask"]["schema"]["parameters"]["properties"]) == {"query"}
    assert json.loads(ctx.tools["search1api_ask"]["handler"]({"query": " "}))["success"] is False
    assert len(calls) == 1


def test_api_key_read_through_hermes_secret_scope(ctx, monkeypatch):
    """The key comes from the active profile's secret scope, not a bare env read."""
    import types

    monkeypatch.delenv("SEARCH1API_KEY", raising=False)
    monkeypatch.delenv("SEARCH1API_API_KEY", raising=False)
    scope = types.ModuleType("agent.secret_scope")
    scope.get_secret = lambda name, default=None: {"SEARCH1API_API_KEY": " scoped "}.get(name, default)
    agent_pkg = types.ModuleType("agent")
    agent_pkg.secret_scope = scope
    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.secret_scope", scope)
    assert plugin._resolve_api_key() == "scoped"
    assert ctx.tools["search1api_search"]["check_fn"]() is True
