import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import app as web  # noqa: E402
from didyouship.scanner import CHECK_COUNT, ScanResult  # noqa: E402
from guides_meta import ALL_SLUGS  # noqa: E402
from problems_meta import ALL_PROBLEM_SLUGS  # noqa: E402


@pytest.fixture
def client():
    web.limiter.reset()
    return TestClient(web.app)


def test_health_and_home(client):
    assert client.get("/health").json() == {"status": "ok", "service": "didyouship"}
    assert "didyouship" in client.get("/").text


def test_every_guide_and_problem_page_renders(client):
    for slug in ALL_SLUGS:
        r = client.get(f"/guides/{slug}")
        assert r.status_code == 200, slug
        assert f'href="https://didyouship.com/guides/{slug}"' in r.text
    for slug in ALL_PROBLEM_SLUGS:
        r = client.get(f"/why/{slug}")
        assert r.status_code == 200, slug
        assert f"{CHECK_COUNT} checks" in r.text
    assert client.get("/guides").status_code == 200


def test_unknown_pages_get_custom_404(client):
    for path in ("/guides/nope", "/why/nope", "/nope"):
        r = client.get(path)
        assert r.status_code == 404 and "<html" in r.text.lower()


def test_sitemap_and_robots(client):
    sm = client.get("/sitemap.xml")
    assert sm.headers["content-type"].startswith("application/xml")
    assert sm.text.count("<url>") == 2 + len(ALL_SLUGS) + len(ALL_PROBLEM_SLUGS)
    assert "<loc>https://didyouship.com/</loc>" in sm.text
    assert "Sitemap: https://didyouship.com/sitemap.xml" in client.get("/robots.txt").text


def test_hsts_header(client):
    assert "max-age=31536000" in client.get("/health").headers["strict-transport-security"]


def test_scan_rejects_internal_targets(client):
    for target in ("localhost", "127.0.0.1", "169.254.169.254", "nodot"):
        assert client.get(f"/api/scan/{target}").status_code in (400, 404), target


def test_scan_returns_result_json(client, monkeypatch):
    def fake_scan(domain):
        r = ScanResult(domain=domain, url=f"https://{domain}", score=90, grade="A")
        r.notes = ["skipped"]
        return r
    monkeypatch.setattr(web, "scan", fake_scan)
    data = client.get("/api/scan/www.Example.com").json()
    assert data["domain"] == "example.com" and data["notes"] == ["skipped"] and data["grade"] == "A"


def test_rate_limit_keys_on_real_client_ip(client, monkeypatch):
    monkeypatch.setattr(web, "scan", lambda d: ScanResult(domain=d, url=""))
    for _ in range(10):
        assert client.get("/api/scan/example.com", headers={"CF-Connecting-IP": "1.1.1.1"}).status_code == 200
    assert client.get("/api/scan/example.com", headers={"CF-Connecting-IP": "1.1.1.1"}).status_code == 429
    # a different visitor behind the same proxy is not affected
    assert client.get("/api/scan/example.com", headers={"CF-Connecting-IP": "2.2.2.2"}).status_code == 200


class _Req:
    def __init__(self, headers, host="100.64.0.7"):
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.client = type("C", (), {"host": host})()


def test_client_ip_precedence():
    assert web.client_ip(_Req({"CF-Connecting-IP": "1.1.1.1", "X-Forwarded-For": "9.9.9.9"})) == "1.1.1.1"
    assert web.client_ip(_Req({"X-Forwarded-For": "9.9.9.9, 100.64.0.7"})) == "9.9.9.9"
    assert web.client_ip(_Req({})) == "100.64.0.7"


def test_www_redirects_to_apex_keeping_path_and_query(client):
    r = client.get("/guides/spf-record?ref=x", headers={"Host": "www.didyouship.com"}, follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "https://didyouship.com/guides/spf-record?ref=x"
    assert "strict-transport-security" in r.headers


def test_apex_is_not_redirected(client):
    assert client.get("/health", headers={"Host": "didyouship.com"}).status_code == 200
