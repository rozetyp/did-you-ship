"""
didyouship.com — production readiness scanner.

24 checks across 9 categories. Every check answers:
"What breaks if I don't fix this?"

All from public data. Zero server access needed.
"""

import ssl
import socket
import time
import re
import gzip
import zlib
import urllib.request
import urllib.error
import dns.resolver
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone
from dataclasses import dataclass, field


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
    email_vendors: list[str] = field(default_factory=list)
    mx_vendors: list[str] = field(default_factory=list)


DNS_TIMEOUT = 3
HTTP_TIMEOUT = 10

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
    ("dnsbl.sorbs.net",         "SORBS"),
]

# ── Secret patterns (ONLY provably secret — zero false positives) ────────────

SECRET_PATTERNS = [
    (r"sk_live_[a-zA-Z0-9]{20,}", "Stripe secret key"),
    (r"sk_test_[a-zA-Z0-9]{20,}", "Stripe test secret key"),
    (r"AKIA[A-Z0-9]{16}", "AWS access key"),
    (r"sk-ant-[a-zA-Z0-9\-]{20,}", "Anthropic API key"),
    (r"xai-[a-zA-Z0-9]{20,}", "xAI API key"),
    (r"ghp_[a-zA-Z0-9]{36,}", "GitHub personal access token"),
    (r"gho_[a-zA-Z0-9]{36,}", "GitHub OAuth token"),
    (r"glpat-[a-zA-Z0-9\-]{20,}", "GitLab personal access token"),
    (r"sk-[a-zA-Z0-9]{40,}", "OpenAI API key"),
    (r"-----BEGIN[A-Z ]*PRIVATE KEY", "Private key"),
    (r"postgres(?:ql)?://[^\s\"'<>]+", "Database connection string"),
    (r"mongodb(?:\+srv)?://[^\s\"'<>]+", "Database connection string"),
    (r"mysql://[^\s\"'<>]+", "Database connection string"),
    (r"redis://[^\s\"'<>]+", "Redis connection string"),
]


# ── Main entry ───────────────────────────────────────────────────────────────

def scan(domain: str) -> ScanResult:
    """Run all 24 checks against a domain."""
    domain = (domain.strip().lower()
              .replace("https://", "").replace("http://", "")
              .replace("www.", "").rstrip("/").split("/")[0])
    if "@" in domain:
        domain = domain.split("@")[-1]

    r = ScanResult(domain=domain, url=f"https://{domain}")
    r.raw = {
        "email": {}, "ssl": {}, "headers": {}, "dns": {},
        "seo": {}, "performance": {}, "secrets": {},
    }

    with ThreadPoolExecutor(max_workers=8) as pool:
        # Start slow I/O checks immediately — no page HTML needed
        # ssl + redirect are grouped to avoid a write race on r.raw["ssl"]
        futures = [
            pool.submit(_check_email, r),                    # checks 1-4  (DNS)
            pool.submit(_check_dkim, r),                     # check 5     (DNS)
            pool.submit(_check_blacklist, r),                # check 6     (DNS)
            pool.submit(_check_ssl_and_redirect, r),         # checks 7-8  (SSL + HTTP)
            pool.submit(_check_dns, r),                      # checks 9-10 (DNS)
            pool.submit(_check_404, r),                      # check 24    (HTTP)
        ]

        # Fetch page in main thread — provides html/headers for remaining checks
        html, headers, fetch_ok = _fetch_page(r)

        # Submit html-dependent checks now that fetch is done
        futures += [
            pool.submit(_check_secrets, r, html),            # checks 7-9
            pool.submit(_check_security_headers, r, headers),# check 12
            pool.submit(_check_seo, r, html, fetch_ok),      # checks 13-20
            pool.submit(_check_performance, r, html, headers),# checks 21-22
            pool.submit(_check_mixed_content, r, html),      # check 23
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
            resp = urllib.request.urlopen(req, timeout=HTTP_TIMEOUT + attempt * 5)
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
            urllib.request.urlopen(req2, timeout=HTTP_TIMEOUT)
            response_time = time.time() - t1
            r.raw["performance"]["response_time"] = round(response_time, 2)

            return html, headers, True

        except Exception as e:
            if attempt == 0:
                continue  # retry once
            r.raw["performance"]["error"] = str(e)
            return "", {}, False


# ── CATEGORY 1: Email ────────────────────────────────────────────────────────

def _check_email(r: ScanResult):
    """Checks 1-4: SPF, DMARC, DMARC reporting, MX records."""

    # ── Check 1: SPF record ──
    spf_record = None
    vendors = []
    try:
        for rdata in dns.resolver.resolve(r.domain, "TXT", lifetime=DNS_TIMEOUT):
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
            f"Add a TXT record to your DNS:\nv=spf1 include:_spf.google.com ~all\n"
            f"(Replace the include with your email provider.)"))
    elif "+all" in spf_record or "?all" in spf_record:
        mech = spf_record.split()[-1]
        r.issues.append(Issue("email", "critical",
            "Your SPF says anyone can send email as you",
            f"Your SPF record ends with {mech}, which means ANY server in the world "
            f"can send email as @{r.domain}.",
            f"Change {mech} to ~all or -all in your SPF TXT record."))
    elif "~all" in spf_record:
        r.issues.append(Issue("email", "low",
            "Email authentication isn't fully locked down",
            "Your SPF uses ~all (softfail). Unauthorized senders are flagged but not "
            "rejected. This is fine for now — upgrade to -all once you're confident "
            "your SPF includes are complete.",
            "Change ~all to -all in your SPF TXT record when ready."))
        r.passed.append("SPF record exists")
    else:
        r.passed.append("SPF record configured correctly")

    # ── Check 2: DMARC record ──
    dmarc_record = None
    dmarc_policy = None
    dmarc_rua = None
    try:
        for rdata in dns.resolver.resolve(f"_dmarc.{r.domain}", "TXT", lifetime=DNS_TIMEOUT):
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

    # ── Check 3: DMARC reporting ──
    if dmarc_record and not dmarc_rua:
        r.issues.append(Issue("email", "medium",
            "You won't know when someone spoofs your email",
            "Your DMARC record doesn't include a reporting address (rua=). "
            "You'll never find out if someone is sending phishing emails "
            "pretending to be you.",
            f"Add rua=mailto:dmarc@{r.domain} to your DMARC TXT record."))
    elif dmarc_record and dmarc_rua:
        r.passed.append("DMARC reporting configured")

    # ── Check 4: MX records (informational) ──
    mx_hosts = []
    mx_vendors_found = []
    try:
        for rdata in dns.resolver.resolve(r.domain, "MX", lifetime=DNS_TIMEOUT):
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
            records = dns.resolver.resolve(
                f"{selector}._domainkey.{r.domain}", "TXT", lifetime=1
            )
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


