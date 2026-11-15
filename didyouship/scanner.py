"""
didyouship — production readiness scanner.

Every check answers "what breaks if I don't fix this?", using only public
data (DNS, TLS, HTTP). No access to the scanned server is needed.
The full list lives in CHECKS below.
"""

from __future__ import annotations

import logging
import os
import ssl
import socket
import time
import re
import gzip
import zlib
import urllib.request
import urllib.error
import dns.resolver
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from dataclasses import dataclass, field

from .bundles import scan_bundles
from .secrets import find_secrets

# One entry per check: (id, category, what it looks at). Used for the check
# count shown on the site, in the API description and in the README.
CHECKS = [
    ("spf", "email", "SPF record"),
    ("dmarc", "email", "DMARC record and policy"),
    ("dmarc-reporting", "email", "DMARC reporting address"),
    ("mx", "email", "MX records and email provider"),
    ("dkim", "email", "DKIM on common selectors"),
    ("blacklist", "email", "Mail server IP on spam blacklists"),
    ("ssl", "ssl", "TLS certificate validity and expiry"),
    ("https-redirect", "ssl", "HTTP to HTTPS redirect"),
    ("env-file", "secrets", "Public /.env file"),
    ("git-dir", "secrets", "Public /.git directory"),
    ("html-secrets", "secrets", "Secret keys in page HTML"),
    ("bundle-secrets", "secrets", "Secret keys in the site's JS bundles"),
    ("source-maps", "secrets", "Public JS source maps"),
    ("www", "dns", "www subdomain resolves"),
    ("www-redirect", "dns", "www and apex don't serve duplicate sites"),
    ("hsts", "security", "HSTS header"),
    ("title", "seo", "Title tag"),
    ("meta-description", "seo", "Meta description"),
    ("open-graph", "seo", "Open Graph tags"),
    ("twitter-card", "seo", "Twitter/X card"),
    ("viewport", "seo", "Viewport meta tag"),
    ("canonical", "seo", "Canonical URL"),
    ("sitemap", "seo", "sitemap.xml"),
    ("favicon", "seo", "Favicon"),
    ("response-time", "performance", "Response time and cold starts"),
    ("compression", "performance", "gzip/brotli compression"),
    ("mixed-content", "breakage", "HTTP resources on an HTTPS page"),
    ("custom-404", "polish", "Custom 404 page"),
]
CHECK_COUNT = len(CHECKS)

_DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$")


def normalize_domain(value: str) -> str:
    """Reduce a URL, email address or hostname to a bare apex-style domain."""
    d = value.strip().lower()
    if "@" in d:
        d = d.rsplit("@", 1)[-1]
    for prefix in ("https://", "http://"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    d = d.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0].split(":", 1)[0].rstrip(".")
    if d.startswith("www."):
        d = d[4:]
    return d


def is_valid_domain(domain: str) -> bool:
    """A public hostname with a letter TLD. IPs, localhost, ports are rejected."""
    return bool(_DOMAIN_RE.match(domain))


@dataclass
class Issue:
    category: str       # email, ssl, secrets, dns, security, seo, performance, breakage, polish
    severity: str       # critical, high, medium, low
    title: str          # human-readable, no jargon
    detail: str         # what breaks + why it matters
    fix: str = ""       # actionable fix instruction


@dataclass
class ScanResult:
    domain: str
    url: str = ""
    score: int = 0
    grade: str = "F"
    issues: list[Issue] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)  # informational; never affects the score
    email_vendors: list[str] = field(default_factory=list)
    mx_vendors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """JSON shape shared by the web API and the CLI's --json output."""
        return {
            "domain": self.domain,
            "score": self.score,
            "grade": self.grade,
            "issues": [
                {"category": i.category, "severity": i.severity, "title": i.title, "detail": i.detail, "fix": i.fix}
                for i in self.issues
            ],
            "passed": self.passed,
            "notes": self.notes,
            "issue_count": len(self.issues),
            "critical_count": sum(1 for i in self.issues if i.severity == "critical"),
            "high_count": sum(1 for i in self.issues if i.severity == "high"),
            "email_vendors": self.email_vendors,
            "mx_vendors": self.mx_vendors,
            "ssl": self.raw.get("ssl", {}),
            "raw": self.raw,
        }


DNS_TIMEOUT = 5
HTTP_TIMEOUT = 10

# ── Proxy support ────────────────────────────────────────────────────────────
# Set SCAN_PROXY to route HTTP requests through a proxy (http://user:pass@host:port).
# If the proxy itself fails (bad credentials, down), requests fall back to a
# direct connection and the proxy is skipped for PROXY_COOLDOWN seconds, so a
# broken proxy never shows up as a problem with the scanned site.
_PROXY_URL = os.environ.get("SCAN_PROXY", "")
PROXY_COOLDOWN = 600

_direct_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_proxy_opener = (
    urllib.request.build_opener(urllib.request.ProxyHandler({"http": _PROXY_URL, "https": _PROXY_URL}))
    if _PROXY_URL else None
)
_proxy_down_until = 0.0
_log = logging.getLogger("didyouship.scanner")


