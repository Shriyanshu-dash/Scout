"""Offline tests for safe Instagram post-count backfilling."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scrapling.parser import Selector

from app.scrapers import instagram
from experiments.test_instagram_scrapling import build_html


class InstagramCountBackfillTests(unittest.TestCase):
    def setUp(self):
        self.username = "instagram"
        self.url = "https://www.instagram.com/instagram/"
        self.html = build_html().replace(
            '"all_media_count": 12000',
            '"all_media_count": null',
        )
        selector = Selector(content=self.html, url=self.url)
        self.page = SimpleNamespace(
            success=True,
            raw_html=self.html,
            url=self.url,
            status_code=200,
            selector=selector,
        )

    def run_scraper_with_legacy_result(self, legacy_profile):
        with (
            patch.object(
                instagram, "fetch_page", return_value=self.page
            ),
            patch.object(
                instagram,
                "_extract_profile_from_html",
                return_value=legacy_profile,
            ) as legacy,
        ):
            profile = instagram.scrape_profile_no_login(self.username)
        return profile, legacy

    def test_exact_username_legacy_count_is_backfilled(self):
        profile, legacy = self.run_scraper_with_legacy_result({
            "username": "instagram",
            "post_count": 8620,
        })

        self.assertIsNotNone(profile)
        self.assertEqual(profile["username"], "instagram")
        self.assertEqual(profile["post_count"], 8620)
        legacy.assert_called_once()

    def test_other_username_count_is_never_backfilled(self):
        profile, legacy = self.run_scraper_with_legacy_result({
            "username": "different_account",
            "post_count": 8620,
        })

        self.assertIsNotNone(profile)
        self.assertEqual(profile["username"], "instagram")
        self.assertEqual(profile["post_count"], 0)
        legacy.assert_called_once()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(
        __import__(__name__, fromlist=["*"])
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
