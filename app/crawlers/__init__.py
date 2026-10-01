"""Crawler integrations for Scout."""

from .crawl4ai_adapter import Crawl4AIError, crawl_url, health_check
from .gateway import fetch, fetch_async
from .scrapling_bridge import (
    ScraplingBridgeError,
    ScraplingPage,
    fetch_page,
    fetch_page_async,
)

__all__ = [
    "Crawl4AIError",
    "crawl_url",
    "health_check",
    "fetch",
    "fetch_async",
    "ScraplingBridgeError",
    "ScraplingPage",
    "fetch_page",
    "fetch_page_async",
]