def _is_proxy_failure(exc: Exception) -> bool:
    """True when the error came from the proxy, not from the scanned site."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code == 407  # plain-http requests: the proxy answers directly
    if isinstance(exc, urllib.error.URLError):
        reason = str(exc.reason).lower()
        return "tunnel connection failed" in reason or "proxy" in reason or isinstance(
            exc.reason, ConnectionRefusedError)
    return False


def _urlopen(req, timeout=HTTP_TIMEOUT):
    """urlopen through SCAN_PROXY when configured and healthy, otherwise direct."""
    global _proxy_down_until
    if _proxy_opener is not None and time.time() >= _proxy_down_until:
        try:
            return _proxy_opener.open(req, timeout=timeout)
        except Exception as exc:
            if not _is_proxy_failure(exc):
                raise
            _proxy_down_until = time.time() + PROXY_COOLDOWN
            _log.warning("SCAN_PROXY failed (%s); going direct for %ds", exc, PROXY_COOLDOWN)
    return _direct_opener.open(req, timeout=timeout)


def dns_query(qname, qtype, lifetime=None):
    """DNS query with up to 3 attempts; only NXDOMAIN is treated as permanent."""
    if lifetime is None:
        lifetime = DNS_TIMEOUT
    last_exc = None
    for attempt in range(3):
        try:
            return list(dns.resolver.resolve(qname, qtype, lifetime=lifetime))
        except dns.resolver.NXDOMAIN:
            raise  # domain doesn't exist — never retry
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(0.2 * (attempt + 1))  # 0.2s, 0.4s back-off
    raise last_exc

# ── Vendor maps ──────────────────────────────────────────────────────────────

SPF_VENDORS = {
    "sendgrid": "SendGrid", "sparkpost": "SparkPost", "mailgun": "Mailgun",
    "postmark": "Postmark", "amazonses": "Amazon SES", "google": "Google Workspace",
    "outlook": "Microsoft 365", "mailchimp": "Mailchimp", "mandrillapp": "Mailchimp",
    "hubspot": "HubSpot", "zendesk": "Zendesk", "salesforce": "Salesforce",
    "intercom": "Intercom", "freshdesk": "Freshdesk", "klaviyo": "Klaviyo",
    "braze": "Braze", "customer.io": "Customer.io", "mailjet": "Mailjet",
    "sendinblue": "Brevo", "resend": "Resend",
}

MX_VENDORS = {
    "google": "Google Workspace", "googlemail": "Google Workspace",
    "outlook": "Microsoft 365", "pphosted": "Proofpoint",
    "mimecast": "Mimecast", "zoho": "Zoho Mail",
    "emailsecurity": "Cloudflare Email", "mx.cloudflare": "Cloudflare Email",
}

# ── DKIM selectors to probe (covers 95% of providers vibe coders use) ────────

DKIM_SELECTORS = [
    "default", "google", "mail", "dkim", "selector1", "selector2",
    "k1", "s1", "s2", "resend", "smtp", "email", "postmark",
    "amazonses", "sendgrid", "mailgun",
]

# ── Public DNSBL servers ──────────────────────────────────────────────────────

DNSBL_SERVERS = [
    ("zen.spamhaus.org",        "Spamhaus"),
    ("b.barracudacentral.org",  "Barracuda"),
    ("bl.spamcop.net",          "SpamCop"),
]

# ── Main entry ───────────────────────────────────────────────────────────────

def scan(domain: str) -> ScanResult:
    """Run every check in CHECKS against a domain (URLs and emails are normalized)."""
    domain = normalize_domain(domain)
    if not is_valid_domain(domain):
        raise ValueError(f"Not a public domain name: {domain!r}")

    r = ScanResult(domain=domain, url=f"https://{domain}")
    r.raw = {
        "email": {}, "ssl": {}, "headers": {}, "dns": {},
        "seo": {}, "performance": {}, "secrets": {}, "breakage": {},
    }

    with ThreadPoolExecutor(max_workers=10) as pool:
        # Start slow I/O checks immediately — no page HTML needed.
        # Each check writes only its own r.raw[...] key; ssl + redirect share
        # r.raw["ssl"], so they run sequentially in one task.
        email_future = pool.submit(_check_email, r)
        futures = [
            email_future,
            pool.submit(_check_blacklist, r),
            pool.submit(_check_ssl_and_redirect, r),
            pool.submit(_check_dns, r),
            pool.submit(_check_404, r),
        ]

        # Fetch page in main thread — provides html/headers for remaining checks
        html, headers, fetch_ok = _fetch_page(r)

        # DKIM must run after email check (reads r.raw["email"]["spf"])
        email_future.result()
        futures.append(pool.submit(_check_dkim, r))

        # Submit html-dependent checks now that fetch is done
        futures += [
            pool.submit(_check_secrets, r, html),
            pool.submit(_check_bundles, r, html),
            pool.submit(_check_security_headers, r, headers),
            pool.submit(_check_seo, r, html, fetch_ok),
            pool.submit(_check_performance, r, html, headers),
            pool.submit(_check_mixed_content, r, html),
        ]

        # Wait for all; each check handles its own exceptions internally
        for f in futures:
            try:
                f.result()
            except Exception:
                pass

    _calculate_score(r)
    return r


def _check_ssl_and_redirect(r: ScanResult):
    """Run SSL and HTTPS-redirect checks sequentially (they share r.raw['ssl'])."""
    _check_ssl(r)
    _check_https_redirect(r)


# ── Page fetch (shared) ─────────────────────────────────────────────────────

def _fetch_page(r: ScanResult) -> tuple[str, dict, bool]:
    """Fetch the main page. Returns (html, headers_dict, success).
    Retries once on failure. Used by SEO, headers, performance, secrets."""
    for attempt in range(2):
        try:
            # First request = warmup (for cold start detection)
            t0 = time.time()
            req = urllib.request.Request(r.url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)",
                "Accept-Encoding": "gzip, deflate",  # no br — urllib can't decompress Brotli
            })
            resp = _urlopen(req, timeout=HTTP_TIMEOUT + attempt * 5)
            warmup_time = time.time() - t0

            raw_bytes = resp.read()
            encoding = resp.headers.get("Content-Encoding", "").lower()

            # Decompress manually — urllib doesn't auto-decompress
            if "gzip" in encoding:
                raw_bytes = gzip.decompress(raw_bytes)
            elif "deflate" in encoding:
                try:
                    raw_bytes = zlib.decompress(raw_bytes)
                except zlib.error:
                    raw_bytes = zlib.decompress(raw_bytes, -zlib.MAX_WBITS)

            html = raw_bytes.decode("utf-8", errors="ignore")
            headers = {k.lower(): v for k, v in resp.headers.items()}

            r.raw["headers"] = dict(resp.headers)
            r.raw["performance"]["warmup_time"] = round(warmup_time, 2)
            r.raw["performance"]["encoding"] = encoding
            r.raw["performance"]["page_size"] = len(html)

            # Second request = measure real response time (post-warmup)
            t1 = time.time()
            req2 = urllib.request.Request(r.url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)",
            })
            _urlopen(req2, timeout=HTTP_TIMEOUT)
            response_time = time.time() - t1
            r.raw["performance"]["response_time"] = round(response_time, 2)

            return html, headers, True

        except urllib.error.HTTPError as e:
            if _looks_blocked(e):
                # Bot protection (Cloudflare challenge, WAF, rate limit): the site
                # works for people, we just can't see it. Not the site's fault.
                r.raw["performance"]["blocked"] = e.code
                r.notes.append(
                    f"{r.url} blocks automated requests (HTTP {e.code}), so page-level "
                    "checks (SEO, headers, secrets in HTML/JS, speed) were skipped. "
                    "DNS, email and TLS checks still ran.")
                return "", {}, False
            if attempt == 0:
                continue
            r.raw["performance"]["error"] = f"HTTP {e.code}"
            return "", {}, False
        except Exception as e:
            if attempt == 0:
                continue  # retry once
            r.raw["performance"]["error"] = str(e)
            return "", {}, False


_CHALLENGE_MARKERS = ("cf-chl", "just a moment", "attention required", "captcha", "challenge-platform")


def _looks_blocked(e: urllib.error.HTTPError) -> bool:
    """True when an HTTP error is bot protection rather than a broken site."""
    if e.code in (401, 403, 429):
        return True
    if e.code == 503:
        try:
            body = e.read(4096).decode("utf-8", errors="ignore").lower()
        except Exception:
            body = ""
        return any(m in body for m in _CHALLENGE_MARKERS)
    return False


# ── CATEGORY 1: Email ────────────────────────────────────────────────────────

def _check_email(r: ScanResult):
    """SPF, DMARC, DMARC reporting, MX records."""

    # ── SPF record ──
    spf_record = None
    vendors = []
    try:
        for rdata in dns_query(r.domain, "TXT"):
            txt = rdata.to_text().strip('"')
            if txt.startswith("v=spf1"):
                spf_record = txt
                for frag, name in SPF_VENDORS.items():
                    if frag in txt.lower() and name not in vendors:
                        vendors.append(name)
    except Exception:
        pass

    r.raw["email"]["spf"] = spf_record
    r.raw["email"]["vendors"] = vendors
    r.email_vendors = vendors

    if not spf_record:
        r.issues.append(Issue("email", "critical",
            "Gmail can't verify your emails are real",
            f"Your domain has no SPF record. Email providers like Gmail see emails "
            f"from @{r.domain} as unverified and send them to spam.",
            "Add a TXT record to your DNS:\nv=spf1 include:_spf.google.com ~all\n"
            "(Replace the include with your email provider.)"))
    elif "+all" in spf_record or "?all" in spf_record:
        mech = spf_record.split()[-1]
        r.issues.append(Issue("email", "critical",
            "Your SPF says anyone can send email as you",
            f"Your SPF record ends with {mech}, which means ANY server in the world "
            f"can send email as @{r.domain}.",
            f"Change {mech} to ~all or -all in your SPF TXT record."))
    elif "~all" in spf_record:
        r.passed.append("SPF record exists (~all softfail)")
    else:
        r.passed.append("SPF record configured correctly")

    # ── DMARC record ──
    dmarc_record = None
    dmarc_policy = None
    dmarc_rua = None
    try:
        for rdata in dns_query(f"_dmarc.{r.domain}", "TXT"):
            txt = rdata.to_text().strip('"')
            if "v=DMARC1" in txt:
                dmarc_record = txt
                for part in txt.split(";"):
                    p = part.strip()
                    if p.startswith("p="):
                        dmarc_policy = p[2:].strip()
                    elif p.startswith("rua="):
                        dmarc_rua = p[4:].strip()
    except Exception:
        pass

    r.raw["email"]["dmarc"] = dmarc_record
    r.raw["email"]["dmarc_policy"] = dmarc_policy

    if not dmarc_record:
        r.issues.append(Issue("email", "critical",
            f"Anyone can send emails pretending to be @{r.domain}",
            "Your domain has no DMARC record. This means: (1) anyone can spoof your "
            "email, and (2) Gmail/Outlook penalize your domain, so even your real "
            "emails are more likely to land in spam.",
            f"Add a TXT record at _dmarc.{r.domain}:\n"
            f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{r.domain}"))
    elif dmarc_policy == "none":
        r.issues.append(Issue("email", "high",
            "Your email protection exists but isn't turned on",
            "Your DMARC policy is set to p=none (monitoring only). Spoofed emails "
            "from your domain are still delivered normally. It's like having a "
            "security camera but no lock on the door.",
            "Change p=none to p=quarantine in your DMARC TXT record once "
            "you've verified your legit emails pass SPF/DKIM."))
    elif dmarc_policy == "quarantine":
        r.passed.append("DMARC enforced (quarantine)")
    elif dmarc_policy == "reject":
        r.passed.append("DMARC fully enforced (reject)")

    # ── DMARC reporting ──
    if dmarc_record and not dmarc_rua:
        r.issues.append(Issue("email", "medium",
            "You won't know when someone spoofs your email",
            "Your DMARC record doesn't include a reporting address (rua=). "
            "You'll never find out if someone is sending phishing emails "
            "pretending to be you.",
            f"Add rua=mailto:dmarc@{r.domain} to your DMARC TXT record."))
    elif dmarc_record and dmarc_rua:
        r.passed.append("DMARC reporting configured")

    # ── MX records (informational) ──
    mx_hosts = []
    mx_vendors_found = []
    try:
        for rdata in dns_query(r.domain, "MX"):
            mx = str(rdata.exchange).rstrip(".")
            mx_hosts.append(mx)
            for frag, name in MX_VENDORS.items():
                if frag in mx.lower() and name not in mx_vendors_found:
                    mx_vendors_found.append(name)
    except Exception:
        pass

    r.raw["email"]["mx_hosts"] = mx_hosts
    r.raw["email"]["mx_vendors"] = mx_vendors_found
    r.mx_vendors = mx_vendors_found


def _check_dkim(r: ScanResult):
    """Check that DKIM is configured by probing common selectors."""
    found_selector = None
    for selector in DKIM_SELECTORS:
        try:
            records = dns_query(f"{selector}._domainkey.{r.domain}", "TXT", lifetime=2)
            for rdata in records:
                txt = rdata.to_text().strip('"')
                if "v=DKIM1" in txt or "k=rsa" in txt or "k=ed25519" in txt:
                    found_selector = selector
                    break
        except Exception:
            continue
        if found_selector:
            break

    r.raw["email"]["dkim_selector"] = found_selector

    spf_rejects_all = r.raw["email"].get("spf") and "-all" in (r.raw["email"]["spf"] or "")

    if found_selector:
        r.passed.append(f"DKIM configured ({found_selector} selector)")
    elif spf_rejects_all:
        # SPF -all means no email is sent from this domain — DKIM is not needed
        r.passed.append("DKIM not required (domain sends no email, SPF -all)")
    else:
        r.issues.append(Issue("email", "high",
            "Emails have no cryptographic signature (DKIM missing)",
            "We checked 16 common DKIM selectors and found none configured. "
            "Without DKIM, Gmail can't verify your emails are genuine — even with "
            "SPF and DMARC in place. This alone can push emails to spam.",
            "Check your email provider's setup guide:\n"
            "• Resend: Domains → your domain → copy the TXT record\n"
            "• Google Workspace: Admin Console → Apps → Gmail → Authenticate email\n"
            "• Postmark: Sending Domains → DKIM settings\n"
            "Note: if you use a custom DKIM selector, this check may be a false negative."))


def _is_listing(answer: str) -> bool:
    """A DNSBL hit is 127.0.0.2-127.0.0.255. Spamhaus answers 127.255.255.x when it
    refuses the query (e.g. sent via a public resolver); that is not a listing."""
    return answer.startswith("127.0.0.") and answer != "127.0.0.1"


def _check_blacklist(r: ScanResult):
    """Check if the domain's mail server IP appears on major spam blacklists."""
    # Resolve the lowest-priority MX host to an IP
    mx_ip = None
    try:
        mx_records = dns_query(r.domain, "MX")
        mx_host = str(min(mx_records, key=lambda x: x.preference).exchange).rstrip(".")
        a_records = dns_query(mx_host, "A")
        mx_ip = str(a_records[0])
    except Exception:
        pass

    if not mx_ip:
        r.raw["email"]["blacklist"] = {"skipped": "no MX record resolved"}
        return

    listed_on = []
    reversed_ip = ".".join(reversed(mx_ip.split(".")))
    for dnsbl, name in DNSBL_SERVERS:
        try:
            answers = dns.resolver.resolve(f"{reversed_ip}.{dnsbl}", "A", lifetime=2)
            if any(_is_listing(str(a)) for a in answers):
                listed_on.append(name)
        except dns.resolver.NXDOMAIN:
            pass  # not listed — expected
        except Exception:
            pass  # timeout / servfail — skip silently

    r.raw["email"]["blacklist"] = {"ip": mx_ip, "listed_on": listed_on}

    if listed_on:
        names = ", ".join(listed_on)
        r.issues.append(Issue("email", "critical",
            f"Your mail server IP is blacklisted ({names})",
            f"The IP {mx_ip} used by your mail server is on {len(listed_on)} spam "
            f"blacklist(s): {names}. Email providers silently drop or spam-folder "
            "every email you send — signups, password resets, invoices, all of it.",
            f"1. Confirm at mxtoolbox.com/blacklists.aspx → enter {mx_ip}\n"
            "2. Follow the delisting process on each blacklist's site\n"
            "3. If you're on shared hosting, consider switching to Resend or Postmark "
            "— they maintain clean IP pools and handle deliverability for you."))
    else:
        r.passed.append(f"Mail server IP not on major blacklists ({mx_ip})")


