from fastapi.testclient import TestClient

from src.api import app
from src.filing_view import sanitize_filing_html, validate_filing_url
from src.sec_client import SECClientError

client = TestClient(app)
FILING = "https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm"


def test_validate_filing_url_rejects_other_hosts():
    try:
        validate_filing_url("https://example.com/Archives/edgar/data/1/a.htm")
    except SECClientError as exc:
        assert "SEC EDGAR" in str(exc)
    else:
        raise AssertionError("expected rejection")


def test_sanitize_filing_html_strips_active_content():
    raw = """
    <html><head><style>p{}</style></head><body>
      <script>alert(1)</script>
      <p style="color: red">Revenue $ 281,724</p>
      <p onclick="alert(2)" style="background: url(https://evil.test/x)">note</p>
      <a href="javascript:alert(3)">bad</a>
      <a href="ex991.htm">exhibit</a>
      <img src="https://example.com/logo.png" alt="logo">
    </body></html>
    """
    html = sanitize_filing_html(raw, FILING)
    assert "script" not in html.lower()
    assert "onclick" not in html.lower()
    assert "javascript:" not in html.lower()
    assert "url(" not in html.lower()
    assert "example.com" not in html
    assert "281,724" in html
    assert "color: red" in html
    assert html.count("https://www.sec.gov/") >= 1


def test_filing_endpoint_rejects_external_url():
    response = client.get("/api/filing", params={"url": "https://example.com/secret"})
    assert response.status_code == 400


def test_filing_endpoint_returns_sanitized_html(monkeypatch):
    monkeypatch.setattr(
        "src.api.load_filing_document",
        lambda url: "<p>Revenue 281,724</p>",
    )
    response = client.get("/api/filing", params={"url": FILING})
    assert response.status_code == 200
    assert response.json()["html"] == "<p>Revenue 281,724</p>"
    assert response.json()["filing_url"] == FILING
