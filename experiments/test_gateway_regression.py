"""Offline regression tests for Scout's shared acquisition gateway."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.crawlers import gateway
from app.crawlers import scrapling_bridge


URL = "https://example.com/"


def result(success=True, html="<html><title>Fixture</title></html>"):
    return {
        "url": URL,
        "final_url": URL,
        "backend": "http",
        "success": success,
        "status": "success" if success else "error",
        "status_code": 200 if success else 503,
        "raw_html": html if success else None,
        "cleaned_html": None,
        "content": None,
        "markdown": None,
        "response_headers": {},
        "metadata": None,
        "error": None if success else "fixture failure",
        "timestamp": "test",
    }


class GatewayTests(unittest.TestCase):
    def test_crawl4ai_success_avoids_http_fallback(self):
        crawl_result = result()
        with (
            patch.object(
                gateway, "crawl_url",
                new_callable=AsyncMock,
                return_value=crawl_result,
            ) as crawl,
            patch.object(gateway, "_http_fetch") as http,
        ):
            output = gateway.fetch(URL, backend="auto")

        self.assertTrue(output["success"])
        self.assertEqual(output["backend"], "crawl4ai")
        crawl.assert_awaited_once_with(URL)
        http.assert_not_called()

    def test_crawl4ai_failure_falls_back_to_http(self):
        with (
            patch.object(
                gateway, "crawl_url",
                new_callable=AsyncMock,
                return_value=result(success=False),
            ),
            patch.object(
                gateway, "_http_fetch", return_value=result()
            ) as http,
        ):
            output = gateway.fetch(URL, backend="auto")

        self.assertTrue(output["success"])
        self.assertEqual(output["backend"], "http")
        http.assert_called_once_with(URL)

    def test_crawl4ai_exception_falls_back_to_http(self):
        with (
            patch.object(
                gateway, "crawl_url",
                new_callable=AsyncMock,
                side_effect=RuntimeError("offline test failure"),
            ),
            patch.object(
                gateway, "_http_fetch", return_value=result()
            ) as http,
        ):
            output = gateway.fetch(URL, backend="auto")

        self.assertTrue(output["success"])
        self.assertEqual(output["backend"], "http")
        http.assert_called_once_with(URL)

    def test_explicit_http_skips_crawl4ai(self):
        with (
            patch.object(
                gateway, "crawl_url", new_callable=AsyncMock
            ) as crawl,
            patch.object(
                gateway, "_http_fetch", return_value=result()
            ) as http,
        ):
            output = gateway.fetch(URL, backend="http")

        self.assertTrue(output["success"])
        self.assertEqual(output["backend"], "http")
        crawl.assert_not_awaited()
        http.assert_called_once_with(URL)

    def test_explicit_crawl4ai_does_not_fall_back(self):
        with (
            patch.object(
                gateway, "crawl_url",
                new_callable=AsyncMock,
                return_value=result(success=False),
            ),
            patch.object(gateway, "_http_fetch") as http,
        ):
            output = gateway.fetch(URL, backend="crawl4ai")

        self.assertFalse(output["success"])
        self.assertEqual(output["backend"], "crawl4ai")
        http.assert_not_called()

    def test_unknown_backend_is_rejected(self):
        with self.assertRaises(ValueError):
            gateway.fetch(URL, backend="unknown")

    def test_scrapling_bridge_parses_gateway_html(self):
        with patch.object(
            scrapling_bridge, "fetch", return_value=result()
        ):
            page = scrapling_bridge.fetch_page(URL, backend="http")

        self.assertTrue(page.success)
        self.assertEqual(page.backend, "http")
        self.assertEqual(page.raw_html, result()["raw_html"])
        self.assertEqual(
            page.selector.css("title::text").get(),
            "Fixture",
        )

    def test_scrapling_bridge_rejects_failed_acquisition(self):
        with patch.object(
            scrapling_bridge, "fetch",
            return_value=result(success=False),
        ):
            with self.assertRaises(scrapling_bridge.ScraplingBridgeError):
                scrapling_bridge.fetch_page(URL, backend="http")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(
        __import__(__name__, fromlist=["*"])
    )
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