# ── CATEGORY 2: SSL / HTTPS ─────────────────────────────────────────────────

def _ssl_connect(domain: str, timeout: int = 5):
    """Try to connect via SSL. Returns cert dict or raises."""
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
        s.settimeout(timeout)
        s.connect((domain, 443))
        return s.getpeercert()


def _check_ssl(r: ScanResult):
    """SSL certificate validity and expiry. Retries once on timeout."""
    cert = None
    for attempt in range(2):
        try:
            cert = _ssl_connect(r.domain, timeout=5 + attempt * 3)
            break
        except ssl.SSLCertVerificationError:
            raise  # don't retry cert errors — they're real
        except Exception:
            if attempt == 0:
                continue  # retry once
            raise

    try:
        if cert is None:
            raise ConnectionError("Could not connect after 2 attempts")

        expiry = datetime.strptime(
            cert["notAfter"], "%b %d %H:%M:%S %Y %Z"
        ).replace(tzinfo=timezone.utc)
        days_left = (expiry - datetime.now(timezone.utc)).days
        issuer = dict(x[0] for x in cert["issuer"]).get(
            "organizationName", "Unknown"
        )

        r.raw["ssl"] = {
            "issuer": issuer,
            "expires": cert["notAfter"],
            "days_left": days_left,
        }

        if days_left < 7:
            r.issues.append(Issue("ssl", "critical",
                f"Your SSL certificate expires in {days_left} days",
                f"Your certificate from {issuer} expires on {cert['notAfter']}. "
                "Once expired, browsers will show a full-page 'Not Secure' warning "
                "and most visitors won't be able to reach your site at all.",
                "Check your hosting dashboard for auto-renewal settings. "
                "Vercel, Netlify, and Cloudflare auto-renew. Railway and "
                "custom servers may need manual renewal."))
        elif days_left < 30:
            r.issues.append(Issue("ssl", "high",
                f"Your SSL certificate expires in {days_left} days",
                f"Your certificate expires on {cert['notAfter']}. "
                "Make sure auto-renewal is configured.",
                "Enable auto-renewal in your hosting dashboard or set "
                "a calendar reminder to renew manually."))
        else:
            r.passed.append(f"SSL certificate valid ({days_left} days left)")

    except ssl.SSLCertVerificationError as e:
        r.issues.append(Issue("ssl", "critical",
            "Your SSL certificate is invalid",
            f"Browsers are blocking your site with a security warning. "
            f"Certificate error: {e}",
            "Check your hosting dashboard. You may need to re-issue "
            "the certificate or verify your domain ownership."))
        r.raw["ssl"] = {"error": str(e)}
    except Exception as e:
        r.issues.append(Issue("ssl", "critical",
            "Your site doesn't have HTTPS",
            f"Could not establish a secure connection to {r.domain}. "
            "Browsers will show 'Not Secure' and may block the site entirely.",
            "Enable HTTPS in your hosting dashboard. Vercel, Netlify, "
            "and Cloudflare provide free SSL automatically."))
        r.raw["ssl"] = {"error": str(e)}


