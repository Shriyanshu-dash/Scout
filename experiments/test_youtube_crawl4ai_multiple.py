import asyncio

from crawl4ai import AsyncWebCrawler

from youtube_crawl4ai_profile import extract_profile


CHANNELS = [
    "https://www.youtube.com/@GoogleDevelopers",
    "https://www.youtube.com/@freecodecamp",
    "https://www.youtube.com/@Fireship",
]


async def main():
    async with AsyncWebCrawler() as crawler:

        for url in CHANNELS:
            print("\n" + "=" * 80)
            print("TESTING:", url)
            print("=" * 80)

            try:
                result = await crawler.arun(url)

                print("Success:", result.success)
                print("Status:", result.status_code)

                if not result.success:
                    print("ERROR:", result.error_message)
                    continue

                profile = extract_profile(
                    result.html or "",
                    url,
                )

                print("username:", profile["username"])
                print("full_name:", profile["full_name"])
                print("follower_count:", profile["follower_count"])
                print("video_count:", profile["video_count"])
                print("channel_id:", profile["channel_id"])
                print("website:", profile["website"])
                print("links:", len(profile["links"]))
                print("bio length:", len(profile["bio"]))

            except Exception as exc:
                print("ERROR:", exc)


if __name__ == "__main__":
    asyncio.run(main())
