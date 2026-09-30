import asyncio
import json
import re
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler


URL = "https://www.youtube.com/@GoogleDevelopers"


def parse_count(text: str | None) -> int:
    """
    Parse compact and word-based counts.

    Examples:
        2680000
        2.68m
        11.9 million
        4.29M
        2.3k
        6 thousand
    """
    if not text:
        return 0

    match = re.search(
        r"(\d[\d,]*(?:\.\d+)?)\s*"
        r"(K|M|B|THOUSAND|MILLION|BILLION)?",
        text,
        re.IGNORECASE,
    )

    if not match:
        return 0

    number = float(match.group(1).replace(",", ""))
    suffix = (match.group(2) or "").upper()

    multiplier = {
        "": 1,
        "K": 1_000,
        "THOUSAND": 1_000,
        "M": 1_000_000,
        "MILLION": 1_000_000,
        "B": 1_000_000_000,
        "BILLION": 1_000_000_000,
    }[suffix]

    return int(number * multiplier)


def extract_json_ld(soup: BeautifulSoup) -> dict:
    """
    Extract YouTube channel metadata from Schema.org JSON-LD.
    """
    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        raw = script.string or script.get_text()

        if not raw.strip():
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates = data if isinstance(data, list) else [data]

        for item in candidates:
            if not isinstance(item, dict):
                continue

            if item.get("@type") != "ProfilePage":
                continue

            main_entity = item.get("mainEntity") or {}
            if not isinstance(main_entity, dict):
                main_entity = {}

            same_as = main_entity.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]

            follower_count = 0

            interaction_statistics = main_entity.get(
                "interactionStatistic",
                [],
            )

            if isinstance(interaction_statistics, dict):
                interaction_statistics = [interaction_statistics]

            for statistic in interaction_statistics:
                if not isinstance(statistic, dict):
                    continue

                interaction_type = statistic.get(
                    "interactionType",
                    {},
                )

                if isinstance(interaction_type, dict):
                    interaction_type = interaction_type.get(
                        "@type",
                        "",
                    )

                if str(interaction_type).lower() != "followaction":
                    continue

                count_value = statistic.get(
                    "userInteractionCount",
                )

                follower_count = parse_count(
                    str(count_value)
                )

                if follower_count:
                    break

            return {
                "name": main_entity.get("name") or item.get("name", ""),
                "description": (
                    main_entity.get("description")
                    or item.get("description", "")
                ),
                "url": (
                    main_entity.get("url")
                    or item.get("url", "")
                ),
                "alternate_name": main_entity.get(
                    "alternateName",
                    "",
                ),
                "same_as": same_as,
                "identifier": "",
                "follower_count": follower_count,
            }

    return {}


def extract_channel_id(soup: BeautifulSoup) -> str:
    """
    Extract the canonical YouTube channel ID.
    Prefer the canonical URL, then Schema.org identifier.
    """
    canonical = soup.find("link", rel="canonical")

    if canonical:
        href = canonical.get("href", "")

        match = re.search(
            r"/channel/(UC[A-Za-z0-9_-]{22})",
            href,
        )

        if match:
            return match.group(1)

    identifier = soup.find(
        "meta",
        attrs={
            "itemprop": "identifier",
        },
    )

    if identifier:
        value = identifier.get("content", "")

        if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", value):
            return value

    return ""


def extract_header_stats(soup: BeautifulSoup) -> tuple[int, int]:
    """
    Extract subscriber and video counts from the modern YouTube header.
    """
    page_text = soup.get_text(" ", strip=True)

    subscriber_element = soup.find(
        attrs={"aria-label": re.compile(
            r"subscribers",
            re.IGNORECASE,
        )}
    )

    subscriber_label = (
        subscriber_element.get("aria-label", "")
        if subscriber_element
        else ""
    )

    follower_count = parse_count(subscriber_label)

    video_match = re.search(
        r"([\d.,]+)\s*(K|M|B)?\s+videos",
        page_text,
        re.IGNORECASE,
    )

    video_count = (
        parse_count(video_match.group(0))
        if video_match
        else 0
    )

    return follower_count, video_count


def classify_links(links: list[str]) -> tuple[str, list[str]]:
    """
    Separate the likely primary website from social links.
    """
    social_domains = (
        "instagram.com",
        "tiktok.com",
        "linkedin.com",
        "threads.net",
        "twitter.com",
        "x.com",
        "facebook.com",
        "youtube.com",
        "open.spotify.com",
    )

    website = ""
    social_links: list[str] = []

    for link in links:
        hostname = urlparse(link).netloc.lower()

        if any(domain in hostname for domain in social_domains):
            social_links.append(link)
        elif not website:
            website = link
        else:
            social_links.append(link)

    return website, social_links


def extract_profile(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    json_ld = extract_json_ld(soup)

    # Structured metadata is preferred for identity/description/links.
    full_name = json_ld.get("name", "")
    bio = json_ld.get("description", "")
    canonical_url = json_ld.get("url", "")

    # Handle
    username = json_ld.get("alternate_name", "")

    if username.startswith("@"):
        username = username[1:]

    if not username:
        handle_match = re.search(
            r"(?<!\w)@([A-Za-z0-9._-]+)",
            soup.get_text(" ", strip=True),
        )
        if handle_match:
            username = handle_match.group(1)

    # Fallback name from modern page header
    if not full_name:
        name_element = soup.select_one(
            "yt-dynamic-text-view-model h1"
        )

        if name_element:
            full_name = name_element.get_text(
                " ",
                strip=True,
            )

    # Fallback canonical URL
    if not canonical_url:
        canonical_element = soup.find(
            "link",
            rel="canonical",
        )

        if canonical_element:
            canonical_url = canonical_element.get(
                "href",
                "",
            )

    if not canonical_url:
        canonical_url = url

    channel_id = extract_channel_id(soup)

    follower_count, video_count = extract_header_stats(soup)

    same_as = json_ld.get("same_as", [])

    if not isinstance(same_as, list):
        same_as = []

    same_as = [
        unquote(link)
        for link in same_as
        if isinstance(link, str) and link.startswith("http")
    ]

    website, social_links = classify_links(same_as)

    return {
        "username": username,
        "full_name": full_name,
        "bio": bio,
        "email": "",
        "follower_count": follower_count,
        "website": website,
        "links": same_as,
        "social_links": social_links,
        "channel_id": channel_id,
        "video_count": video_count,
        "platform": "youtube",
        "profile_url": canonical_url,
    }


async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(URL)

    print("\n=== CRAWL4AI YOUTUBE STRUCTURED EXTRACTION ===")
    print("Success:", result.success)
    print("Status:", result.status_code)

    if not result.success:
        print("ERROR:", result.error_message)
        return

    profile = extract_profile(
        result.html or "",
        URL,
    )

    for key, value in profile.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