def _check_https_redirect(r: ScanResult):
    """Does HTTP redirect to HTTPS?"""
    try:
        # Don't follow redirects — we want to see the redirect itself
        import http.client
        conn = http.client.HTTPConnection(r.domain, timeout=5)
        conn.request("GET", "/", headers={
            "User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)",
            "Host": r.domain,
        })
        resp = conn.getresponse()
        location = resp.getheader("Location", "")
        conn.close()

        r.raw["ssl"]["http_redirect"] = {
            "status": resp.status,
            "location": location,
        }

        if resp.status in (301, 302, 307, 308) and "https://" in location.lower():
            r.passed.append("HTTP redirects to HTTPS")
        else:
            r.issues.append(Issue("ssl", "high",
                "Visitors typing your URL get an insecure version",
                f"http://{r.domain} doesn't redirect to https://. Visitors who "
                "don't explicitly type https:// will see the insecure version "
                "with a 'Not Secure' warning in Chrome.",
                "Enable 'Force HTTPS' in your hosting dashboard. "
                "Vercel does this by default. Cloudflare: SSL/TLS → "
                "Always Use HTTPS. Railway: add a redirect in your app."))
    except Exception:
        # Can't connect on HTTP at all — might mean HTTP is blocked (fine)
        pass


# ── CATEGORY 3: Exposed Secrets ──────────────────────────────────────────────

