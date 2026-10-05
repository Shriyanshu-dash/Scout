"""Local regression test for the Linktree Scrapling parser."""

import json

from scrapling.parser import Selector

from app.scrapers.linktree import _parse_linktree_selector


SAMPLE_DATA = {
    "props": {
        "pageProps": {
            "account": {
                "username": "demo",
                "pageTitle": "Demo Creator",
                "description": "Example creator profile",
                "links": [
                    {
                        "title": "Website",
                        "url": "https://example.com",
                    },
                    {
                        "title": "YouTube",
                        "url": "https://youtube.com/@demo",
                    },
                ],
            }
        }
    }
}


def main() -> None:
    payload = json.dumps(SAMPLE_DATA)

    html = f"""
    <!doctype html>
    <html>
      <head>
        <script id="__NEXT_DATA__" type="application/json">{payload}</script>
      </head>
      <body></body>
    </html>
    """

    selector = Selector(
        content=html,
        url="https://linktr.ee/demo",
    )

    result = _parse_linktree_selector(selector, "demo")

    assert result is not None
    assert result["username"] == "demo"
    assert result["full_name"] == "Demo Creator"
    assert result["bio"] == "Example creator profile"
    assert result["link_count"] == 2
    assert result["platform"] == "linktree"
    assert result["profile_url"] == "https://linktr.ee/demo"
    assert result["links"][0]["url"] == "https://example.com"
    assert result["links"][1]["url"] == "https://youtube.com/@demo"

    print("Linktree Scrapling regression test: PASS")


if __name__ == "__main__":
    main()
