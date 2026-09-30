import asyncio
import re

from crawl4ai import AsyncWebCrawler


URL = "https://www.youtube.com/@GoogleDevelopers"


def parse_subscribers(text: str) -> int:
    match = re.search(
        r'([\d.,]+)\s*([KMB])?\s+subscribers',
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
        "M": 1_000_000,
        "B": 1_000_000_000,
    }[suffix]

    return int(number * multiplier)


def extract_youtube_profile(markdown: str, url: str) -> dict:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]

    full_name = ""
    username = ""
    bio = ""
    follower_count = parse_subscribers(markdown)

    for line in lines:
        if line.startswith("# ") and not full_name:
            full_name = line[2:].strip()

        if line.startswith("@") and " " not in line:
            username = line[1:].strip()

    # Use the first substantial paragraph after the channel header
    # as a preliminary bio candidate.
    header_index = -1

    for i, line in enumerate(lines):
        if username and line == f"@{username}":
            header_index = i
            break

    if header_index >= 0:
        for line in lines[header_index + 1:]:
            if "subscribers" in line.lower():
                continue
            if line.startswith("Subscribe"):
                continue
            if len(line) > 40:
                bio = line
                break

    return {
        "username": username,
        "full_name": full_name,
        "bio": bio,
        "email": "",
        "follower_count": follower_count,
        "website": "",
        "links": [],
        "channel_id": "",
        "platform": "youtube",
        "profile_url": url,
    }


async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(URL)

    print("\n=== CRAWL4AI YOUTUBE EXTRACTION EXPERIMENT ===")
    print("Success:", result.success)

    if not result.success:
        print("ERROR:", result.error_message)
        return

    markdown = result.markdown.raw_markdown

    profile = extract_youtube_profile(markdown, URL)

    for key, value in profile.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