def _check_secrets(r: ScanResult, html: str):
    """.env exposed, .git exposed, secret keys in HTML."""

    # ── .env file ──
    env_exposed = _check_path_exposed(r.url, "/.env")
    r.raw["secrets"]["env_exposed"] = env_exposed
    if env_exposed:
        r.issues.append(Issue("secrets", "critical",
            "Your .env file is publicly accessible",
            "Anyone can read your environment variables by visiting "
            f"{r.url}/.env — this typically contains database passwords, "
            "API keys, and other secrets. Bots actively scan for this.",
            "Your deployment is serving your project root directory. "
            "Fix your build output setting in your hosting config so only "
            "the build output (e.g., .next/, dist/, build/) is served."))
    else:
        r.passed.append(".env file not exposed")

    # ── .git directory ──
    git_exposed = _check_path_exposed(r.url, "/.git/config")
    r.raw["secrets"]["git_exposed"] = git_exposed
    if git_exposed:
        r.issues.append(Issue("secrets", "critical",
            "Your source code and git history are downloadable",
            f"Anyone can access {r.url}/.git/config — this means your "
            "entire source code and commit history (including any secrets "
            "you ever committed, even if later deleted) is public.",
            "Block access to .git/ in your web server config, or fix "
            "your deployment to not serve the project root directory."))
    else:
        r.passed.append(".git directory not exposed")

    # ── Secret keys in HTML ──
    if html:
        found_secrets = find_secrets(html)
        r.raw["secrets"]["found_in_html"] = found_secrets
        if found_secrets:
            labels = ", ".join(found_secrets)
            r.issues.append(Issue("secrets", "critical",
                "Secret keys found in your page source",
                f"We found what looks like: {labels}. "
                "Anyone can view your page source and extract these. "
                "Bots actively scrape for secret keys in HTML.",
                "Move these to server-side environment variables. "
                "In Next.js, only NEXT_PUBLIC_ vars are sent to the browser. "
                "In Vite, only VITE_ vars. Everything else stays server-side."))
        else:
            r.passed.append("No secret keys found in page source")


def _check_path_exposed(base_url: str, path: str) -> bool:
    """GET request to check if a sensitive path returns real secret content.
    SPAs return 200 for all routes — we verify the body actually looks like
    the sensitive file, not an HTML page."""
    try:
        req = urllib.request.Request(
            base_url + path,
            headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
        )
        resp = _urlopen(req, timeout=5)
        if resp.status != 200:
            return False
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" in content_type:
            return False
        body = resp.read(1024).decode("utf-8", errors="ignore")
        # Reject HTML responses (SPA catch-all routes)
        if any(m in body[:200].lower() for m in ("<!doctype", "<html", "<head")):
            return False
        if path.endswith(".env"):
            # Real .env files have KEY=VALUE lines
            return bool(re.search(r"[A-Z_]{2,}=", body))
        if ".git" in path:
            # Real git configs have [core] or [remote sections
            return "[core]" in body or "[remote" in body or "repositoryformatversion" in body
        return True
    except Exception:
        return False


