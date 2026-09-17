"""
search1api — Hermes Plugin
Search the live web, read pages, find news, discover site links, and explore
trending topics through the Search1API API (https://s1.dev).

The official ``search1api`` Python SDK is vendored into this plugin
(``search1api/`` subpackage) so installs need no pip step. Its only third-party
dependency, ``httpx``, is a Hermes core dependency and always present.
"""
from __future__ import annotations

__version__ = "0.1.0"

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, get_args

# Hermes plugin discovery can execute this flat plugin from outside the plugin
# directory. Keep sibling imports cwd-independent (same pattern as
# hermes-web-search-plus).
_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.append(str(_PLUGIN_DIR))

try:  # Package load path used by Hermes plugin discovery.
    from .search1api import (
        APIStatusError,
        Search1API,
        Search1APIConfigurationError,
        Search1APIError,
    )
    from .search1api.types import NewsEngine, SearchEngine, TimeRange
except ImportError:  # Direct script/test imports from the plugin directory.
    from search1api import (
        APIStatusError,
        Search1API,
        Search1APIConfigurationError,
        Search1APIError,
    )
    from search1api.types import NewsEngine, SearchEngine, TimeRange

_TOOLSET_NAME = "search1api"
_API_KEY_ENV_VARS = ("SEARCH1API_KEY", "SEARCH1API_API_KEY")

_SEARCH_ENGINES = sorted(get_args(SearchEngine))
_NEWS_ENGINES = sorted(get_args(NewsEngine))
_TIME_RANGES = sorted(get_args(TimeRange))
_TRENDING_SERVICES = ["github", "hackernews"]


def _resolve_api_key() -> Optional[str]:
    for var in _API_KEY_ENV_VARS:
        value = os.environ.get(var, "").strip()
        if value:
            return value
    return None


def _error_payload(exc: Exception) -> str:
    payload: Dict[str, Any] = {
        "success": False,
        "error": {"type": type(exc).__name__, "message": str(exc)},
    }
    if isinstance(exc, APIStatusError):
        payload["error"]["status_code"] = exc.status_code
        if exc.request_id:
            payload["error"]["request_id"] = exc.request_id
    if isinstance(exc, Search1APIConfigurationError):
        payload["error"]["hint"] = (
            "Set SEARCH1API_KEY (or SEARCH1API_API_KEY). "
            "Get a key at https://s1.dev — the free plan includes 100 credits."
        )
    return json.dumps(payload)


def _call(fn, *args, **kwargs) -> str:
    """Run one SDK call and serialize the response envelope for the model."""
    api_key = _resolve_api_key()
    try:
        client = Search1API(api_key=api_key)
    except Search1APIError as exc:
        return _error_payload(exc)
    try:
        with client:
            return json.dumps(fn(client, *args, **kwargs))
    except Search1APIError as exc:
        return _error_payload(exc)


def _str_list(value: Any) -> Optional[List[str]]:
    if not isinstance(value, list):
        return None
    items = [str(v).strip() for v in value if str(v).strip()]
    return items or None


def _search_kwargs(params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "search_service": params.get("search_service"),
        "max_results": params.get("max_results"),
        "crawl_results": params.get("crawl_results"),
        "include_sites": _str_list(params.get("include_sites")),
        "exclude_sites": _str_list(params.get("exclude_sites")),
        "time_range": params.get("time_range"),
    }


def _has_api_key() -> bool:
    return _resolve_api_key() is not None


