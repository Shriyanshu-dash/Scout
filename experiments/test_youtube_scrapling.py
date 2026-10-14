import json

from app.scrapers.youtube_crawl4ai import extract_profile


CHANNEL_ID = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
CHANNEL_URL = f"https://www.youtube.com/channel/{CHANNEL_ID}"
DESCRIPTION = (
    "Learn the latest in Google technology — from AI and cloud, "
    "to mobile and web."
)

SAME_AS = [
    "https://www.linkedin.com/showcase/googledevelopers/",
    "https://developers.google.com/",
]


def build_html(include_jsonld=True):
    main_entity = {
        "@type": "Person",
        "name": "Google for Developers",
        "url": CHANNEL_URL,
        "alternateName": "@GoogleDevelopers",
        "description": DESCRIPTION,
        "sameAs": SAME_AS,
        "interactionStatistic": [
            {
                "@type": "InteractionCounter",
                "interactionType": {"@type": "FollowAction"},
                "userInteractionCount": "2680000",
            }
        ],
    }

    jsonld = {
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "url": CHANNEL_URL,
        "name": "Google for Developers - YouTube",
        "description": DESCRIPTION,
        "mainEntity": main_entity,
    }

    script = ""
    if include_jsonld:
        script = (
            '<script type="application/ld+json">'
            + json.dumps(jsonld, ensure_ascii=False)
            + "</script>"
        )

    return f"""<!doctype html>
    <html>
      <head>
        <link rel="canonical" href="{CHANNEL_URL}">
        <meta itemprop="identifier" content="{CHANNEL_ID}">
        {script}
      </head>
      <body>
        <yt-dynamic-text-view-model>
          <h1>Google for Developers</h1>
        </yt-dynamic-text-view-model>
        <div aria-label="2.68 million subscribers"></div>
        <div>6.1k videos</div>
        <p>@GoogleDevelopers</p>
      </body>
    </html>
    """


def test_structured_profile():
    result = extract_profile(
        build_html(),
        "https://www.youtube.com/@GoogleDevelopers",
    )

    assert result["username"] == "GoogleDevelopers"
    assert result["full_name"] == "Google for Developers"
    assert result["bio"] == DESCRIPTION
    assert result["follower_count"] == 2_680_000
    assert result["website"] == "https://developers.google.com/"
    assert result["links"] == SAME_AS
    assert result["social_links"] == [
        "https://www.linkedin.com/showcase/googledevelopers/"
    ]
    assert result["channel_id"] == CHANNEL_ID
    assert result["video_count"] == 6_100
    assert result["platform"] == "youtube"
    assert result["profile_url"] == CHANNEL_URL


def test_header_fallback_without_jsonld():
    result = extract_profile(
        build_html(include_jsonld=False),
        "https://www.youtube.com/@GoogleDevelopers",
    )

    assert result["username"] == "GoogleDevelopers"
    assert result["full_name"] == "Google for Developers"
    assert result["follower_count"] == 2_680_000
    assert result["channel_id"] == CHANNEL_ID
    assert result["video_count"] == 6_100
    assert result["platform"] == "youtube"


def main():
    test_structured_profile()
    test_header_fallback_without_jsonld()
    print("YouTube Scrapling regression test: PASS")
    print("Structured JSON-LD extraction: PASS")
    print("Header fallback without JSON-LD: PASS")


if __name__ == "__main__":
    main()