def _fetch_text(url: str, max_bytes: int) -> tuple[int, str]:
    """GET a URL and return (status, body text truncated to max_bytes)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"})
    try:
        resp = _urlopen(req, timeout=8)
    except urllib.error.HTTPError as e:
        return e.code, ""
    return resp.status, resp.read(max_bytes).decode("utf-8", errors="ignore")


def _check_bundles(r: ScanResult, html: str):
    """Secret keys in the site's own JS bundles, and public source maps."""
    if not html:
        return
    report = scan_bundles(html, r.url, r.domain, _fetch_text)
    r.raw["secrets"]["bundles"] = report
    if not report["bundles"]:
        return  # no external scripts of our own to inspect

    if report["secrets"]:
        lines = []
        for label, urls in report["secrets"].items():
            names = ", ".join(u.rsplit("/", 1)[-1] or u for u in urls[:3])
            lines.append(f"{label} (in {names})")
        r.issues.append(Issue("secrets", "critical",
            "Secret keys found in your JavaScript bundles",
            "Your site ships these to every visitor's browser: " + "; ".join(lines) + ". "
            "Anyone can open DevTools and copy them. Treat them as leaked.",
            "1. Rotate every key listed above now (revoke the old one at the provider).\n"
            "2. Move the call that needs it to a server route or edge function.\n"
            "3. Only expose publishable keys: NEXT_PUBLIC_ / VITE_ variables are sent "
            "to the browser, so never put a secret in one. A Supabase service_role key "
            "bypasses Row Level Security and must never reach the frontend."))
    else:
        r.passed.append(f"No secret keys in your JS bundles ({len(report['bundles'])} scanned)")

    if report["source_maps"]:
        maps = "\n".join(report["source_maps"][:5])
        r.issues.append(Issue("secrets", "medium",
            "Your original source code is downloadable via source maps",
            f"{len(report['source_maps'])} source map(s) are public. They rebuild your "
            "original, unminified source (comments, file names, internal routes) for "
            "anyone who asks.",
            "Stop publishing .map files in production:\n"
            "Vite: build.sourcemap = false (or 'hidden' and don't deploy the .map files)\n"
            "Next.js: productionBrowserSourceMaps: false (the default)\n"
            "Exposed:\n" + maps))
    else:
        r.passed.append("No public source maps")


# ── CATEGORY 4: DNS ──────────────────────────────────────────────────────────

def _check_dns(r: ScanResult):
    """www resolves, www ↔ apex redirect."""

    # ── www subdomain ──
    www_resolves = False
    try:
        dns_query(f"www.{r.domain}", "A")
        www_resolves = True
    except Exception:
        try:
            dns_query(f"www.{r.domain}", "CNAME")
            www_resolves = True
        except Exception:
            pass

    r.raw["dns"]["www_resolves"] = www_resolves

    if not www_resolves:
        r.issues.append(Issue("dns", "medium",
            f"www.{r.domain} doesn't work",
            f"If someone types www.{r.domain} in their browser, they'll get "
            "an error page. Many people still type www out of habit.",
            f"Add a CNAME record in your DNS settings:\n"
            f"Name: www → Value: {r.domain}"))
    else:
        r.passed.append("www subdomain resolves")

        # ── www ↔ apex redirect ──
        _check_www_redirect(r)


def _check_www_redirect(r: ScanResult):
    """Check if www and apex redirect to each other (not both serving 200)."""
    import http.client

    apex_status = None
    www_status = None

    try:
        conn = http.client.HTTPSConnection(r.domain, timeout=5)
        conn.request("GET", "/", headers={
            "User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)",
            "Host": r.domain,
        })
        resp = conn.getresponse()
        apex_status = resp.status
        conn.close()
    except Exception:
        return  # can't check, skip

    try:
        conn = http.client.HTTPSConnection(f"www.{r.domain}", timeout=5)
        conn.request("GET", "/", headers={
            "User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)",
            "Host": f"www.{r.domain}",
        })
        resp = conn.getresponse()
        www_status = resp.status
        conn.close()
    except Exception:
        return

    r.raw["dns"]["apex_status"] = apex_status
    r.raw["dns"]["www_status"] = www_status

    # If both return 200, check if canonical tag handles deduplication
    if apex_status == 200 and www_status == 200:
        # If the page has a canonical URL pointing to one version, Google
        # respects it — no duplicate content issue despite both serving 200
        has_canonical = False
        try:
            req = urllib.request.Request(
                f"https://www.{r.domain}/",
                headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
            )
            resp = _urlopen(req, timeout=5)
            body = resp.read(4096).decode("utf-8", errors="ignore")
            if re.search(r'rel=["\']canonical["\']', body, re.IGNORECASE):
                has_canonical = True
        except Exception:
            pass

        if has_canonical:
            r.passed.append("www and apex both serve (canonical URL set)")
        else:
            r.issues.append(Issue("dns", "medium",
                "Google might index duplicate versions of your site",
                f"Both www.{r.domain} and {r.domain} serve content with no "
                "canonical tag or redirect. Google may treat these as two "
                "separate sites, splitting your search rankings.",
                "Set up a 301 redirect from www to your apex domain "
                "(or vice versa) in your hosting dashboard. Or add a "
                '<link rel="canonical"> tag pointing to your preferred version.'))
    elif www_status >= 400 and apex_status < 400:
        r.issues.append(Issue("dns", "medium",
            f"www.{r.domain} shows an error page (HTTP {www_status})",
            f"www.{r.domain} resolves but returns HTTP {www_status} instead of your "
            "site. People who type www out of habit land on an error.",
            f"Add www.{r.domain} as a domain in your hosting dashboard, or add a "
            f"redirect rule sending www.{r.domain}/* to https://{r.domain}/$1 (301)."))
    else:
        r.passed.append("www and apex properly redirect")


# ── CATEGORY 5: Security Headers ────────────────────────────────────────────

def _check_security_headers(r: ScanResult, headers: dict):
    """HSTS header."""
    if not headers:
        return

    # ── HSTS ──
    if "strict-transport-security" in headers:
        r.passed.append("HSTS header set")
    else:
        r.issues.append(Issue("security", "medium",
            "Your site allows insecure connections on first visit",
            "Without the HSTS header, even though you have HTTPS, the very "
            "first time someone visits, their browser might use HTTP. "
            "An attacker on public WiFi could intercept that first request.",
            "Add this header to your server responses:\n"
            "Strict-Transport-Security: max-age=31536000; includeSubDomains"))


# ── CATEGORY 6: SEO & Shareability ──────────────────────────────────────────

