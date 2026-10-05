"""
Scout Acquisition Gateway.

Provides one stable interface for acquiring web pages while keeping
the acquisition backend separate from platform-specific extraction.

Current backends:
- Crawl4AI
- HTTP/requests

Future backends, including Scrapling, can be added without changing
the callers that depend on this gateway.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Literal

import requests

from .crawl4ai_adapter import crawl_url

logger = logging.getLogger(__name__)

BackendName = Literal["auto", "crawl4ai", "http"]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_fetch(url: str) -> dict[str, Any]:
    # Lazy import avoids app.scrapers <-> app.crawlers circular imports.
    from app.scrapers.stealth import (
        get_requests_proxies,
        random_user_agent,
    )
    """Fetch a URL with Scout's existing HTTP/stealth infrastructure."""
    headers = {
        "User-Agent": random_user_agent(),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20,
            proxies=get_requests_proxies(),
        )

        return {
            "url": url,
            "final_url": str(response.url),
            "backend": "http",
            "success": response.status_code == 200,
            "status": (
                "success"
                if response.status_code == 200
                else "error"
            ),
            "status_code": response.status_code,
            "raw_html": response.text,
            "cleaned_html": None,
            "content": None,
            "markdown": None,
            "response_headers": dict(response.headers),
            "metadata": None,
            "error": (
                None
                if response.status_code == 200
                else f"HTTP {response.status_code}"
            ),
            "timestamp": _timestamp(),
        }

    except requests.exceptions.Timeout:
        return {
            "url": url,
            "final_url": url,
            "backend": "http",
            "success": False,
            "status": "error",
            "status_code": None,
            "raw_html": None,
            "cleaned_html": None,
            "content": None,
            "markdown": None,
            "response_headers": None,
            "metadata": None,
            "error": "HTTP request timed out",
            "timestamp": _timestamp(),
        }

    except requests.exceptions.RequestException as exc:
        return {
            "url": url,
            "final_url": url,
            "backend": "http",
            "success": False,
            "status": "error",
            "status_code": None,
            "raw_html": None,
            "cleaned_html": None,
            "content": None,
            "markdown": None,
            "response_headers": None,
            "metadata": None,
            "error": str(exc),
            "timestamp": _timestamp(),
        }


async def fetch_async(
    url: str,
    backend: BackendName = "auto",
) -> dict[str, Any]:
    """
    Acquire one URL through the requested backend.

    auto:
        Crawl4AI first, then HTTP fallback.

    crawl4ai:
        Crawl4AI only.

    http:
        Requests/HTTP only.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")

    target = url.strip()

    if backend not in {"auto", "crawl4ai", "http"}:
        raise ValueError(
            f"Unsupported acquisition backend: {backend}"
        )

    if backend in {"auto", "crawl4ai"}:
        try:
            result = await crawl_url(target)

            if (
                result.get("success")
                and result.get("raw_html")
            ):
                result["backend"] = "crawl4ai"
                return result

            if backend == "crawl4ai":
                result["backend"] = "crawl4ai"
                return result

            logger.warning(
                "Crawl4AI acquisition failed for %s; "
                "falling back to HTTP.",
                target,
            )

        except Exception as exc:
            if backend == "crawl4ai":
                logger.exception(
                    "Crawl4AI acquisition failed for %s",
                    target,
                )
                return {
                    "url": target,
                    "final_url": target,
                    "backend": "crawl4ai",
                    "success": False,
                    "status": "error",
                    "status_code": None,
                    "raw_html": None,
                    "cleaned_html": None,
                    "content": None,
                    "markdown": None,
                    "response_headers": None,
                    "metadata": None,
                    "error": str(exc),
                    "timestamp": _timestamp(),
                }

            logger.warning(
                "Crawl4AI acquisition raised for %s: %s; "
                "falling back to HTTP.",
                target,
                exc,
            )

    return _http_fetch(target)


def fetch(
    url: str,
    backend: BackendName = "auto",
) -> dict[str, Any]:
    """
    Synchronous acquisition entry point for Scout callers.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(fetch_async(url, backend))

    raise RuntimeError(
        "Scout acquisition fetch() cannot be called from a running "
        "event loop; use fetch_async() instead."
    )


__all__ = [
    "BackendName",
    "fetch",
    "fetch_async",
]
