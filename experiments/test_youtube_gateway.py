"""Offline tests for YouTube's Scout gateway and requests fallback."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.scrapers import youtube
from experiments.test_youtube_scrapling import build_html
from app.scrapers.youtube_crawl4ai import extract_profile as real_extract_profile


class YouTubeGatewayTests(unittest.TestCase):
    def test_gateway_success_uses_scrapling_result(self):
        final_url = "https://www.youtube.com/@demo"
        page = SimpleNamespace(
            success=True,
            raw_html="<html>gateway fixture</html>",
            url=final_url,
            backend="http",
            status_code=200,
        )
        profile = {
            "username": "demo",
            "full_name": "Demo Channel",
            "follower_count": 321,
            "channel_id": "UCdemo123456789012345678",
            "profile_url": final_url,
            "platform": "youtube",
            "bio": "Demo description",
            "email": "",
        }

        with (
            patch.object(youtube, "fetch_page", return_value=page) as fetch,
            patch.object(
                youtube, "extract_profile_from_html", return_value=profile
            ) as extract,
            patch.object(youtube.requests, "get") as legacy_get,
            patch.object(
                youtube, "_extract_email_from_description", return_value=""
            ),
        ):
            result = youtube.scrape_channel("@demo")

        self.assertEqual(result["username"], "demo")
        self.assertEqual(result["channel_id"], "UCdemo123456789012345678")
        self.assertEqual(result["platform"], "youtube")
        fetch.assert_called_once_with(final_url, backend="auto")
        extract.assert_called_once_with(
            page.raw_html,
            final_url,
        )
        legacy_get.assert_not_called()

    def test_gateway_failure_uses_requests_fallback(self):
        response = SimpleNamespace(
            status_code=200,
            text=build_html(),
        )

        with (
            patch.object(
                youtube,
                "fetch_page",
                side_effect=RuntimeError("offline gateway failure"),
            ),
            patch.object(
                youtube.requests, "get", return_value=response
            ) as legacy_get,
            patch.object(
                youtube, "random_user_agent", return_value="ScoutTest/1.0"
            ),
            patch.object(
                youtube, "get_requests_proxies", return_value=None
            ),
        ):
            result = youtube.scrape_channel("@GoogleDevelopers")

        self.assertIsNotNone(result)
        self.assertEqual(result["username"], "GoogleDevelopers")
        self.assertEqual(result["channel_id"], "UC_x5XG1OV2P6uZZ5FSM9Ttw")
        self.assertEqual(result["platform"], "youtube")
        legacy_get.assert_called_once()

        request_kwargs = legacy_get.call_args.kwargs
        self.assertEqual(
            request_kwargs["cookies"]["CONSENT"],
            "PENDING+999",
        )

    def test_incomplete_gateway_profile_uses_requests_fallback(self):
        incomplete_profile = {
            "username": "",
            "full_name": "",
            "follower_count": 0,
            "channel_id": "",
            "profile_url": "",
            "platform": "youtube",
            "bio": "",
            "email": "",
        }
        page = SimpleNamespace(
            success=True,
            raw_html="<html>incomplete</html>",
            url="https://www.youtube.com/@GoogleDevelopers",
            backend="http",
            status_code=200,
        )
        response = SimpleNamespace(status_code=200, text=build_html())

        with (
            patch.object(youtube, "fetch_page", return_value=page),
            patch.object(
                youtube,
                "extract_profile_from_html",
                side_effect=lambda html, url: (
                    incomplete_profile
                    if html == "<html>incomplete</html>"
                    else real_extract_profile(html, url)
                ),
            ),
            patch.object(
                youtube.requests, "get", return_value=response
            ) as legacy_get,
            patch.object(
                youtube, "random_user_agent", return_value="ScoutTest/1.0"
            ),
            patch.object(
                youtube, "get_requests_proxies", return_value=None
            ),
        ):
            result = youtube.scrape_channel("@GoogleDevelopers")

        self.assertIsNotNone(result)
        self.assertEqual(result["channel_id"], "UC_x5XG1OV2P6uZZ5FSM9Ttw")
        legacy_get.assert_called_once()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(
        __import__(__name__, fromlist=["*"])
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