def _check_blacklist(r: ScanResult):
    """Check if the domain's mail server IP appears on major spam blacklists."""
    # Resolve the lowest-priority MX host to an IP
    mx_ip = None
    try:
        mx_records = list(dns.resolver.resolve(r.domain, "MX", lifetime=DNS_TIMEOUT))
        mx_host = str(min(mx_records, key=lambda x: x.preference).exchange).rstrip(".")
        a_records = dns.resolver.resolve(mx_host, "A", lifetime=DNS_TIMEOUT)
        mx_ip = str(list(a_records)[0])
    except Exception:
        pass

    if not mx_ip:
        r.raw["email"]["blacklist"] = {"skipped": "no MX record resolved"}
        return

    listed_on = []
    reversed_ip = ".".join(reversed(mx_ip.split(".")))
    for dnsbl, name in DNSBL_SERVERS:
        try:
            dns.resolver.resolve(f"{reversed_ip}.{dnsbl}", "A", lifetime=2)
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
    """Check 5: SSL certificate validity and expiry. Retries once on timeout."""
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
    """Check 6: Does HTTP redirect to HTTPS?"""
    try:
        req = urllib.request.Request(
            f"http://{r.domain}",
            headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
        )
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
    """Checks 7-9: .env exposed, .git exposed, secret keys in HTML."""

    # ── Check 7: .env file ──
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

    # ── Check 8: .git directory ──
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

    # ── Check 9: Secret keys in HTML ──
    if html:
        found_secrets = []
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, html):
                found_secrets.append(label)

        r.raw["secrets"]["found_in_html"] = found_secrets
        if found_secrets:
            unique = list(dict.fromkeys(found_secrets))  # dedupe preserving order
            labels = ", ".join(unique)
            r.issues.append(Issue("secrets", "critical",
                f"Secret keys found in your page source",
                f"We found what looks like: {labels}. "
                "Anyone can view your page source and extract these. "
                "Bots actively scrape for secret keys in HTML.",
                "Move these to server-side environment variables. "
                "In Next.js, only NEXT_PUBLIC_ vars are sent to the browser. "
                "In Vite, only VITE_ vars. Everything else stays server-side."))
        else:
            r.passed.append("No secret keys found in page source")


