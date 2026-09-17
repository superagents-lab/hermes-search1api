from __future__ import annotations

import asyncio
import json
import os
import random
import time
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Literal, Mapping, Optional, cast
from urllib.parse import quote

import httpx

from .errors import (
    APIConnectionError,
    APITimeoutError,
    DeepcrawlFailedError,
    DeepcrawlTimeoutError,
    Search1APIConfigurationError,
    Search1APIError,
    api_status_error,
)
from .types import (
    BatchResponse,
    CrawlRequest,
    CrawlResponse,
    CrawlType,
    DeepcrawlAcceptedResponse,
    DeepcrawlStatusResponse,
    ExtractResponse,
    HealthResponse,
    NewsEngine,
    NewsRequest,
    NewsResponse,
    ScreenshotFormat,
    ScreenshotResponse,
    ScreenshotViewport,
    ScreenshotWaitUntil,
    SearchEngine,
    SearchRequest,
    SearchResponse,
    SitemapResponse,
    TimeRange,
    TrendingResponse,
    UsageResponse,
)

DEFAULT_BASE_URL = "https://api.search1api.com"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_DELAY = 0.5
DEFAULT_DEEPCRAWL_POLL_INTERVAL = 2.0
DEFAULT_DEEPCRAWL_TIMEOUT = 300.0


