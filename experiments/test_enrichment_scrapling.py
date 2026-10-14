"""Offline regression tests for website contact extraction."""

import app.scrapers.enrichment as enrichment
from app.scrapers.enrichment import LeadEnricher


HTML = """
<!doctype html>
<html>
  <head><title>Sample Company</title></head>
  <body>
    <h1>Contact Sample Company</h1>
    <p>Email our team at hello@sampleco.io</p>
    <a href="mailto:support@sampleco.io">Email support</a>
    <a href="tel:+1-415-555-2671">Call us</a>
  </body>
</html>
"""


def test_extract_contacts_from_text():
    enricher = LeadEnricher()

    result = enricher._extract_from_text(
        "Contact hello@sampleco.io or call +1-415-555-2671"
    )

    assert result["email"] == "hello@sampleco.io"
    assert result["phone"] is not None

    print("Contact text extraction: PASS")


def test_deep_scrape_website():
    enricher = LeadEnricher()
    requested_urls = []

    def fake_fetch(url):
        requested_urls.append(url)
        return HTML

    enricher._fetch_page = fake_fetch

    result = enricher._deep_scrape_website("https://sampleco.io")

    assert result["email"] == "hello@sampleco.io"
    assert "hello@sampleco.io" in result["all_emails"]
    assert result["phone"] is not None
    assert requested_urls[0] == "https://sampleco.io"

    print("Website enrichment output: PASS")


def test_scrape_link_page():
    enricher = LeadEnricher()
    enricher._fetch_page = lambda url: HTML

    result = enricher._scrape_link_page("https://sampleco.io/contact")

    assert result["email"] == "hello@sampleco.io"
    assert result["phone"] is not None

    print("Contact-page extraction: PASS")


def test_email_blacklist_is_preserved():
    enricher = LeadEnricher()

    assert enricher._is_valid_email("hello@sampleco.io")
    assert not enricher._is_valid_email("user@example.com")

    print("Email validation rules: PASS")



def test_fetch_page_uses_scout_gateway():
    class FakePage:
        success = True
        status_code = 200
        backend = "http"
        raw_html = HTML

    calls = []

    def fake_fetch(url, backend):
        calls.append((url, backend))
        return FakePage()

    original_fetch = enrichment.fetch_page
    enrichment.fetch_page = fake_fetch

    try:
        result = LeadEnricher()._fetch_page("sampleco.io")
    finally:
        enrichment.fetch_page = original_fetch

    assert result == HTML
    assert calls == [("https://sampleco.io", "auto")]
    print("Scout gateway acquisition: PASS")



def test_gateway_failure_returns_none():
    class FailedPage:
        success = False
        status_code = 403
        backend = "http"
        raw_html = "<html>Blocked</html>"

    original_fetch = enrichment.fetch_page
    enrichment.fetch_page = lambda url, backend: FailedPage()

    try:
        result = LeadEnricher()._fetch_page("sampleco.io")
    finally:
        enrichment.fetch_page = original_fetch

    assert result is None
    print("Gateway failure handling: PASS")


def test_gateway_exception_returns_none():
    original_fetch = enrichment.fetch_page

    def failing_fetch(url, backend):
        raise RuntimeError("Simulated gateway failure")

    enrichment.fetch_page = failing_fetch

    try:
        result = LeadEnricher()._fetch_page("sampleco.io")
    finally:
        enrichment.fetch_page = original_fetch

    assert result is None
    print("Gateway exception handling: PASS")


def test_html_email_extraction():
    enricher = LeadEnricher()
    html = """
    <html>
      <body>
        <p>Contact hello@sampleco.io</p>
        <a href="mailto:press@sampleco.io?subject=Hello">Press</a>
        <script>const address = "embedded@sampleco.io";</script>
        <p>Example user@example.com</p>
      </body>
    </html>
    """

    emails = enricher._extract_emails_from_html(html)

    assert "hello@sampleco.io" in emails
    assert "press@sampleco.io" in emails
    assert "embedded@sampleco.io" in emails
    assert "user@example.com" not in emails
    assert len(emails) == len({email.lower() for email in emails})

    print("Visible, mailto, and embedded email extraction: PASS")


def test_whatsapp_phone_extraction():
    enricher = LeadEnricher()

    phone = enricher._extract_phone_from_text(
        '<a href="https://wa.me/14155552671">WhatsApp</a>'
    )

    assert phone == "+14155552671"
    print("WhatsApp phone extraction: PASS")


def test_email_order_preserves_legacy_html_priority():
    enricher = LeadEnricher()
    html = """
    <html>
      <body>
        <a href="mailto:linkfirst@sampleco.io">Support</a>
        <p>visiblelater@sampleco.io</p>
      </body>
    </html>
    """

    emails = enricher._extract_emails_from_html(html)

    assert emails[0] == "linkfirst@sampleco.io"
    assert "visiblelater@sampleco.io" in emails

    print("Legacy email-selection priority: PASS")


def main():
    test_email_order_preserves_legacy_html_priority()
    test_gateway_failure_returns_none()
    test_gateway_exception_returns_none()
    test_html_email_extraction()
    test_whatsapp_phone_extraction()
    test_fetch_page_uses_scout_gateway()
    test_extract_contacts_from_text()
    test_deep_scrape_website()
    test_scrape_link_page()
    test_email_blacklist_is_preserved()

    print("Enrichment regression tests: PASS")


if __name__ == "__main__":
    main()
