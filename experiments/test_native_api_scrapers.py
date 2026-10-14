"""Offline regression tests for Scout's native API scrapers."""

import unittest
from unittest.mock import patch

from app.scrapers import github, linkedin, twitch


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.url = "https://www.linkedin.com/feed/"

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.last_url = None
        self.last_headers = None

    def get(self, url, headers=None):
        self.last_url = url
        self.last_headers = headers or {}
        return self.response


class GitHubTests(unittest.TestCase):
    def test_profile_mapping(self):
        payload = {
            "login": "alice",
            "name": "Alice Doe",
            "bio": "Builder",
            "email": "alice@example.com",
            "company": "@example",
            "location": "Pune",
            "blog": "https://alice.example",
            "twitter_username": "alice",
            "followers": 120,
            "following": 45,
            "public_repos": 18,
            "hireable": True,
            "html_url": "https://github.com/alice",
        }

        with patch.object(
            github, "get_requests_proxies", return_value=None
        ), patch.object(
            github, "random_user_agent", return_value="ScoutTest/1.0"
        ), patch.object(
            github.requests, "get", return_value=FakeResponse(200, payload)
        ) as mock_get:
            result = github.scrape_profile("alice")

        self.assertEqual(result["username"], "alice")
        self.assertEqual(result["full_name"], "Alice Doe")
        self.assertEqual(result["email"], "alice@example.com")
        self.assertEqual(result["follower_count"], 120)
        self.assertEqual(result["public_repos"], 18)
        self.assertEqual(result["company"], "example")
        self.assertEqual(result["platform"], "github")
        mock_get.assert_called_once()
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://api.github.com/users/alice",
        )

    def test_missing_or_rate_limited_profile_returns_none(self):
        for status in (404, 403):
            with self.subTest(status=status):
                with patch.object(
                    github, "get_requests_proxies", return_value=None
                ), patch.object(
                    github, "random_user_agent", return_value="ScoutTest/1.0"
                ), patch.object(
                    github.requests,
                    "get",
                    return_value=FakeResponse(status),
                ):
                    self.assertIsNone(github.scrape_profile("unknown-user"))


class LinkedInTests(unittest.TestCase):
    def test_missing_cookie_returns_none(self):
        with patch.object(linkedin, "_get_li_cookie", return_value=None):
            self.assertIsNone(
                linkedin.scrape_linkedin_profile("alice")
            )

    def test_profile_mapping_uses_authenticated_api_response(self):
        payload = {
            "included": [
                {
                    "firstName": "Alice",
                    "lastName": "Doe",
                    "publicIdentifier": "alice",
                    "headline": "Founder",
                    "summary": "Hello alice@example.com",
                    "websites": [{"url": "https://alice.example"}],
                    "showVerificationBadge": True,
                    "premium": False,
                    "influencer": False,
                }
            ]
        }
        client = FakeClient(FakeResponse(200, payload))

        with patch.object(
            linkedin, "_get_li_cookie", return_value="x" * 60
        ), patch.object(
            linkedin, "_get_session", return_value=(client, "csrf-test")
        ):
            result = linkedin.scrape_linkedin_profile("alice")

        self.assertEqual(result["username"], "alice")
        self.assertEqual(result["full_name"], "Alice Doe")
        self.assertEqual(result["headline"], "Founder")
        self.assertEqual(result["email"], "alice@example.com")
        self.assertEqual(result["website"], "https://alice.example")
        self.assertEqual(result["platform"], "linkedin")
        self.assertIn("/voyager/api/identity/", client.last_url)
        self.assertEqual(client.last_headers["csrf-token"], "csrf-test")

    def test_unauthorized_response_invalidates_session_cache(self):
        client = FakeClient(FakeResponse(401, {}))
        linkedin._session_cache.update(
            {"client": client, "csrf": "old-token"}
        )

        try:
            with patch.object(
                linkedin, "_get_li_cookie", return_value="x" * 60
            ), patch.object(
                linkedin, "_get_session", return_value=(client, "old-token")
            ):
                result = linkedin.scrape_linkedin_profile("alice")

            self.assertIsNone(result)
            self.assertIsNone(linkedin._session_cache["client"])
            self.assertIsNone(linkedin._session_cache["csrf"])
        finally:
            linkedin._session_cache.update(
                {"client": None, "csrf": None}
            )


class TwitchTests(unittest.TestCase):
    def test_graphql_profile_mapping(self):
        payload = {
            "data": {
                "user": {
                    "id": "123",
                    "login": "alice",
                    "displayName": "Alice",
                    "description": "Streamer alice@example.com",
                    "followers": {"totalCount": 321},
                    "roles": {
                        "isPartner": True,
                        "isAffiliate": False,
                    },
                    "channel": {
                        "socialMedias": [
                            {
                                "name": "Instagram",
                                "url": "https://instagram.com/alice",
                            }
                        ]
                    },
                }
            }
        }

        with patch.object(
            twitch, "get_requests_proxies", return_value=None
        ), patch.object(
            twitch, "random_user_agent", return_value="ScoutTest/1.0"
        ), patch.object(
            twitch.requests, "post", return_value=FakeResponse(200, payload)
        ) as mock_post:
            result = twitch.scrape_profile("Alice")

        self.assertEqual(result["username"], "alice")
        self.assertEqual(result["full_name"], "Alice")
        self.assertEqual(result["follower_count"], 321)
        self.assertTrue(result["is_partner"])
        self.assertFalse(result["is_affiliate"])
        self.assertEqual(result["email"], "alice@example.com")
        self.assertEqual(result["platform"], "twitch")
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://gql.twitch.tv/gql",
        )

    def test_graphql_errors_return_none(self):
        payload = {"errors": [{"message": "test error"}]}

        with patch.object(
            twitch, "get_requests_proxies", return_value=None
        ), patch.object(
            twitch, "random_user_agent", return_value="ScoutTest/1.0"
        ), patch.object(
            twitch.requests, "post", return_value=FakeResponse(200, payload)
        ):
            self.assertIsNone(twitch.scrape_profile("alice"))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(
        __import__(__name__, fromlist=["*"])
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
