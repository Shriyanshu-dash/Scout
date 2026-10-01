"""Crawler integrations for Scout."""

from .crawl4ai_adapter import Crawl4AIError, crawl_url, health_check

__all__ = [
    "Crawl4AIError",
    "crawl_url",
    "health_check",
    "fetch",
    "fetch_async",
]
from .gateway import fetch, fetch_async
