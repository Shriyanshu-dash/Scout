import asyncio
from pprint import pprint

from app.scrapers.youtube import scrape_channel
from app.crawlers import crawl_url


USERNAME = "@GoogleDevelopers"
URL = "https://www.youtube.com/@GoogleDevelopers"


async def main():
    print("\n" + "=" * 70)
    print("YOUTUBE A/B COMPARISON")
    print("=" * 70)

    # ---------------------------------------------------------
    # A. Existing Scout scraper
    # ---------------------------------------------------------
    print("\n[1] EXISTING SCOUT SCRAPER")
    print("-" * 70)

    old_result = scrape_channel(USERNAME)

    if old_result is None:
        print("Existing Scout scraper: FAILED")
    else:
        print("Existing Scout scraper: SUCCESS")
        pprint(old_result)

    # ---------------------------------------------------------
    # B. Crawl4AI
    # ---------------------------------------------------------
    print("\n[2] CRAWL4AI")
    print("-" * 70)

    crawl_result = await crawl_url(URL)

    print("Success:", crawl_result["success"])
    print("Status:", crawl_result["status_code"])
    print("Final URL:", crawl_result["final_url"])
    print("Title:", crawl_result["title"])
    print("Markdown length:", len(crawl_result["markdown"] or ""))
    print("HTML length:", len(crawl_result["cleaned_html"] or ""))

    # ---------------------------------------------------------
    # C. Extract obvious YouTube signals from Crawl4AI output
    # ---------------------------------------------------------
    html = crawl_result.get("cleaned_html") or ""

    print("\nCrawl4AI HTML signals:")
    for signal in [
        "channelMetadataRenderer",
        "subscriberCountText",
        "canonicalChannelUrl",
        "channelId",
    ]:
        print(f"  {signal}: {signal in html}")

    print("\nCrawl4AI content sample:")
    print((crawl_result.get("markdown") or "")[:2500])

    # ---------------------------------------------------------
    # D. Field comparison
    # ---------------------------------------------------------
    if old_result:
        print("\n" + "=" * 70)
        print("EXISTING SCOUT FIELDS")
        print("=" * 70)

        for key, value in old_result.items():
            print(f"{key}: {value}")

    print("\n" + "=" * 70)
    print("A/B TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
