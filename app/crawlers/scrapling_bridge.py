"""
Scout <-> Scrapling bridge.

Architecture:
    Caller
      ↓
    Scrapling bridge
      ↓
    Scout acquisition gateway
      ↓
    Crawl4AI / HTTP
      ↓
    raw HTML
      ↓
    Scrapling Selector
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scrapling.parser import Selector

from .gateway import BackendName, fetch, fetch_async


class ScraplingBridgeError(RuntimeError):
    """Raised when Scout cannot provide HTML for Scrapling."""


@dataclass(slots=True)
class ScraplingPage:
    """
    Parsed Scrapling page together with Scout acquisition metadata.
    """

    selector: Selector
    acquisition: dict[str, Any]

    @property
    def backend(self) -> str | None:
        return self.acquisition.get("backend")

    @property
    def success(self) -> bool:
        return bool(self.acquisition.get("success"))

    @property
    def status_code(self) -> int | None:
        return self.acquisition.get("status_code")

    @property
    def url(self) -> str:
        return self.selector.url

    @property
    def raw_html(self) -> str:
        return self.acquisition.get("raw_html") or ""


def _build_page(result: dict[str, Any], requested_url: str) -> ScraplingPage:
    """
    Convert Scout acquisition output into a Scrapling Selector.
    """
    if not result.get("success"):
        error = result.get("error") or "Unknown acquisition error"
        raise ScraplingBridgeError(
            f"Scout acquisition failed for {requested_url}: {error}"
        )

    html = result.get("raw_html") or ""
    if not html:
        raise ScraplingBridgeError(
            f"Scout returned no raw HTML for {requested_url}"
        )

    final_url = result.get("final_url") or requested_url

    selector = Selector(
        content=html,
        url=final_url,
    )

    return ScraplingPage(
        selector=selector,
        acquisition=result,
    )


def fetch_page(
    url: str,
    backend: BackendName = "auto",
) -> ScraplingPage:
    """
    Acquire a page through Scout and parse it with Scrapling.
    """
    result = fetch(url, backend=backend)
    return _build_page(result, url)


async def fetch_page_async(
    url: str,
    backend: BackendName = "auto",
) -> ScraplingPage:
    """
    Async version of fetch_page().
    """
    result = await fetch_async(url, backend=backend)
    return _build_page(result, url)


__all__ = [
    "ScraplingBridgeError",
    "ScraplingPage",
    "fetch_page",
    "fetch_page_async",
]
