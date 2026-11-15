import base64
import json

import pytest

from didyouship import scanner
from didyouship.scanner import CHECK_COUNT, CHECKS, Issue, is_valid_domain, normalize_domain, scan

from .conftest import FakeResponse


@pytest.mark.parametrize("raw,expected", [
    ("https://www.Example.com/pricing?x=1", "example.com"),
    ("http://example.com:8080/", "example.com"),
    ("founder@mail.example.com", "mail.example.com"),
    ("example.com.", "example.com"),
    ("awww.io", "awww.io"),            # only a leading "www." is stripped
    ("news.www.example.com", "news.www.example.com"),
    ("  EXAMPLE.com  ", "example.com"),
])
def test_normalize_domain(raw, expected):
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize("domain", ["example.com", "sub.example.co.uk", "xn--80ak6aa92e.com", "example.xn--p1ai", "a-b.io"])
def test_valid_domains(domain):
    assert is_valid_domain(domain)


@pytest.mark.parametrize("domain", ["localhost", "127.0.0.1", "10.0.0.1", "exa mple.com", "-bad.com", "com", "", "a.b"])
def test_invalid_domains(domain):
    assert not is_valid_domain(domain)


def test_scan_rejects_internal_targets():
    with pytest.raises(ValueError):
        scan("http://169.254.169.254/latest/meta-data")


def test_check_registry_ids_are_unique():
    ids = [c[0] for c in CHECKS]
    assert len(ids) == len(set(ids)) == CHECK_COUNT


@pytest.mark.parametrize("severities,score,grade", [
    ([], 100, "A"),
    (["critical"], 80, "A"),
    (["critical", "high"], 68, "B"),
    (["critical"] * 3, 40, "C"),
    (["critical"] * 6, 0, "F"),
    (["low", "medium"], 93, "A"),
])
def test_scoring(result, severities, score, grade):
    result.issues = [Issue("x", s, "t", "d") for s in severities]
    scanner._calculate_score(result)
    assert (result.score, result.grade) == (score, grade)


@pytest.mark.parametrize("answer,listed", [
    ("127.0.0.2", True), ("127.0.0.10", True),
    ("127.255.255.254", False),  # Spamhaus: query refused via public resolver
    ("127.255.255.252", False), ("127.0.0.1", False),
])
def test_dnsbl_answer_interpretation(answer, listed):
    assert scanner._is_listing(answer) is listed


# ── email ──

def _titles(r):
    return [i.title for i in r.issues]


def test_missing_spf_and_dmarc_are_critical(result, dns_records):
    dns_records({})
    scanner._check_email(result)
    sev = {i.title: i.severity for i in result.issues}
    assert sev["Gmail can't verify your emails are real"] == "critical"
    assert sev["Anyone can send emails pretending to be @example.com"] == "critical"


def test_spf_plus_all_is_critical(result, dns_records):
    dns_records({("example.com", "TXT"): ["v=spf1 +all"],
                 ("_dmarc.example.com", "TXT"): ["v=DMARC1; p=reject; rua=mailto:d@example.com"]})
    scanner._check_email(result)
    assert _titles(result) == ["Your SPF says anyone can send email as you"]


def test_good_email_setup_passes_and_detects_vendor(result, dns_records):
    dns_records({("example.com", "TXT"): ["google-site-verification=abc", "v=spf1 include:_spf.resend.com ~all"],
                 ("_dmarc.example.com", "TXT"): ["v=DMARC1; p=quarantine; rua=mailto:d@example.com"]})
    scanner._check_email(result)
    assert result.issues == []
    assert "Resend" in result.email_vendors


def test_dmarc_p_none_is_flagged(result, dns_records):
    dns_records({("example.com", "TXT"): ["v=spf1 -all"],
                 ("_dmarc.example.com", "TXT"): ["v=DMARC1; p=none; rua=mailto:d@example.com"]})
    scanner._check_email(result)
    assert _titles(result) == ["Your email protection exists but isn't turned on"]


def test_dkim_skipped_for_non_sending_domain(result, dns_records):
    dns_records({})
    result.raw["email"]["spf"] = "v=spf1 -all"
    scanner._check_dkim(result)
    assert result.issues == []


# ── exposed files ──

def test_spa_catch_all_is_not_an_exposed_env(offline):
    offline.add("https://example.com/.env", "<!doctype html><html><div id=root></div></html>",
                headers={"Content-Type": "text/plain"})
    assert scanner._check_path_exposed("https://example.com", "/.env") is False


def test_real_env_file_is_exposed(offline):
    offline.add("https://example.com/.env", "DATABASE_URL=postgres://x\nSTRIPE_KEY=abc\n",
                headers={"Content-Type": "application/octet-stream"})
    assert scanner._check_path_exposed("https://example.com", "/.env") is True


# ── page fetch: blocked vs broken ──

def test_bot_protection_is_a_note_not_an_issue(offline):
    offline.add("https://example.com", "<title>Just a moment...</title>", status=403)
    r = scan("example.com")
    assert r.notes and "blocks automated requests (HTTP 403)" in r.notes[0]
    assert not any(i.category == "seo" for i in r.issues)


