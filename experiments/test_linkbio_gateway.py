"""Offline gateway and fallback tests for Stan, Linkr, and Bio.link."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scrapling.parser import Selector

from app.scrapers import linktree


PROVIDERS = {
    "stan": linktree.scrape_stan,
    "linkr": linktree.scrape_linkr,
    "biolink": linktree.scrape_biolink,
}


def make_html(platform):
    if platform == "stan":
        return """
        <html>
          <head>
            <script type="application/json">
              {"name":"Stan Demo","description":"Stan profile bio"}
            </script>
          </head>
          <body>
            <a href="https://example.com/stan">Website</a>
          </body>
        </html>
        """

    return f"""
    <html>
      <head>
        <title>Demo {platform.title()} Creator</title>
        <meta name="description" content="Creator profile bio">
      </head>
      <body>
        <a href="https://example.com/profile">Website</a>
        <a href="https://instagram.com/demo">Instagram</a>
      </body>
    </html>
    """


def make_page(platform, html=None):
    url = linktree.PLATFORMS[platform].format(username="demo")
    selector = Selector(
        content=html if html is not None else make_html(platform),
        url=url,
    )
    return SimpleNamespace(selector=selector)


class LinkBioGatewayTests(unittest.TestCase):
    def test_all_providers_use_gateway_primary_path(self):
        for platform, scraper in PROVIDERS.items():
            with self.subTest(platform=platform):
                def fake_fetch(url, backend="auto"):
                    self.assertEqual(
                        url,
                        linktree.PLATFORMS[platform].format(username="demo"),
                    )
                    self.assertEqual(backend, "auto")
                    return make_page(platform)

                with (
                    patch.object(
                        linktree, "fetch_page", side_effect=fake_fetch
                    ) as gateway,
                    patch.object(linktree.requests, "get") as legacy,
                ):
                    result = scraper("demo")

                self.assertIsNotNone(result)
                self.assertEqual(result["username"], "demo")
                self.assertEqual(result["platform"], platform)
                self.assertTrue(result["links"])
                gateway.assert_called_once()
                legacy.assert_not_called()

                if platform == "stan":
                    self.assertEqual(result["full_name"], "Stan Demo")
                    self.assertEqual(result["bio"], "Stan profile bio")
                else:
                    self.assertIn(platform.title(), result["full_name"])
                    self.assertEqual(result["bio"], "Creator profile bio")

    def test_stan_uses_visible_heading_when_embedded_name_is_missing(self):
        html = """
        <html>
          <head>
            <title>Abigail Peugh (@abigailpeugh) | Stan</title>
            <meta property="og:title"
                  content="Abigail Peugh (@abigailpeugh) | Stan">
          </head>
          <body>
            <h1>Abigail Peugh</h1>
            <a href="https://example.com">Website</a>
          </body>
        </html>
        """
        page = make_page("stan", html=html)

        with (
            patch.object(linktree, "fetch_page", return_value=page),
            patch.object(linktree.requests, "get") as legacy,
        ):
            result = linktree.scrape_stan("abigailpeugh")

        self.assertIsNotNone(result)
        self.assertEqual(result["full_name"], "Abigail Peugh")
        self.assertEqual(result["platform"], "stan")
        legacy.assert_not_called()

    def test_gateway_exception_preserves_http_fallback(self):
        for platform, scraper in PROVIDERS.items():
            with self.subTest(platform=platform):
                response = SimpleNamespace(
                    status_code=200,
                    text=make_html(platform),
                )

                with (
                    patch.object(
                        linktree,
                        "fetch_page",
                        side_effect=RuntimeError("offline fixture"),
                    ),
                    patch.object(
                        linktree.requests,
                        "get",
                        return_value=response,
                    ) as legacy,
                ):
                    result = scraper("demo")

                self.assertIsNotNone(result)
                self.assertEqual(result["platform"], platform)
                legacy.assert_called_once()

    def test_unparseable_primary_page_preserves_http_fallback(self):
        for platform, scraper in PROVIDERS.items():
            with self.subTest(platform=platform):
                response = SimpleNamespace(
                    status_code=200,
                    text=make_html(platform),
                )

                with (
                    patch.object(
                        linktree,
                        "fetch_page",
                        return_value=make_page(platform, "<html></html>"),
                    ),
                    patch.object(
                        linktree.requests,
                        "get",
                        return_value=response,
                    ) as legacy,
                ):
                    result = scraper("demo")

                self.assertIsNotNone(result)
                self.assertEqual(result["platform"], platform)
                legacy.assert_called_once()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(
        __import__(__name__, fromlist=["*"])
    )
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
