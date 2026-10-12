from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

JsonPrimitive = Union[bool, float, int, str, None]
JsonValue = Union[JsonPrimitive, List["JsonValue"], Dict[str, "JsonValue"]]
TimeRange = Literal["day", "week", "month", "year"]
SearchEngine = Literal[
    "google",
    "bing",
    "bingcn",
    "duckduckgo",
    "yahoo",
    "yandex",
    "youtube",
    "x",
    "reddit",
    "github",
    "arxiv",
    "wechat",
    "bilibili",
    "imdb",
    "wikipedia",
    "grokipedia",
    "baidu",
    "360",
    "quark",
]
NewsEngine = Literal["google", "bing", "duckduckgo", "yahoo", "hackernews", "reuters"]
CrawlType = Literal["sitemap", "all"]
ScreenshotFormat = Literal["png", "jpeg", "webp"]
ScreenshotWaitUntil = Literal["domcontentloaded", "load", "networkidle"]


class SearchRequestRequired(TypedDict):
    query: str


class SearchRequest(SearchRequestRequired, total=False):
    search_service: SearchEngine
    max_results: int
    page: int
    crawl_results: int
    image: bool
    include_sites: List[str]
    exclude_sites: List[str]
    language: str
    time_range: TimeRange


class SearchResultRequired(TypedDict):
    title: str
    link: str
    snippet: str


class SearchResultMetadata(TypedDict, total=False):
    kind: Literal["repo", "issue", "pr", "discussion"]
    stars: int
    language: str
    num_comments: int
    points: int
    story_url: str


class SearchResult(SearchResultRequired, total=False):
    content: str
    published_date: str
    metadata: SearchResultMetadata


class SearchResponseRequired(TypedDict):
    searchParameters: SearchRequest
    results: List[SearchResult]


class SearchResponse(SearchResponseRequired, total=False):
    images: List[str]


NewsResponse = SearchResponse


class NewsRequestRequired(TypedDict):
    query: str


class NewsRequest(NewsRequestRequired, total=False):
    search_service: NewsEngine
    max_results: int
    crawl_results: int
    image: bool
    include_sites: List[str]
    exclude_sites: List[str]
    language: str
    time_range: TimeRange


class AskIntent(TypedDict):
    search_query: str
    sources: List[str]
    time_range: Optional[TimeRange]


class AskResultRequired(TypedDict):
    title: str
    link: str
    snippet: str
    source: str
    relevance: float


class AskResult(AskResultRequired, total=False):
    published_date: str


class AskError(TypedDict):
    source: str
    message: str


class AskResponse(TypedDict):
    query: str
    intent: AskIntent
    results: List[AskResult]
    errors: List[AskError]


FeedbackCategory = Literal["bug", "feature_request", "docs", "other"]


class FeedbackAgent(TypedDict, total=False):
    name: str
    model: str


class FeedbackResponse(TypedDict):
    id: str
    status: Literal["new"]


class BatchItemRequired(TypedDict):
    success: bool
    cost: int


class BatchItem(BatchItemRequired, total=False):
    data: SearchResponse
    error: Dict[str, Any]


class BatchSummary(TypedDict):
    total: int
    successful: int
    failed: int
    totalCost: int


class BatchResponse(TypedDict):
    results: List[BatchItem]
    summary: BatchSummary


class CrawlRequestRequired(TypedDict):
    url: str


class CrawlRequest(CrawlRequestRequired, total=False):
    enableFallback: bool


class CrawlResultRequired(TypedDict):
    title: str
    link: str
    content: str


class CrawlResult(CrawlResultRequired, total=False):
    metadata: Dict[str, Any]


class CrawlResponse(TypedDict):
    crawlParameters: Dict[str, str]
    results: CrawlResult


class ScreenshotViewport(TypedDict, total=False):
    width: int
    height: int
    device_scale_factor: float


class ScreenshotResponseRequired(TypedDict):
    data: bytes
    content_type: str


class ScreenshotResponse(ScreenshotResponseRequired, total=False):
    request_id: str


class SitemapResponse(TypedDict):
    links: List[str]


class TrendingResult(TypedDict, total=False):
    title: str
    url: str
    description: Optional[str]


class TrendingResponse(TypedDict):
    trendingParameters: Dict[str, Any]
    results: List[TrendingResult]


class ExtractResponse(TypedDict):
    success: bool
    extractParameters: Dict[str, str]
    results: Any


class DeepcrawlAcceptedResponse(TypedDict):
    taskId: str
    status: str


class DeepcrawlStatusResponseRequired(TypedDict):
    taskId: str


class DeepcrawlStatusResponse(DeepcrawlStatusResponseRequired, total=False):
    status: str
    success: bool
    message: str
    error: Optional[str]
    r2Key: str
    zipUrl: Optional[str]


class UsageResponse(TypedDict):
    usage: int
    user_id: Optional[str]
    credential_type: str
    client_id: Optional[str]


class HealthResponseRequired(TypedDict):
    status: str


class HealthResponse(HealthResponseRequired, total=False):
    timestamp: str
    version: str
