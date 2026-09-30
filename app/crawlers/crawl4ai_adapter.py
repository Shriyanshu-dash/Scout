"""
Crawl4AI adapter for Scout.

Keeps Crawl4AI-specific implementation details isolated from the rest
of the Scout application.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from crawl4ai import AsyncWebCrawler

logger = logging.getLogger(__name__)


class Crawl4AIError(Exception):
    """Raised when a Crawl4AI operation fails."""


class _TitleParser(HTMLParser):
    """Small standard-library HTML title parser."""

    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.parts.append(data)


def extract_title(html: str | None) -> str | None:
    """Extract the page title from raw HTML."""
    if not html:
        return None

    parser = _TitleParser()

    try:
        parser.feed(html)
        title = " ".join("".join(parser.parts).split())
        return title or None
    except Exception:
        logger.exception("Failed to extract HTML title")
        return None


def _markdown_text(markdown: Any) -> str | None:
    """
    Normalize Crawl4AI's markdown result.

    Crawl4AI can expose markdown as either a string or a markdown
    generation object depending on configuration/version.
    """
    if markdown is None:
        return None

    if isinstance(markdown, str):
        return markdown

    raw_markdown = getattr(markdown, "raw_markdown", None)
    if isinstance(raw_markdown, str):
        return raw_markdown

    return str(markdown)


def health_check() -> bool:
    """
    Verify that Crawl4AI can be imported and its crawler can be constructed.

    A real network crawl is intentionally not performed here.
    """
    try:
        AsyncWebCrawler()
        return True
    except Exception:
        logger.exception("Crawl4AI health check failed")
        return False


async def crawl_url(url: str) -> dict[str, Any]:
    """
    Crawl one URL using Crawl4AI and return a normalized Scout result.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")

    original_url = url.strip()

    try:
        async with AsyncWebCrawler() as crawler:
            crawl_result = await crawler.arun(original_url)

        markdown = _markdown_text(crawl_result.markdown)

        result: dict[str, Any] = {
            "url": original_url,
            "final_url": crawl_result.url,
            "success": bool(crawl_result.success),
            "status": "success" if crawl_result.success else "error",
            "status_code": crawl_result.status_code,
            "title": extract_title(crawl_result.html),
            "content": markdown,
            "markdown": markdown,
            "cleaned_html": crawl_result.cleaned_html,
            "raw_html": crawl_result.html,
            "metadata": crawl_result.metadata,
            "response_headers": crawl_result.response_headers,
            "error": crawl_result.error_message if not crawl_result.success else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not crawl_result.success:
            logger.warning(
                "Crawl4AI crawl failed for %s: %s",
                original_url,
                crawl_result.error_message,
            )
        else:
            logger.info(
                "Crawl4AI crawl succeeded: %s -> %s (%s)",
                original_url,
                crawl_result.url,
                crawl_result.status_code,
            )

        return result

    except Exception as exc:
        logger.exception("Crawl4AI error while crawling %s", original_url)

        return {
            "url": original_url,
            "final_url": original_url,
            "success": False,
            "status": "error",
            "status_code": None,
            "title": None,
            "content": None,
            "markdown": None,
            "cleaned_html": None,
            "metadata": None,
            "response_headers": None,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