def _check_seo(r: ScanResult, html: str, fetch_ok: bool):
    """title, meta desc, OG, Twitter Card, viewport,
    canonical, sitemap, favicon."""
    if not fetch_ok and r.raw["performance"].get("blocked"):
        return  # explained in r.notes; not the site's fault
    if not fetch_ok:
        r.issues.append(Issue("seo", "high",
            "Could not load your site to check SEO",
            f"We couldn't fetch {r.url} to check your meta tags, "
            "which means search engines probably can't either.",
            "Make sure your site loads at the root URL without errors."))
        return

    r.raw["seo"]["html_length"] = len(html)

    # ── Title tag ──
    title_match = re.search(r"<title[^>]*>(.+?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        r.raw["seo"]["title"] = title_match.group(1).strip()
        r.passed.append("Page title set")
    else:
        r.issues.append(Issue("seo", "high",
            "Your browser tab is blank and Google can't rank you",
            "Your page has no <title> tag. This is what shows in browser tabs "
            "and as your headline in Google search results. Without it, "
            "Google can't properly index your site.",
            "<title>Your App Name — what it does in 5 words</title>\n"
            "Add this inside your <head> tag."))

    # ── Meta description ──
    if re.search(r'<meta\s+name=["\']description["\']', html, re.IGNORECASE):
        desc_match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\'](.+?)["\']',
            html, re.IGNORECASE,
        )
        if desc_match:
            r.raw["seo"]["description"] = desc_match.group(1).strip()
        r.passed.append("Meta description set")
    else:
        r.issues.append(Issue("seo", "high",
            "Google shows random text from your page instead of your pitch",
            "No meta description found. This is the snippet shown under your "
            "title in Google search results. Without it, Google picks random "
            "text from your page — usually something unhelpful.",
            '<meta name="description" content="What your app does in one sentence">\n'
            "Add this inside your <head> tag."))

    # ── Open Graph tags ──
    has_og_title = bool(re.search(r'og:title', html, re.IGNORECASE))
    has_og_desc = bool(re.search(r'og:description', html, re.IGNORECASE))
    has_og_image = bool(re.search(r'og:image', html, re.IGNORECASE))

    if has_og_title and has_og_desc and has_og_image:
        r.passed.append("Open Graph tags set")
    elif has_og_title or has_og_desc:
        if not has_og_image:
            r.issues.append(Issue("seo", "medium",
                "Link previews have no image",
                "You have og:title and og:description but no og:image. "
                "When someone shares your link on Slack, Discord, or LinkedIn, "
                "it'll show text but no image preview.",
                '<meta property="og:image" content="https://yourdomain.com/og.png">\n'
                "Use a 1200×630 image for best results."))
    else:
        r.issues.append(Issue("seo", "medium",
            "Your links look plain when shared",
            "No Open Graph tags found. When someone shares your link on "
            "Slack, Discord, LinkedIn, or iMessage, it shows as a plain URL "
            "with no title, description, or image preview.",
            '<meta property="og:title" content="Your App Name">\n'
            '<meta property="og:description" content="What it does">\n'
            '<meta property="og:image" content="https://yourdomain.com/og.png">'))

    # ── Twitter Card tags ──
    if re.search(r'twitter:card', html, re.IGNORECASE):
        r.passed.append("Twitter Card tags set")
    else:
        r.issues.append(Issue("seo", "medium",
            "Your links on X/Twitter show no image preview",
            "X/Twitter uses its own meta tags, separate from Open Graph. "
            "Even if you have OG tags, X won't show a rich preview without "
            "Twitter Card tags.",
            '<meta name="twitter:card" content="summary_large_image">\n'
            '<meta name="twitter:title" content="Your App Name">\n'
            '<meta name="twitter:image" content="https://yourdomain.com/og.png">'))

    # ── Viewport meta tag ──
    if re.search(r'viewport', html, re.IGNORECASE):
        r.passed.append("Viewport meta tag set (mobile-friendly)")
    else:
        r.issues.append(Issue("seo", "high",
            "Your site is broken on mobile phones",
            "No viewport meta tag found. Your site renders at desktop width "
            "on phones — everything is tiny and users have to pinch-zoom "
            "to read anything.",
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            "Add this inside your <head> tag."))

    # ── Canonical URL ──
    if re.search(r'rel=["\']canonical["\']', html, re.IGNORECASE):
        r.passed.append("Canonical URL set")
    else:
        r.issues.append(Issue("seo", "medium",
            "Google might index duplicate versions of your pages",
            "No canonical URL tag found. Google may index yourdomain.com/page, "
            "yourdomain.com/page/, and www.yourdomain.com/page as three "
            "separate pages, splitting your rankings.",
            f'<link rel="canonical" href="https://{r.domain}/">\n'
            "Add this inside your <head> tag on every page."))

    # ── Sitemap ──
    # Check /sitemap.xml first, then fall back to robots.txt Sitemap directive.
    has_sitemap = False
    try:
        req = urllib.request.Request(
            f"{r.url}/sitemap.xml",
            headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
        )
        resp = _urlopen(req, timeout=5)
        if resp.status == 200 and len(resp.read()) > 50:
            has_sitemap = True
    except Exception:
        pass

    if not has_sitemap:
        # Check robots.txt for a Sitemap: directive (e.g. Stripe, large sites)
        try:
            req = urllib.request.Request(
                f"{r.url}/robots.txt",
                headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
            )
            resp = _urlopen(req, timeout=5)
            robots = resp.read().decode("utf-8", errors="ignore")
            if re.search(r"(?i)^Sitemap:\s*https?://", robots, re.MULTILINE):
                has_sitemap = True
        except Exception:
            pass

    r.raw["seo"]["has_sitemap"] = has_sitemap
    if has_sitemap:
        r.passed.append("sitemap.xml exists")
    else:
        r.issues.append(Issue("seo", "medium",
            "Google Search Console can't track your indexed pages",
            "No sitemap.xml found at /sitemap.xml. Google Search Console "
            "asks you to submit a sitemap — without one, you can't see "
            "which pages are indexed and which aren't.",
            "Most frameworks have a sitemap plugin:\n"
            "Next.js: next-sitemap\n"
            "Astro: @astrojs/sitemap\n"
            "Django: django.contrib.sitemaps"))

    # ── Favicon ──
    has_favicon = bool(re.search(
        r'(?:rel=["\'](?:icon|shortcut icon)["\']|favicon)',
        html, re.IGNORECASE,
    ))
    if has_favicon:
        r.passed.append("Favicon set")
    else:
        r.issues.append(Issue("seo", "low",
            "Your browser tab has a blank icon",
            "No favicon found. Browsers request /favicon.ico on every page load. "
            "Missing = blank icon in the tab + 404 errors cluttering your "
            "server logs.",
            "Add a 32×32 PNG as /favicon.ico and link it:\n"
            '<link rel="icon" href="/favicon.ico">'))