def _compact(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _search_payload(
    query: str,
    *,
    search_service: Optional[str] = None,
    max_results: Optional[int] = None,
    crawl_results: Optional[int] = None,
    image: Optional[bool] = None,
    include_sites: Optional[List[str]] = None,
    exclude_sites: Optional[List[str]] = None,
    language: Optional[str] = None,
    time_range: Optional[TimeRange] = None,
) -> Dict[str, Any]:
    return _compact(
        {
            "query": query,
            "search_service": search_service,
            "max_results": max_results,
            "crawl_results": crawl_results,
            "image": image,
            "include_sites": include_sites,
            "exclude_sites": exclude_sites,
            "language": language,
            "time_range": time_range,
        }
    )


def _screenshot_payload(
    url: str,
    *,
    format: Optional[ScreenshotFormat] = None,
    full_page: Optional[bool] = None,
    viewport: Optional[ScreenshotViewport] = None,
    wait_until: Optional[ScreenshotWaitUntil] = None,
    wait_for_selector: Optional[str] = None,
    selector: Optional[str] = None,
    delay_ms: Optional[int] = None,
    timeout_ms: Optional[int] = None,
    quality: Optional[int] = None,
    omit_background: Optional[bool] = None,
    color_scheme: Optional[Literal["light", "dark"]] = None,
    animations: Optional[Literal["disabled", "allow"]] = None,
) -> Dict[str, Any]:
    return _compact(
        {
            "url": url,
            "format": format,
            "full_page": full_page,
            "viewport": viewport,
            "wait_until": wait_until,
            "wait_for_selector": wait_for_selector,
            "selector": selector,
            "delay_ms": delay_ms,
            "timeout_ms": timeout_ms,
            "quality": quality,
            "omit_background": omit_background,
            "color_scheme": color_scheme,
            "animations": animations,
        }
    )


def _retry_after(response: httpx.Response) -> Optional[float]:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = float(parsedate_to_datetime(value).timestamp())
            return max(0.0, retry_at - time.time())
        except (TypeError, ValueError, OverflowError):
            return None


def _should_retry(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _error_body(response: httpx.Response) -> Mapping[str, Any]:
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError):
        return {"message": response.text}
    return body if isinstance(body, dict) else {"message": response.text}


class _ClientConfig:
    def __init__(
        self,
        api_key: Optional[str],
        *,
        base_url: str,
        timeout: float,
        max_retries: int,
        retry_delay: float,
        headers: Optional[Mapping[str, str]],
    ) -> None:
        resolved_key = api_key or os.getenv("SEARCH1API_API_KEY")
        if not resolved_key:
            raise Search1APIConfigurationError(
                "Missing API key. Pass api_key or set SEARCH1API_API_KEY."
            )
        if max_retries < 0:
            raise Search1APIConfigurationError("max_retries cannot be negative")
        if timeout <= 0:
            raise Search1APIConfigurationError("timeout must be positive")
        if retry_delay < 0:
            raise Search1APIConfigurationError("retry_delay cannot be negative")

        self.api_key: str = resolved_key
        self.base_url: str = base_url.rstrip("/")
        self.timeout: float = timeout
        self.max_retries: int = max_retries
        self.retry_delay: float = retry_delay
        self.headers: Dict[str, str] = dict(headers or {})

    def _request_headers(self, accept: str = "application/json") -> Dict[str, str]:
        return {
            "Accept": accept,
            "Authorization": f"Bearer {self.api_key}",
            "X-Search1API-Client": "python/0.2.0",
            **self.headers,
        }

    def _retry_sleep(self, attempt: int) -> float:
        base = self.retry_delay * (2**attempt)
        return float(base + random.random() * base * 0.25)


class Search1API(_ClientConfig):
    """Synchronous Search1API client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        headers: Optional[Mapping[str, str]] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(
            api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            headers=headers,
        )
        self._client = client or httpx.Client()
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "Search1API":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def search(
        self,
        query: str,
        *,
        search_service: Optional[SearchEngine] = None,
        max_results: Optional[int] = None,
        crawl_results: Optional[int] = None,
        image: Optional[bool] = None,
        include_sites: Optional[List[str]] = None,
        exclude_sites: Optional[List[str]] = None,
        language: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
    ) -> SearchResponse:
        payload = _search_payload(
            query,
            search_service=search_service,
            max_results=max_results,
            crawl_results=crawl_results,
            image=image,
            include_sites=include_sites,
            exclude_sites=exclude_sites,
            language=language,
            time_range=time_range,
        )
        return cast(SearchResponse, self._request_json("POST", "/search", json=payload))

    def search_batch(self, requests: List[SearchRequest]) -> BatchResponse:
        return cast(BatchResponse, self._request_json("POST", "/search", json=requests))

    def news(
        self,
        query: str,
        *,
        search_service: Optional[NewsEngine] = None,
        max_results: Optional[int] = None,
        crawl_results: Optional[int] = None,
        image: Optional[bool] = None,
        include_sites: Optional[List[str]] = None,
        exclude_sites: Optional[List[str]] = None,
        language: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
    ) -> NewsResponse:
        payload = _search_payload(
            query,
            search_service=search_service,
            max_results=max_results,
            crawl_results=crawl_results,
            image=image,
            include_sites=include_sites,
            exclude_sites=exclude_sites,
            language=language,
            time_range=time_range,
        )
        return cast(NewsResponse, self._request_json("POST", "/news", json=payload))

    def news_batch(self, requests: List[NewsRequest]) -> BatchResponse:
        return cast(BatchResponse, self._request_json("POST", "/news", json=requests))

    def crawl(
        self, url: str, *, enable_fallback: Optional[bool] = None
    ) -> CrawlResponse:
        payload = _compact({"url": url, "enableFallback": enable_fallback})
        return cast(CrawlResponse, self._request_json("POST", "/crawl", json=payload))

    def crawl_batch(self, requests: List[CrawlRequest]) -> List[CrawlResponse]:
        return cast(
            List[CrawlResponse], self._request_json("POST", "/crawl", json=requests)
        )

    def screenshot(
        self,
        url: str,
        *,
        format: Optional[ScreenshotFormat] = None,
        full_page: Optional[bool] = None,
        viewport: Optional[ScreenshotViewport] = None,
        wait_until: Optional[ScreenshotWaitUntil] = None,
        wait_for_selector: Optional[str] = None,
        selector: Optional[str] = None,
        delay_ms: Optional[int] = None,
        timeout_ms: Optional[int] = None,
        quality: Optional[int] = None,
        omit_background: Optional[bool] = None,
        color_scheme: Optional[Literal["light", "dark"]] = None,
        animations: Optional[Literal["disabled", "allow"]] = None,
    ) -> ScreenshotResponse:
        response = self._request(
            "POST",
            "/screenshot",
            accept=f"image/{format or 'png'}",
            json=_screenshot_payload(
                url,
                format=format,
                full_page=full_page,
                viewport=viewport,
                wait_until=wait_until,
                wait_for_selector=wait_for_selector,
                selector=selector,
                delay_ms=delay_ms,
                timeout_ms=timeout_ms,
                quality=quality,
                omit_background=omit_background,
                color_scheme=color_scheme,
                animations=animations,
            ),
        )
        result: ScreenshotResponse = {
            "data": response.content,
            "content_type": response.headers.get(
                "content-type", f"image/{format or 'png'}"
            ),
        }
        request_id = response.headers.get("x-request-id")
        if request_id:
            result["request_id"] = request_id
        return result

    def sitemap(self, url: str, *, type: Optional[CrawlType] = None) -> SitemapResponse:
        return cast(
            SitemapResponse,
            self._request_json(
                "POST", "/sitemap", json=_compact({"url": url, "type": type})
            ),
        )

    def trending(
        self, search_service: str, *, max_results: Optional[int] = None
    ) -> TrendingResponse:
        return cast(
            TrendingResponse,
            self._request_json(
                "POST",
                "/trending",
                json=_compact(
                    {"search_service": search_service, "max_results": max_results}
                ),
            ),
        )

    def extract(
        self,
        url: str,
        *,
        prompt: Optional[str] = None,
        response_format: Optional[Mapping[str, Any]] = None,
    ) -> ExtractResponse:
        return cast(
            ExtractResponse,
            self._request_json(
                "POST",
                "/extract",
                json=_compact(
                    {"url": url, "prompt": prompt, "response_format": response_format}
                ),
            ),
        )

    def start_deepcrawl(
        self, url: str, *, type: Optional[CrawlType] = None
    ) -> DeepcrawlAcceptedResponse:
        return cast(
            DeepcrawlAcceptedResponse,
            self._request_json(
                "POST",
                "/deepcrawl",
                json=_compact({"url": url, "type": type}),
                retryable=False,
            ),
        )

    def get_deepcrawl_status(self, task_id: str) -> DeepcrawlStatusResponse:
        return cast(
            DeepcrawlStatusResponse,
            self._request_json("GET", f"/deepcrawl/status/{quote(task_id, safe='')}"),
        )

    def wait_for_deepcrawl(
        self,
        task_id: str,
        *,
        poll_interval: float = DEFAULT_DEEPCRAWL_POLL_INTERVAL,
        timeout: float = DEFAULT_DEEPCRAWL_TIMEOUT,
    ) -> DeepcrawlStatusResponse:
        deadline = time.monotonic() + timeout
        while True:
            response = self.get_deepcrawl_status(task_id)
            if response.get("success") is True or response.get("status") == "completed":
                return response
            if response.get("success") is False or response.get("status") in {
                "failed",
                "not_found",
            }:
                raise DeepcrawlFailedError(response)
            if time.monotonic() + poll_interval > deadline:
                raise DeepcrawlTimeoutError(task_id, timeout)
            time.sleep(poll_interval)

    def deepcrawl(
        self,
        url: str,
        *,
        type: Optional[CrawlType] = None,
        poll_interval: float = DEFAULT_DEEPCRAWL_POLL_INTERVAL,
        timeout: float = DEFAULT_DEEPCRAWL_TIMEOUT,
    ) -> DeepcrawlStatusResponse:
        task = self.start_deepcrawl(url, type=type)
        return self.wait_for_deepcrawl(
            task["taskId"], poll_interval=poll_interval, timeout=timeout
        )

    def usage(self, period: Optional[TimeRange] = None) -> UsageResponse:
        return cast(
            UsageResponse,
            self._request_json("GET", "/usage", params=_compact({"period": period})),
        )

    def health(self) -> HealthResponse:
        return cast(HealthResponse, self._request_json("GET", "/health"))

    def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._request(method, path, **kwargs)
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise Search1APIError(
                f"Search1API returned invalid JSON for {path}"
            ) from exc

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        retryable = bool(kwargs.pop("retryable", True))
        accept = str(kwargs.pop("accept", "application/json"))
        max_retries = self.max_retries if retryable else 0
        for attempt in range(max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=self._request_headers(accept),
                    timeout=self.timeout,
                    **kwargs,
                )
            except httpx.TimeoutException as exc:
                if attempt < max_retries:
                    time.sleep(self._retry_sleep(attempt))
                    continue
                raise APITimeoutError(
                    f"Search1API request timed out after {self.timeout:g}s"
                ) from exc
            except httpx.RequestError as exc:
                if attempt < max_retries:
                    time.sleep(self._retry_sleep(attempt))
                    continue
                raise APIConnectionError("Unable to connect to Search1API") from exc

            if response.is_success:
                return response
            if attempt < max_retries and _should_retry(response.status_code):
                delay = _retry_after(response)
                time.sleep(delay if delay is not None else self._retry_sleep(attempt))
                continue
            raise api_status_error(
                response.status_code, _error_body(response), response.headers
            )
        raise Search1APIError("Search1API request exhausted its retry budget")


class AsyncSearch1API(_ClientConfig):
    """Asynchronous Search1API client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        headers: Optional[Mapping[str, str]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(
            api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            headers=headers,
        )
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncSearch1API":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def search(
        self,
        query: str,
        *,
        search_service: Optional[SearchEngine] = None,
        max_results: Optional[int] = None,
        crawl_results: Optional[int] = None,
        image: Optional[bool] = None,
        include_sites: Optional[List[str]] = None,
        exclude_sites: Optional[List[str]] = None,
        language: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
    ) -> SearchResponse:
        return cast(
            SearchResponse,
            await self._request_json(
                "POST",
                "/search",
                json=_search_payload(
                    query,
                    search_service=search_service,
                    max_results=max_results,
                    crawl_results=crawl_results,
                    image=image,
                    include_sites=include_sites,
                    exclude_sites=exclude_sites,
                    language=language,
                    time_range=time_range,
                ),
            ),
        )

    async def search_batch(self, requests: List[SearchRequest]) -> BatchResponse:
        return cast(
            BatchResponse,
            await self._request_json("POST", "/search", json=requests),
        )

    async def news(
        self,
        query: str,
        *,
        search_service: Optional[NewsEngine] = None,
        max_results: Optional[int] = None,
        crawl_results: Optional[int] = None,
        image: Optional[bool] = None,
        include_sites: Optional[List[str]] = None,
        exclude_sites: Optional[List[str]] = None,
        language: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
    ) -> NewsResponse:
        return cast(
            NewsResponse,
            await self._request_json(
                "POST",
                "/news",
                json=_search_payload(
                    query,
                    search_service=search_service,
                    max_results=max_results,
                    crawl_results=crawl_results,
                    image=image,
                    include_sites=include_sites,
                    exclude_sites=exclude_sites,
                    language=language,
                    time_range=time_range,
                ),
            ),
        )

    async def news_batch(self, requests: List[NewsRequest]) -> BatchResponse:
        return cast(
            BatchResponse,
            await self._request_json("POST", "/news", json=requests),
        )

    async def crawl(
        self, url: str, *, enable_fallback: Optional[bool] = None
    ) -> CrawlResponse:
        return cast(
            CrawlResponse,
            await self._request_json(
                "POST",
                "/crawl",
                json=_compact({"url": url, "enableFallback": enable_fallback}),
            ),
        )

    async def crawl_batch(self, requests: List[CrawlRequest]) -> List[CrawlResponse]:
        return cast(
            List[CrawlResponse],
            await self._request_json("POST", "/crawl", json=requests),
        )

    async def screenshot(
        self,
        url: str,
        *,
        format: Optional[ScreenshotFormat] = None,
        full_page: Optional[bool] = None,
        viewport: Optional[ScreenshotViewport] = None,
        wait_until: Optional[ScreenshotWaitUntil] = None,
        wait_for_selector: Optional[str] = None,
        selector: Optional[str] = None,
        delay_ms: Optional[int] = None,
        timeout_ms: Optional[int] = None,
        quality: Optional[int] = None,
        omit_background: Optional[bool] = None,
        color_scheme: Optional[Literal["light", "dark"]] = None,
        animations: Optional[Literal["disabled", "allow"]] = None,
    ) -> ScreenshotResponse:
        response = await self._request(
            "POST",
            "/screenshot",
            accept=f"image/{format or 'png'}",
            json=_screenshot_payload(
                url,
                format=format,
                full_page=full_page,
                viewport=viewport,
                wait_until=wait_until,
                wait_for_selector=wait_for_selector,
                selector=selector,
                delay_ms=delay_ms,
                timeout_ms=timeout_ms,
                quality=quality,
                omit_background=omit_background,
                color_scheme=color_scheme,
                animations=animations,
            ),
        )
        result: ScreenshotResponse = {
            "data": response.content,
            "content_type": response.headers.get(
                "content-type", f"image/{format or 'png'}"
            ),
        }
        request_id = response.headers.get("x-request-id")
        if request_id:
            result["request_id"] = request_id
        return result

    async def sitemap(
        self, url: str, *, type: Optional[CrawlType] = None
    ) -> SitemapResponse:
        return cast(
            SitemapResponse,
            await self._request_json(
                "POST", "/sitemap", json=_compact({"url": url, "type": type})
            ),
        )

    async def trending(
        self, search_service: str, *, max_results: Optional[int] = None
    ) -> TrendingResponse:
        return cast(
            TrendingResponse,
            await self._request_json(
                "POST",
                "/trending",
                json=_compact(
                    {"search_service": search_service, "max_results": max_results}
                ),
            ),
        )

    async def extract(
        self,
        url: str,
        *,
        prompt: Optional[str] = None,
        response_format: Optional[Mapping[str, Any]] = None,
    ) -> ExtractResponse:
        return cast(
            ExtractResponse,
            await self._request_json(
                "POST",
                "/extract",
                json=_compact(
                    {"url": url, "prompt": prompt, "response_format": response_format}
                ),
            ),
        )

    async def start_deepcrawl(
        self, url: str, *, type: Optional[CrawlType] = None
    ) -> DeepcrawlAcceptedResponse:
        return cast(
            DeepcrawlAcceptedResponse,
            await self._request_json(
                "POST",
                "/deepcrawl",
                json=_compact({"url": url, "type": type}),
                retryable=False,
            ),
        )

    async def get_deepcrawl_status(self, task_id: str) -> DeepcrawlStatusResponse:
        return cast(
            DeepcrawlStatusResponse,
            await self._request_json(
                "GET", f"/deepcrawl/status/{quote(task_id, safe='')}"
            ),
        )

    async def wait_for_deepcrawl(
        self,
        task_id: str,
        *,
        poll_interval: float = DEFAULT_DEEPCRAWL_POLL_INTERVAL,
        timeout: float = DEFAULT_DEEPCRAWL_TIMEOUT,
    ) -> DeepcrawlStatusResponse:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            response = await self.get_deepcrawl_status(task_id)
            if response.get("success") is True or response.get("status") == "completed":
                return response
            if response.get("success") is False or response.get("status") in {
                "failed",
                "not_found",
            }:
                raise DeepcrawlFailedError(response)
            if loop.time() + poll_interval > deadline:
                raise DeepcrawlTimeoutError(task_id, timeout)
            await asyncio.sleep(poll_interval)

    async def deepcrawl(
        self,
        url: str,
        *,
        type: Optional[CrawlType] = None,
        poll_interval: float = DEFAULT_DEEPCRAWL_POLL_INTERVAL,
        timeout: float = DEFAULT_DEEPCRAWL_TIMEOUT,
    ) -> DeepcrawlStatusResponse:
        task = await self.start_deepcrawl(url, type=type)
        return await self.wait_for_deepcrawl(
            task["taskId"], poll_interval=poll_interval, timeout=timeout
        )

    async def usage(self, period: Optional[TimeRange] = None) -> UsageResponse:
        return cast(
            UsageResponse,
            await self._request_json(
                "GET", "/usage", params=_compact({"period": period})
            ),
        )

    async def health(self) -> HealthResponse:
        return cast(HealthResponse, await self._request_json("GET", "/health"))

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._request(method, path, **kwargs)
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise Search1APIError(
                f"Search1API returned invalid JSON for {path}"
            ) from exc

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        retryable = bool(kwargs.pop("retryable", True))
        accept = str(kwargs.pop("accept", "application/json"))
        max_retries = self.max_retries if retryable else 0
        for attempt in range(max_retries + 1):
            try:
                response = await self._client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=self._request_headers(accept),
                    timeout=self.timeout,
                    **kwargs,
                )
            except httpx.TimeoutException as exc:
                if attempt < max_retries:
                    await asyncio.sleep(self._retry_sleep(attempt))
                    continue
                raise APITimeoutError(
                    f"Search1API request timed out after {self.timeout:g}s"
                ) from exc
            except httpx.RequestError as exc:
                if attempt < max_retries:
                    await asyncio.sleep(self._retry_sleep(attempt))
                    continue
                raise APIConnectionError("Unable to connect to Search1API") from exc

            if response.is_success:
                return response
            if attempt < max_retries and _should_retry(response.status_code):
                delay = _retry_after(response)
                await asyncio.sleep(
                    delay if delay is not None else self._retry_sleep(attempt)
                )
                continue
            raise api_status_error(
                response.status_code, _error_body(response), response.headers
            )
        raise Search1APIError("Search1API request exhausted its retry budget")