def test_cloudflare_503_challenge_is_blocked_but_plain_503_is_not(offline):
    offline.add("https://example.com", "<html>cf-chl-bypass Just a moment</html>", status=503)
    assert scan("example.com").notes

    offline.add("https://example.com", "Service Unavailable", status=503)
    r = scan("example.com")
    assert r.notes == []
    assert "Could not load your site to check SEO" in _titles(r)


def test_unreachable_site_is_still_reported(offline):
    r = scan("example.com")
    assert "Could not load your site to check SEO" in _titles(r)


# ── www ──

class FakeHTTPS:
    statuses = {}

    def __init__(self, host, timeout=None):
        self.host = host

    def request(self, *a, **k):
        pass

    def getresponse(self):
        return FakeResponse(self.statuses[self.host])

    def close(self):
        pass


def test_www_404_is_flagged(result, monkeypatch):
    import http.client
    FakeHTTPS.statuses = {"example.com": 200, "www.example.com": 404}
    monkeypatch.setattr(http.client, "HTTPSConnection", FakeHTTPS)
    scanner._check_www_redirect(result)
    assert _titles(result) == ["www.example.com shows an error page (HTTP 404)"]


def test_www_redirect_passes(result, monkeypatch):
    import http.client
    FakeHTTPS.statuses = {"example.com": 200, "www.example.com": 301}
    monkeypatch.setattr(http.client, "HTTPSConnection", FakeHTTPS)
    scanner._check_www_redirect(result)
    assert result.issues == [] and result.passed == ["www and apex properly redirect"]


# ── page content ──

def test_mixed_content(result):
    html = '<img src="http://cdn.example.org/a.png"><script src="https://ok.example.org/x.js"></script>' \
           '<a href="http://example.org/">plain link is fine</a><img src="http://localhost/dev.png">'
    scanner._check_mixed_content(result, html)
    assert result.raw["breakage"]["mixed_content"] == ["http://cdn.example.org/a.png"]


def _jwt(payload):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")  # noqa: E731
    return f"{b({'alg': 'HS256'})}.{b(payload)}.c2lnbmF0dXJlLXNpZ25hdHVyZQ"


def test_service_role_key_in_bundle_is_critical_and_not_echoed(result, offline):
    key = _jwt({"iss": "supabase", "role": "service_role", "ref": "abcdefghijklmnopqrst"})
    offline.add("https://example.com/assets/index-1.js", f'createClient("https://x.supabase.co","{key}")',
                headers={"Content-Type": "application/javascript"})
    scanner._check_bundles(result, '<script type="module" src="/assets/index-1.js"></script>')
    [issue] = result.issues
    assert issue.severity == "critical"
    assert "Supabase service_role key (in index-1.js)" in issue.detail
    assert key not in issue.detail + issue.fix


def test_clean_bundles_pass_with_count(result, offline):
    offline.add("https://example.com/a.js", "console.log(1)", headers={"Content-Type": "application/javascript"})
    scanner._check_bundles(result, '<script src="/a.js"></script>')
    assert result.issues == []
    assert "No secret keys in your JS bundles (1 scanned)" in result.passed


def test_public_source_map_is_medium(result, offline):
    offline.add("https://example.com/a.js", "x\n//# sourceMappingURL=a.js.map", headers={"Content-Type": "text/javascript"})
    offline.add("https://example.com/a.js.map", '{"version":3,"sources":["src/App.tsx"]}',
                headers={"Content-Type": "application/json"})
    scanner._check_bundles(result, '<script src="/a.js"></script>')
    assert [(i.severity, i.title) for i in result.issues] == [
        ("medium", "Your original source code is downloadable via source maps")]


# ── proxy fallback ──

class FakeOpener:
    def __init__(self, exc=None):
        self.exc, self.calls = exc, 0

    def open(self, req, timeout=None):
        self.calls += 1
        if self.exc:
            raise self.exc
        return "ok"


@pytest.fixture
def proxy(monkeypatch):
    def install(proxy_exc=None, direct_exc=None):
        p, d = FakeOpener(proxy_exc), FakeOpener(direct_exc)
        monkeypatch.setattr(scanner, "_proxy_opener", p)
        monkeypatch.setattr(scanner, "_direct_opener", d)
        monkeypatch.setattr(scanner, "_proxy_down_until", 0.0)
        return p, d
    return install


def test_healthy_proxy_is_used(proxy):
    p, d = proxy()
    assert scanner._urlopen("https://example.com") == "ok"
    assert (p.calls, d.calls) == (1, 0)


def test_proxy_auth_failure_falls_back_to_direct_and_cools_down(proxy):
    import urllib.error
    p, d = proxy(proxy_exc=urllib.error.URLError("Tunnel connection failed: 407 Proxy Authentication Required"))
    assert scanner._urlopen("https://example.com") == "ok"
    assert scanner._urlopen("https://example.com") == "ok"
    assert (p.calls, d.calls) == (1, 2)  # proxy skipped during cooldown


def test_site_errors_through_proxy_are_not_retried_direct(proxy):
    from .conftest import http_error
    p, d = proxy(proxy_exc=http_error("https://example.com", 403))
    with pytest.raises(Exception) as e:
        scanner._urlopen("https://example.com")
    assert getattr(e.value, "code", None) == 403 and d.calls == 0