# ── CATEGORY 7: Performance ─────────────────────────────────────────────────

def _check_performance(r: ScanResult, html: str, headers: dict):
    """Response time, compression."""

    warmup = r.raw["performance"].get("warmup_time", 0)
    response = r.raw["performance"].get("response_time", 0)

    # ── Response time ──
    if warmup and response:
        if warmup > 10 and response < 3:
            # Cold start detected
            r.issues.append(Issue("performance", "high",
                f"First visit takes {warmup:.1f}s (cold start detected)",
                f"Your site took {warmup:.1f}s on first load but only "
                f"{response:.1f}s after warmup. Your hosting is sleeping when "
                "idle and waking up on the first request. Most visitors won't "
                "wait that long.",
                "If you're on a free tier (Railway, Render, Fly), your app "
                "sleeps after inactivity. Upgrade to a paid plan or set up "
                "a health check ping every 5 minutes to keep it warm."))
        elif response > 3:
            r.issues.append(Issue("performance", "high",
                f"Your site takes {response:.1f}s to respond",
                f"Response time of {response:.1f}s means most visitors will "
                "leave before the page loads. Anything over 3 seconds "
                "significantly increases bounce rate.",
                "Check: (1) server region — deploy close to your users, "
                "(2) database queries — add indexes for slow queries, "
                "(3) heavy computations — move to background jobs."))
        else:
            r.passed.append(f"Response time: {response:.1f}s")
    elif r.raw["performance"].get("error"):
        pass  # Already flagged as SEO issue (can't fetch)

    # ── Compression ──
    encoding = r.raw["performance"].get("encoding", "")
    if encoding:
        r.passed.append(f"Compression enabled ({encoding})")
    elif headers:  # Only flag if we actually got a response
        r.issues.append(Issue("performance", "medium",
            "Your pages are 3-4x bigger than they need to be",
            "Your server isn't compressing responses. Enabling gzip or brotli "
            "typically reduces page size by 60-80%, making your site load "
            "significantly faster, especially on mobile.",
            "Vercel and Cloudflare do this automatically. For custom servers:\n"
            "Nginx: add 'gzip on;' to config\n"
            "Express: use the 'compression' middleware"))


# ── CATEGORY 8: Broken Resources ────────────────────────────────────────────

def _check_mixed_content(r: ScanResult, html: str):
    """Mixed content (HTTP resources on HTTPS page)."""
    if not html:
        return

    # Find http:// in src, href (for resources, not links), action attributes
    # Exclude localhost, 127.0.0.1, and regular <a> links
    mixed = set()
    for match in re.finditer(
        r'(?:src|action)\s*=\s*["\']?(http://(?!localhost|127\.0\.0\.1)[^\s"\'<>]+)',
        html, re.IGNORECASE,
    ):
        mixed.add(match.group(1))

    # Also check link[rel=stylesheet] with http://
    for match in re.finditer(
        r'<link[^>]+href\s*=\s*["\']?(http://(?!localhost|127\.0\.0\.1)[^\s"\'<>]+)[^>]*(?:rel=["\']?stylesheet|type=["\']?text/css)',
        html, re.IGNORECASE,
    ):
        mixed.add(match.group(1))

    r.raw["breakage"]["mixed_content"] = list(mixed)

    if mixed:
        urls = "\n".join(list(mixed)[:5])  # Show max 5
        r.issues.append(Issue("breakage", "high",
            "Parts of your site are silently broken",
            f"Your HTTPS page loads {len(mixed)} resource(s) over insecure HTTP. "
            "Browsers silently block these — images don't show, scripts don't run, "
            "and you won't see any error unless you check the browser console.",
            f"Change these http:// URLs to https://:\n{urls}"))
    else:
        r.passed.append("No mixed content issues")


# ── CATEGORY 9: Polish ──────────────────────────────────────────────────────

def _check_404(r: ScanResult):
    """Custom 404 page."""
    import random
    import string
    random_path = "/" + "".join(random.choices(string.ascii_lowercase, k=12))

    try:
        req = urllib.request.Request(
            r.url + random_path,
            headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
        )
        _urlopen(req, timeout=5)
        # 200 for a random path = SPA with client-side routing.
        # These apps handle 404s in JS — skip the check, it's not applicable.
        r.passed.append("Custom 404 page exists")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Read the error page content
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                body = ""

            if len(body) > 500 and "<a" in body.lower():
                r.passed.append("Custom 404 page exists")
            else:
                r.issues.append(Issue("polish", "low",
                    "Broken links show a bare error page",
                    "When someone hits a broken link on your site, they see a "
                    "default error page like 'Cannot GET /path' or a blank page. "
                    "A custom 404 with a link home keeps visitors on your site.",
                    "Create a 404 page in your framework:\n"
                    "Next.js: pages/404.js\n"
                    "Astro: src/pages/404.astro\n"
                    "Static: 404.html in your public directory"))
        else:
            pass  # Other error, skip
    except Exception:
        pass  # Can't check, skip


# ── Score calculation ────────────────────────────────────────────────────────

def _calculate_score(r: ScanResult):
    """Score starts at 100, deducts per issue severity."""
    score = 100
    weights = {"critical": 20, "high": 12, "medium": 5, "low": 2}

    for issue in r.issues:
        score -= weights.get(issue.severity, 5)

    r.score = max(0, min(100, score))

    if r.score >= 80:
        r.grade = "A"
    elif r.score >= 60:
        r.grade = "B"
    elif r.score >= 40:
        r.grade = "C"
    elif r.score >= 20:
        r.grade = "D"
    else:
        r.grade = "F"