def register(ctx) -> None:
    """Hermes plugin entry point: register Search1API tools and skill."""

    search_schema = {
        "name": "search1api_search",
        "description": (
            "Search the live web. Use for current facts, research, documentation, "
            "people, companies, products, and source discovery."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of results.",
                },
                "search_service": {
                    "type": "string",
                    "enum": _SEARCH_ENGINES,
                    "description": "Search backend to use.",
                },
                "crawl_results": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of results to retrieve in full.",
                },
                "include_sites": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Only return results from these domains.",
                },
                "exclude_sites": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Exclude results from these domains.",
                },
                "time_range": {
                    "type": "string",
                    "enum": _TIME_RANGES,
                    "description": "Restrict results to a freshness window.",
                },
            },
            "required": ["query"],
        },
    }

    def search_handler(params, **kwargs) -> str:
        del kwargs
        params = params if isinstance(params, dict) else {}
        query = str(params.get("query") or "").strip()
        if not query:
            return json.dumps({"success": False, "error": {"message": "query is required"}})
        return _call(lambda c: c.search(query, **_search_kwargs(params)))

    ctx.register_tool(
        name="search1api_search",
        toolset=_TOOLSET_NAME,
        schema=search_schema,
        handler=search_handler,
        check_fn=_has_api_key,
        requires_env=[],
        description="Search the live web via Search1API",
        emoji="🔍",
    )

    news_schema = {
        "name": "search1api_news",
        "description": "Search current news and optionally retrieve full article content.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "News query."},
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of results.",
                },
                "search_service": {
                    "type": "string",
                    "enum": _NEWS_ENGINES,
                    "description": "News backend to use.",
                },
                "crawl_results": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of articles to retrieve in full.",
                },
                "include_sites": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Only return results from these domains.",
                },
                "exclude_sites": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Exclude results from these domains.",
                },
                "time_range": {
                    "type": "string",
                    "enum": _TIME_RANGES,
                    "description": "Restrict results to a freshness window.",
                },
            },
            "required": ["query"],
        },
    }

    def news_handler(params, **kwargs) -> str:
        del kwargs
        params = params if isinstance(params, dict) else {}
        query = str(params.get("query") or "").strip()
        if not query:
            return json.dumps({"success": False, "error": {"message": "query is required"}})
        return _call(lambda c: c.news(query, **_search_kwargs(params)))

    ctx.register_tool(
        name="search1api_news",
        toolset=_TOOLSET_NAME,
        schema=news_schema,
        handler=news_handler,
        check_fn=_has_api_key,
        requires_env=[],
        description="Search current news via Search1API",
        emoji="📰",
    )

    crawl_schema = {
        "name": "search1api_crawl",
        "description": (
            "Retrieve clean readable Markdown content from a public URL. "
            "Use after search1api_search to read a promising result in full."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "Public page URL to retrieve.",
                }
            },
            "required": ["url"],
        },
    }

    def crawl_handler(params, **kwargs) -> str:
        del kwargs
        params = params if isinstance(params, dict) else {}
        url = str(params.get("url") or "").strip()
        if not url:
            return json.dumps({"success": False, "error": {"message": "url is required"}})
        return _call(lambda c: c.crawl(url))

    ctx.register_tool(
        name="search1api_crawl",
        toolset=_TOOLSET_NAME,
        schema=crawl_schema,
        handler=crawl_handler,
        check_fn=_has_api_key,
        requires_env=[],
        description="Read a public page as clean Markdown via Search1API",
        emoji="📄",
    )

    sitemap_schema = {
        "name": "search1api_sitemap",
        "description": "Discover links related to a public URL or domain.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Public URL or domain to explore.",
                }
            },
            "required": ["url"],
        },
    }

    def sitemap_handler(params, **kwargs) -> str:
        del kwargs
        params = params if isinstance(params, dict) else {}
        url = str(params.get("url") or "").strip()
        if not url:
            return json.dumps({"success": False, "error": {"message": "url is required"}})
        return _call(lambda c: c.sitemap(url))

    ctx.register_tool(
        name="search1api_sitemap",
        toolset=_TOOLSET_NAME,
        schema=sitemap_schema,
        handler=sitemap_handler,
        check_fn=_has_api_key,
        requires_env=[],
        description="Discover a site's link structure via Search1API",
        emoji="🗺️",
    )

    trending_schema = {
        "name": "search1api_trending",
        "description": "Find trending repositories on GitHub or stories on Hacker News.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "enum": _TRENDING_SERVICES,
                    "description": "Trending source.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of results.",
                },
            },
            "required": ["service"],
        },
    }

    def trending_handler(params, **kwargs) -> str:
        del kwargs
        params = params if isinstance(params, dict) else {}
        service = str(params.get("service") or "").strip()
        if service not in _TRENDING_SERVICES:
            return json.dumps({
                "success": False,
                "error": {"message": f"service must be one of {_TRENDING_SERVICES}"},
            })
        return _call(lambda c: c.trending(service, max_results=params.get("max_results")))

    ctx.register_tool(
        name="search1api_trending",
        toolset=_TOOLSET_NAME,
        schema=trending_schema,
        handler=trending_handler,
        check_fn=_has_api_key,
        requires_env=[],
        description="Trending GitHub repos and Hacker News stories via Search1API",
        emoji="📈",
    )

    if hasattr(ctx, "register_skill"):
        ctx.register_skill(
            name="search1api",
            path=_PLUGIN_DIR / "skills" / "search1api" / "SKILL.md",
            description="When and how to use the Search1API search, news, crawl, sitemap, and trending tools.",
        )
