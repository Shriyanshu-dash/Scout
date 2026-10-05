"""Local regression tests for Pinterest Scrapling extraction."""

import json

from scrapling.parser import Selector

from app.scrapers.pinterest import (
    _extract_profile_data,
    _extract_profile_data_from_selector,
)


SAMPLE_DATA = {
    "otaData": {"deltas": {}},
    "initialReduxState": {
        "users": {
            "424605208526455283": {
                "username": "pinterest",
                "full_name": "Pinterest",
                "about": "Find your reason to go offline. 📌",
                "website_url": "http://www.pinterest.com",
                "follower_count": 6266053,
                "following_count": 396,
                "pin_count": 97138,
                "board_count": 145,
                "is_verified_merchant": False,
                "verified_identity": {
                    "name": "pinterest",
                    "verified": True,
                },
            }
        }
    },
}


def build_html() -> str:
    payload = json.dumps(SAMPLE_DATA)

    return f"""
    <!doctype html>
    <html>
      <head>
        <script id="__PWS_INITIAL_PROPS__" type="application/json">
          {payload}
        </script>
      </head>
      <body></body>
    </html>
    """


def main() -> None:
    html = build_html()

    selector = Selector(
        content=html,
        url="https://www.pinterest.com/pinterest/",
    )

    primary = _extract_profile_data_from_selector(
        selector,
        "pinterest",
    )

    assert primary is not None
    assert primary["username"] == "pinterest"
    assert primary["full_name"] == "Pinterest"
    assert primary["bio"] == "Find your reason to go offline. 📌"
    assert primary["website"] == "http://www.pinterest.com"
    assert primary["follower_count"] == 6266053
    assert primary["following_count"] == 396
    assert primary["pin_count"] == 97138
    assert primary["board_count"] == 145
    assert primary["verified"] is True
    assert primary["platform"] == "pinterest"

    safe_fallback = _extract_profile_data(
        html,
        "pinterest",
    )

    assert safe_fallback is not None
    assert safe_fallback["username"] == "pinterest"
    assert safe_fallback["full_name"] == "Pinterest"
    assert safe_fallback["follower_count"] == 6266053
    assert safe_fallback["following_count"] == 396
    assert safe_fallback["pin_count"] == 97138
    assert safe_fallback["board_count"] == 145
    assert safe_fallback["verified"] is True

    wrong_user = _extract_profile_data(
        html,
        "not_the_pinterest_user",
    )

    assert wrong_user is None

    print("Pinterest Scrapling regression test: PASS")


if __name__ == "__main__":
    main()