def _check_path_exposed(base_url: str, path: str) -> bool:
    """HEAD request to check if a sensitive path returns 200."""
    try:
        req = urllib.request.Request(
            base_url + path,
            method="HEAD",
            headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200
    except Exception:
        return False


# ── CATEGORY 4: DNS ──────────────────────────────────────────────────────────

def _check_dns(r: ScanResult):
    """Checks 10-11: www resolves, www ↔ apex redirect."""

    # ── Check 10: www subdomain ──
    # Use socket.getaddrinfo as it follows CNAME chains and works with
    # Cloudflare-proxied records that flatten to A records.
    www_resolves = False
    try:
        dns.resolver.resolve(f"www.{r.domain}", "A", lifetime=DNS_TIMEOUT)
        www_resolves = True
    except Exception:
        try:
            dns.resolver.resolve(f"www.{r.domain}", "CNAME", lifetime=DNS_TIMEOUT)
            www_resolves = True
        except Exception:
            try:
                results = socket.getaddrinfo(f"www.{r.domain}", 80, proto=socket.IPPROTO_TCP)
                if results:
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

        # ── Check 11: www ↔ apex redirect ──
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

    # If both return 200, neither is redirecting — that's the problem
    if apex_status == 200 and www_status == 200:
        r.issues.append(Issue("dns", "high",
            f"www.{r.domain} and {r.domain} are separate sites",
            f"Both www.{r.domain} and {r.domain} serve content independently. "
            "Google treats these as two different websites, splitting your "
            "search rankings in half.",
            "Set up a 301 redirect from www to your apex domain "
            "(or vice versa) in your hosting dashboard. Pick one "
            "canonical version and redirect the other."))
    else:
        r.passed.append("www and apex properly redirect")


# ── CATEGORY 5: Security Headers ────────────────────────────────────────────

def _check_security_headers(r: ScanResult, headers: dict):
    """Check 12: HSTS header."""
    if not headers:
        return

    # ── Check 12: HSTS ──
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
    """Checks 13-20: title, meta desc, OG, Twitter Card, viewport,
    canonical, sitemap, favicon."""
    if not fetch_ok:
        r.issues.append(Issue("seo", "high",
            "Could not load your site to check SEO",
            f"We couldn't fetch {r.url} to check your meta tags, "
            "which means search engines probably can't either.",
            "Make sure your site loads at the root URL without errors."))
        return

    r.raw["seo"]["html_length"] = len(html)

    # ── Check 13: Title tag ──
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

    # ── Check 14: Meta description ──
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

    # ── Check 15: Open Graph tags ──
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

    # ── Check 16: Twitter Card tags ──
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

    # ── Check 17: Viewport meta tag ──
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

    # ── Check 18: Canonical URL ──
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

    # ── Check 19: Sitemap.xml ──
    try:
        req = urllib.request.Request(
            f"{r.url}/sitemap.xml",
            headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
        )
        resp = urllib.request.urlopen(req, timeout=5)
        content = resp.read()
        if resp.status == 200 and len(content) > 50:
            r.passed.append("sitemap.xml exists")
            r.raw["seo"]["has_sitemap"] = True
        else:
            raise ValueError("empty")
    except Exception:
        r.raw["seo"]["has_sitemap"] = False
        r.issues.append(Issue("seo", "medium",
            "Google Search Console can't track your indexed pages",
            "No sitemap.xml found at /sitemap.xml. Google Search Console "
            "asks you to submit a sitemap — without one, you can't see "
            "which pages are indexed and which aren't.",
            "Most frameworks have a sitemap plugin:\n"
            "Next.js: next-sitemap\n"
            "Astro: @astrojs/sitemap\n"
            "Django: django.contrib.sitemaps"))

    # ── Check 20: Favicon ──
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
    """Checks 21-22: Response time, compression."""

    warmup = r.raw["performance"].get("warmup_time", 0)
    response = r.raw["performance"].get("response_time", 0)

    # ── Check 21: Response time ──
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

    # ── Check 22: Compression ──
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
    """Check 23: Mixed content (HTTP resources on HTTPS page)."""
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

    r.raw["secrets"]["mixed_content"] = list(mixed)

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
    """Check 24: Custom 404 page."""
    import random
    import string
    random_path = "/" + "".join(random.choices(string.ascii_lowercase, k=12))

    try:
        req = urllib.request.Request(
            r.url + random_path,
            headers={"User-Agent": "Mozilla/5.0 (compatible; didyouship/1.0)"},
        )
        resp = urllib.request.urlopen(req, timeout=5)
        # If we get 200 for a random path, that's weird but not a 404 issue
        html = resp.read().decode("utf-8", errors="ignore")
        if len(html) > 500 and "<a" in html.lower():
            r.passed.append("Custom 404 page exists")
        else:
            r.issues.append(Issue("polish", "low",
                "Broken links show a bare error page",
                "When someone hits a broken link on your site, they see a "
                "minimal default error page. A custom 404 page with a "
                "link back home keeps visitors on your site.",
                "Create a 404 page in your framework:\n"
                "Next.js: pages/404.js\n"
                "Astro: src/pages/404.astro\n"
                "Static: 404.html in your public directory"))
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
