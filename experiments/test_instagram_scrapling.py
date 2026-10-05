import json

from scrapling.parser import Selector

from app.scrapers.instagram import (
    _extract_profile_from_selector,
)


def build_html(username="instagram"):
    profile = {
        "pk": "25025320",
        "id": "17841400039600391",
        "username": username,
        "profile_pic_url": "https://example.com/profile.jpg",
        "is_private": False,
        "is_unpublished": False,
        "biography": "Discover what's new on Instagram 🔎✨",
        "full_name": "Instagram",
        "is_verified": True,
        "follower_count": 686586312,
        "following_count": 305,
        "all_media_count": 12000,
        "is_memorialized": False,
        "pronouns": [],
        "bio_links": [
            {
                "link_type": "external",
                "url": "https://help.instagram.com",
            }
        ],
    }

    payload = {
        "require": [
            [
                "ScheduledServerJS",
                "handle",
                None,
                [
                    {
                        "__bbox": {
                            "result": {
                                "data": {
                                    "xig_user_by_username": profile
                                }
                            }
                        }
                    }
                ],
            ]
        ]
    }

    return (
        "<html><body>"
        "<script>"
        + json.dumps(payload, ensure_ascii=False)
        + "</script>"
        "</body></html>"
    )


def main():
    html = build_html()
    selector = Selector(
        content=html,
        url="https://www.instagram.com/instagram/",
    )

    result = _extract_profile_from_selector(selector, "instagram")

    assert result is not None
    assert result["username"] == "instagram"
    assert result["full_name"] == "Instagram"
    assert result["bio"] == "Discover what's new on Instagram 🔎✨"
    assert result["follower_count"] == 686586312
    assert result["following_count"] == 305
    assert result["post_count"] == 12000
    assert result["is_verified"] is True
    assert result["is_private"] is False
    assert result["website"] == "https://help.instagram.com"

    wrong = _extract_profile_from_selector(
        selector,
        "definitely_not_instagram_987654",
    )

    assert wrong is None

    print("Instagram Scrapling regression test: PASS")


if __name__ == "__main__":
    main()
