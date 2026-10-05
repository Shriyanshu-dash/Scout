"""
Pinterest Profile Scraper

Scrapes public Pinterest user profiles by parsing HTML page data.
Extracts follower counts, pin counts, bio, and website links.

Features:
- Parses embedded JSON from page source
- No authentication required
- Extracts email and phone from bio text
"""

import requests
from typing import Dict, Optional
import logging
import re
import json

from app.scrapers.stealth import random_user_agent, get_requests_proxies
from app.scrapers.utils import extract_email
from app.crawlers import fetch_page

logger = logging.getLogger(__name__)


def scrape_profile(username: str) -> Optional[Dict]:
    """
    Fetch Pinterest profile data.

    Args:
        username: Pinterest username
    """
    username = username.strip().lower()

    url = f'https://www.pinterest.com/{username}/'

    # Scrapling + Scout gateway is the primary Pinterest HTML path.
    # The existing requests parser remains the fallback.
    try:
        page = fetch_page(url, backend='auto')
        profile = _extract_profile_data_from_selector(page.selector, username)

        if profile:
            return profile

        logger.debug(
            "Scrapling Pinterest extraction returned no profile for %s; "
            "using requests fallback.",
            username,
        )
    except Exception as exc:
        logger.debug(
            "Scrapling Pinterest path failed for %s: %s; "
            "using requests fallback.",
            username,
            exc,
        )

    headers = {
        'User-Agent': random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        r = requests.get(url, headers=headers, timeout=20, proxies=get_requests_proxies())

        if r.status_code == 404:
            logger.error(f"Pinterest user {username} not found")
            return None

        if r.status_code != 200:
            logger.error(f"Pinterest error {r.status_code} for {username}")
            return None

        html = r.text

        if 'User not found' in html or "This page isn't available" in html:
            logger.error(f"Pinterest user {username} not found")
            return None

        return _extract_profile_data(html, username)

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching Pinterest profile {username}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Pinterest profile {username}: {e}")
        return None



def _extract_profile_data_from_selector(selector, username: str) -> Optional[Dict]:
    """Extract Pinterest profile data from the scoped PWS initial-props payload."""
    script_text = selector.css("script#__PWS_INITIAL_PROPS__::text").get()

    if not script_text:
        return None

    try:
        data = json.loads(script_text)
    except json.JSONDecodeError:
        return None

    state = data.get("initialReduxState", {})
    users = state.get("users", {})

    if not isinstance(users, dict):
        return None

    target = None

    for user in users.values():
        if (
            isinstance(user, dict)
            and str(user.get("username", "")).lower() == username.lower()
        ):
            target = user
            break

    if not target:
        return None

    verified_identity = target.get("verified_identity")
    if isinstance(verified_identity, dict) and "verified" in verified_identity:
        verified = bool(verified_identity.get("verified"))
    else:
        verified = bool(target.get("is_verified_merchant"))

    return {
        "username": target.get("username", username),
        "full_name": target.get("full_name", ""),
        "bio": target.get("about", ""),
        "email": _extract_email(target.get("about", "")),
        "website": target.get("website_url", ""),
        "follower_count": target.get("follower_count", 0),
        "following_count": target.get("following_count", 0),
        "pin_count": target.get("pin_count", 0),
        "board_count": target.get("board_count", 0),
        "verified": verified,
        "platform": "pinterest",
        "profile_url": f"https://pinterest.com/{username}/",
    }

def _extract_profile_data(html: str, username: str) -> Optional[Dict]:
    """Extract Pinterest profile data from HTML safely."""

    # When Pinterest exposes its structured initial state, use the same
    # identity-safe Scrapling parser as the primary acquisition path.
    # Do not fall through to global regex matching if that payload exists,
    # because unrelated users can appear elsewhere in the page.
    try:
        from scrapling.parser import Selector

        selector = Selector(
            content=html,
            url=f"https://www.pinterest.com/{username}/",
        )

        initial_props = selector.css(
            "script#__PWS_INITIAL_PROPS__::text"
        ).get()

        if initial_props:
            return _extract_profile_data_from_selector(selector, username)

    except Exception as exc:
        logger.debug(
            "Structured Pinterest fallback parser failed for %s: %s",
            username,
            exc,
        )
        return None

    # Legacy regex fallback is retained for older responses that do not
    # contain Pinterest's structured initial-props payload.
    results = {}

    pws_match = re.search(r'<script[^>]*id="__PWS_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if pws_match:
        try:
            pws_data = json.loads(pws_match.group(1))
            user_data = _find_user_in_pws(pws_data, username)
            if user_data:
                results.update(user_data)
        except json.JSONDecodeError:
            pass

    if 'full_name' not in results:
        name_match = re.search(r'"full_name":"([^"]+)"', html)
        if name_match:
            results['full_name'] = _decode_unicode(name_match.group(1))

    if 'follower_count' not in results:
        followers_match = re.search(r'"follower_count":(\d+)', html)
        if followers_match:
            results['follower_count'] = int(followers_match.group(1))

    if 'following_count' not in results:
        following_match = re.search(r'"following_count":(\d+)', html)
        if following_match:
            results['following_count'] = int(following_match.group(1))

    if 'bio' not in results:
        bio_match = re.search(r'"about":"([^"]*)"', html)
        if bio_match:
            results['bio'] = _decode_unicode(bio_match.group(1))

    if 'website' not in results:
        website_match = re.search(r'"website_url":"([^"]+)"', html)
        if website_match:
            results['website'] = website_match.group(1).replace('\\/', '/')

    pin_match = re.search(r'"pin_count":(\d+)', html)
    if pin_match:
        results['pin_count'] = int(pin_match.group(1))

    board_match = re.search(r'"board_count":(\d+)', html)
    if board_match:
        results['board_count'] = int(board_match.group(1))

    verified_match = re.search(r'"is_verified_merchant":true', html)
    results['verified'] = bool(verified_match)

    if 'full_name' not in results and 'follower_count' not in results:
        return None

    bio = results.get('bio', '')

    return {
        'username': username,
        'full_name': results.get('full_name', ''),
        'bio': bio,
        'email': _extract_email(bio),
        'website': results.get('website', ''),
        'follower_count': results.get('follower_count', 0),
        'following_count': results.get('following_count', 0),
        'pin_count': results.get('pin_count', 0),
        'board_count': results.get('board_count', 0),
        'verified': results.get('verified', False),
        'platform': 'pinterest',
        'profile_url': f'https://pinterest.com/{username}/',
    }


def _find_user_in_pws(data: dict, username: str, depth: int = 0) -> Optional[Dict]:
    """Recursively search for user data in PWS JSON."""
    if depth > 15:
        return None

    if isinstance(data, dict):
        if data.get('username', '').lower() == username.lower() and 'follower_count' in data:
            return {
                'full_name': data.get('full_name', ''),
                'bio': data.get('about', ''),
                'follower_count': data.get('follower_count', 0),
                'following_count': data.get('following_count', 0),
                'website': data.get('website_url', ''),
                'pin_count': data.get('pin_count', 0),
                'board_count': data.get('board_count', 0),
            }

        for value in data.values():
            result = _find_user_in_pws(value, username, depth + 1)
            if result:
                return result

    elif isinstance(data, list):
        for item in data:
            result = _find_user_in_pws(item, username, depth + 1)
            if result:
                return result

    return None


def _decode_unicode(text: str) -> str:
    try:
        return text.encode('utf-8').decode('unicode_escape')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


_extract_email = extract_email
