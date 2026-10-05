"""
Test script for the production YouTube scraper using Crawl4AI.

This script tests the integrated production function with real YouTube channels.
"""

import json
from typing import Dict, Optional

from app.scrapers.youtube import scrape_channel
from app.crawlers.crawl4ai_adapter import crawl_url


def test_production_integration():
    """Test the production integration with real YouTube channels."""
    test_channels = [
        "GoogleDevelopers",
        "freecodecamp",
        "Fireship",
    ]

    expected_channel_ids = {
        "GoogleDevelopers": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "freecodecamp": "UC8butISFwT-Wl7EV0hUK0BQ",
        "Fireship": "UCsBjURrPoezykLs9EqgamOA",
    }

    for channel_handle in test_channels:
        print(f"\n=== Testing {channel_handle} ===")
        # Test the synchronous production scrape_channel function.
        profile = scrape_channel(channel_handle)

        if not profile:
            print(f"❌ Failed to fetch profile for {channel_handle}")
            continue

        print(f"Username: {profile.get('username', 'N/A')}")
        print(f"Full Name: {profile.get('full_name', 'N/A')}")
        print(f"Follower Count: {profile.get('follower_count', 'N/A')}")
        print(f"Channel ID: {profile.get('channel_id', 'N/A')}")
        print(f"Profile URL: {profile.get('profile_url', 'N/A')}")
        print(f"Platform: {profile.get('platform', 'N/A')}")

        # Verify required fields
        assert profile.get('username') is not None, "Username must be non-empty"
        assert profile.get('full_name') is not None, "Full name must be non-empty"
        assert profile.get('follower_count') > 0, "Follower count must be positive"
        assert profile.get('channel_id') != "", "Channel ID must be non-empty"
        assert profile.get('profile_url') != "", "Profile URL must be non-empty"
        assert profile.get('platform') == "youtube", "Platform must be 'youtube'"

        # Verify channel ID matches expected value
        assert profile.get('channel_id') == expected_channel_ids[channel_handle], \
            f"Channel ID mismatch for {channel_handle}"

        print(f"✅ All assertions passed for {channel_handle}")


if __name__ == "__main__":
    test_production_integration()