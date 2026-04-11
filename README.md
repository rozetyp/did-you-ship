# didyouship.com

**You shipped your app. But did you check?**

Free production readiness scanner that finds everything you forgot before launch — email going to spam, secrets exposed, SSL broken, SEO missing, slow cold starts. 26 checks in under 10 seconds. One domain. Zero signup.

**Live at [didyouship.com](https://didyouship.com)**

---

## The problem

You build an app with Cursor, Replit, v0, or Bolt. You deploy it. It works. You share the link.

Then:
- Your signup emails land in spam (no SPF/DMARC)
- Someone finds your `.env` file on Google (exposed secrets)
- Your link on Slack shows a blank preview (no OG tags)
- Chrome says "Not Secure" on first visit (no HSTS)
- Google indexes `www.` and non-`www.` as two separate sites
- Your site takes 8 seconds to load on first visit (cold start)

These aren't bugs. They're the boring infrastructure stuff that nobody teaches and every vibe coder forgets. didyouship.com checks all of it in one scan.

## Who it's for

Indie hackers, solo founders, and developers who ship fast and want a single check to catch what they missed. If you've ever launched something and then discovered a week later that all your transactional emails were going to spam — this is for you.

---

## All 26 checks in detail

### Category 1: Email Deliverability (6 checks)

Email is the most common thing that breaks silently after launch. Your app sends signup confirmations, password resets, invoices — and they all land in spam because you never set up 3 DNS records.

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 1 | **SPF record** | Query TXT records for `v=spf1`. Verify the mechanism (`-all`, `~all`, `+all`). Flag `+all` and `?all` as critical (anyone can send as you). Accept `~all` as valid. | Gmail marks your emails as unverified. They go to spam or get rejected. |
| 2 | **DMARC record** | Query `_dmarc.{domain}` TXT. Parse policy (`p=none/quarantine/reject`) and reporting address (`rua=`). | Anyone can send phishing emails from your domain. Gmail penalizes your real emails. |
| 3 | **DMARC reporting** | Check if DMARC record includes `rua=` (reporting address). | You'll never know when someone is spoofing your domain. |
| 4 | **MX records** | Query MX records. Identify email provider (Google Workspace, Microsoft 365, Zoho, etc). | Informational — displayed in results. |
| 5 | **DKIM** | Probe 16 common selectors (`default`, `google`, `selector1`, `k1`, `s1`, `resend`, `postmark`, `sendgrid`, `mailgun`, etc.) at `{selector}._domainkey.{domain}`. Skip if SPF is `-all` (non-sending domain). | Gmail can't cryptographically verify your emails are genuine — even with SPF and DMARC, emails may land in spam. |
| 6 | **IP blacklist** | Resolve MX to IP, check against 4 public DNSBLs: Spamhaus, Barracuda, SpamCop, SORBS. | Every email you send gets silently dropped or spam-foldered. Signups, resets, invoices — all of it. |

**Vendor detection**: We identify 20 email providers from SPF includes (SendGrid, Resend, Postmark, Amazon SES, Mailchimp, HubSpot, Braze, Customer.io, etc.) and 8 from MX records (Google Workspace, Microsoft 365, Proofpoint, Mimecast, Zoho, Cloudflare).

### Category 2: SSL & HTTPS (2 checks)

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 7 | **SSL certificate** | TLS handshake on port 443. Check validity, issuer, expiry date. Warn at <30 days, critical at <7 days. Retry once on timeout. | Browsers show a full-page "Not Secure" warning. Most visitors won't proceed. |
| 8 | **HTTP→HTTPS redirect** | Raw HTTP GET to port 80 (without following redirects). Check for 301/302/307/308 with `https://` location. | Visitors who type your URL without `https://` see an insecure version with a Chrome warning. |

### Category 3: Exposed Secrets (3 checks)

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 9 | **`.env` file exposed** | GET `/.env`. Reject HTML responses (catches SPAs that return 200 for everything). Verify body contains `KEY=VALUE` patterns. | Your database passwords, API keys, and secrets are publicly readable. Bots actively scan for this. |
| 10 | **`.git` directory exposed** | GET `/.git/config`. Reject HTML. Verify body contains `[core]` or `[remote`. | Your entire source code and commit history — including any secrets you ever committed — is downloadable. |
| 11 | **Secret keys in HTML** | Regex scan the page source for 14 secret patterns: Stripe keys (`sk_live_`, `sk_test_`), AWS keys (`AKIA`), OpenAI/Anthropic/xAI API keys, GitHub/GitLab tokens, private keys, database connection strings (postgres/mongo/mysql/redis). | Anyone viewing page source can extract your API keys. Bots scrape for these. |

**SPA handling**: Single-page apps return HTTP 200 for all routes (including `/.env`). We detect this by checking Content-Type and body content — only flag as exposed if the response actually looks like a real `.env` or `.git/config` file.

### Category 4: DNS (2 checks)

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 12 | **www subdomain** | DNS A/CNAME lookup for `www.{domain}`. Falls back to `socket.getaddrinfo` for Cloudflare-proxied CNAMEs that flatten to A records. | People who type `www.yourdomain.com` get an error page. |
| 13 | **www↔apex redirect** | HTTPS GET to both `www.` and apex. If both return 200, check if `www.` has a `<link rel="canonical">` — if so, Google handles deduplication correctly. Only flag if both serve 200 with no canonical. | Google treats www and non-www as two separate sites, splitting your search rankings. |

### Category 5: Security Headers (1 check)

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 14 | **HSTS** | Check response headers for `Strict-Transport-Security`. | Even with HTTPS, the first visit might use HTTP. An attacker on public WiFi can intercept that first request. |

### Category 6: SEO & Shareability (8 checks)

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 15 | **Title tag** | Parse `<title>` from HTML. | Browser tab is blank. Google can't rank you — no headline in search results. |
| 16 | **Meta description** | Check for `<meta name="description">`. | Google picks random text from your page as the search snippet. |
| 17 | **Open Graph tags** | Check for `og:title`, `og:description`, `og:image`. | Links shared on Slack, Discord, LinkedIn, iMessage show as plain URLs with no preview. |
| 18 | **Twitter Cards** | Check for `twitter:card` meta tag. | Links on X/Twitter show no image preview (separate from OG tags). |
| 19 | **Viewport** | Check for `<meta name="viewport">`. | Site renders at desktop width on phones — tiny and unusable. |
| 20 | **Canonical URL** | Check for `<link rel="canonical">`. | Google indexes `/page`, `/page/`, and `www.../page` as three separate pages. |
| 21 | **Sitemap** | Check `/sitemap.xml`. Falls back to parsing `robots.txt` for `Sitemap:` directive (catches sites like Stripe with `/sitemap/sitemap.xml`). | Google Search Console can't track which pages are indexed. |
| 22 | **Favicon** | Check for `<link rel="icon">` or favicon reference in HTML. | Blank icon in browser tab. 404 errors in server logs on every page load. |

### Category 7: Performance (2 checks)

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 23 | **Response time** | Two requests: first = warmup, second = real measurement. If warmup >10s but second <3s, we detect a **cold start** (free tier sleeping). Flag if response >3s. | Users leave. Bounce rate spikes. Free tier cold starts can hit 10-15 seconds. |
| 24 | **Compression** | Check `Content-Encoding` header for gzip/deflate/brotli. | Pages are 3-4x bigger than they need to be. Slow on mobile. |

### Category 8: Breakage (1 check)

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 25 | **Mixed content** | Regex scan HTML for `src=` and `action=` attributes loading `http://` resources on an HTTPS page. Also checks `<link>` stylesheets. Excludes localhost. | Images don't show, scripts don't run, styles break — all silently. No visible error unless you check browser console. |

### Category 9: Polish (1 check)

| # | Check | What we do | What breaks |
|---|-------|-----------|-------------|
| 26 | **Custom 404** | GET a random path. If 200 → SPA (client-side routing handles it, pass). If 404 → check body length and links. | Broken links show a bare "Cannot GET /path" error instead of a helpful page. |

---

## Scoring

Score starts at 100. Each issue deducts points:

| Severity | Deduction | Example |
|----------|-----------|---------|
| Critical | -20 | No SPF, .env exposed, SSL expired |
| High | -12 | No meta description, DKIM missing, slow response |
| Medium | -5 | No HSTS, no canonical, no sitemap |
| Low | -2 | No custom 404, no favicon |

**Grades**: A (80+), B (60+), C (40+), D (20+), F (<20)

---

## AI explanations

When `XAI_API_KEY` is set, each scan result includes:

- **One-line summary**: "Your emails are going to spam because you're missing two DNS records."
- **Per-issue explanations**: 2-3 sentence plain-English explanation + the one action to fix it

Powered by xAI Grok (`grok-3-mini-fast`). Both calls run in parallel to minimize latency. Gracefully degrades — scanner works fine without it.

---

## Guide pages (25 guides)

Every issue the scanner can find has a dedicated educational guide at `/guides/{slug}`. Each guide includes:

- What the issue is and why it matters
- Step-by-step fix instructions
- Provider-specific setup (Vercel, Netlify, Cloudflare, Railway, etc.)
- HowTo and BreadcrumbList schema for Google rich results
- Inline scanner CTA — type your domain and scan without leaving the page

### Email Deliverability
| Guide | URL |
|-------|-----|
| SPF Record Missing | `/guides/spf-record` |
| DMARC Record Missing | `/guides/dmarc` |
| Email Spoofing Protection | `/guides/email-spoofing` |
| DKIM Not Configured | `/guides/dkim-setup` |
| Mail Server IP Blacklisted | `/guides/ip-blacklisted` |
| Email Deliverability Overview | `/guides/email-deliverability` |

### SSL & HTTPS
| Guide | URL |
|-------|-----|
| SSL Certificate Expired or Invalid | `/guides/ssl-certificate` |
| HTTP to HTTPS Redirect | `/guides/https-redirect` |

### Exposed Secrets
| Guide | URL |
|-------|-----|
| .env File Exposed | `/guides/env-exposed` |
| .git Directory Exposed | `/guides/git-exposed` |
| API Keys in Page Source | `/guides/leaked-secrets` |

### DNS
| Guide | URL |
|-------|-----|
| www Subdomain Not Working | `/guides/www-redirect` |

### Security Headers
| Guide | URL |
|-------|-----|
| HSTS Header Missing | `/guides/hsts-header` |

### SEO
| Guide | URL |
|-------|-----|
| Page Title Tag Missing | `/guides/page-title` |
| Meta Description Missing | `/guides/meta-description` |
| Open Graph Tags Missing | `/guides/open-graph` |
| Twitter Card Tags Missing | `/guides/twitter-cards` |
| Viewport Meta Tag Missing | `/guides/viewport-meta` |
| Canonical URL Missing | `/guides/canonical-url` |
| Sitemap.xml Missing | `/guides/sitemap` |
| Favicon Missing | `/guides/favicon` |

### Performance
| Guide | URL |
|-------|-----|
| Slow Response Time & Cold Starts | `/guides/response-time` |
| Gzip Compression Not Enabled | `/guides/compression` |

### Breakage & Polish
| Guide | URL |
|-------|-----|
| Mixed Content Errors | `/guides/mixed-content` |
| No Custom 404 Page | `/guides/custom-404` |

---

## Problem pages (9 symptom-driven pages)

Users don't search for "SPF record missing" — they search for "why are my emails going to spam." These pages target symptom-driven queries and link to the relevant guides.

Each page includes multiple causes with severity ratings, FAQ section with schema markup, and an inline scanner.

| Page | URL | Causes | FAQs |
|------|-----|--------|------|
| Why Are Your Emails Going to Spam? | `/why/emails-going-to-spam` | 5 | 6 |
| Why Isn't Your Website Showing in Google? | `/why/not-in-google` | 5 | 5 |
| Why Do Your Links Look Bad When Shared? | `/why/link-preview-not-working` | 3 | 5 |
| Why Does Your Website Say "Not Secure"? | `/why/website-not-secure` | 5 | 4 |
| Why Is Your Website Loading Slowly? | `/why/website-loading-slow` | 3 | 5 |
| Why Is Your Website Broken on Mobile? | `/why/website-broken-on-mobile` | 1 | 5 |
| Why Are Secrets or API Keys Exposed? | `/why/secrets-exposed` | 3 | 4 |
| Why Doesn't www Work? | `/why/www-not-working` | 2 | 4 |
| Why Are There Broken Page Errors? | `/why/broken-page-errors` | 2 | 4 |

---

## Architecture

```
                    ┌──────────────┐
                    │  Cloudflare  │  DNS + CDN + SSL
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │   Railway    │  Auto-deploy from GitHub
                    │   (uvicorn)  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴────┐ ┌────┴─────┐
        │  app.py   │ │scanner │ │ai_report │
        │  FastAPI  │ │  .py   │ │   .py    │
        │  routes   │ │26checks│ │ xAI Grok │
        └───────────┘ └───┬────┘ └──────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
          DNS queries  HTTP reqs   SSL handshake
          (dnspython)  (urllib     (ssl module)
                       via proxy)
```

**Scanner internals**: The `scan()` function runs checks in parallel using a ThreadPool with 8 workers. DNS-only checks (email, DKIM, blacklist, DNS) start immediately. The main thread fetches the page HTML, then submits HTML-dependent checks (SEO, secrets, performance, headers). DKIM waits for the email check to complete first (needs SPF data to handle non-sending domains). Total scan time: 3-8 seconds.

**Proxy**: All outbound HTTP requests are routed through a configurable residential proxy (`SCAN_PROXY` env var) to avoid blocks and rate limits from target sites. DNS queries go direct.

**DNS reliability**: All DNS queries use a retry wrapper — 3 attempts with exponential backoff (0.2s, 0.4s). Only `NXDOMAIN` is treated as permanent. This eliminates false positives from transient resolver failures.

---

## Stack

- **Backend**: Python, FastAPI, uvicorn
- **Scanner**: `dnspython` (DNS), `ssl` (certificates), `urllib` (HTTP), `socket` (fallback resolution)
- **AI**: xAI Grok `grok-3-mini-fast` via OpenAI-compatible API
- **Frontend**: Vanilla HTML/CSS/JS — no framework, no build step, no node_modules
- **Templates**: Jinja2 (guide and problem pages)
- **Rate limiting**: slowapi (10 scans/min per IP)
- **Hosting**: Railway (auto-deploy) + Cloudflare (DNS, CDN, SSL)
- **Schema**: HowTo, FAQPage, BreadcrumbList, Article (for Google rich results)

---

## Run locally

```bash
git clone https://github.com/rozetyp/did-you-ship.git
cd did-you-ship
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional
export XAI_API_KEY="your-xai-key"                          # AI explanations
export SCAN_PROXY="http://user:pass@host:port"              # residential proxy

uvicorn app:app --port 8000
# Open http://localhost:8000
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `XAI_API_KEY` | No | xAI API key — enables AI summaries and per-issue explanations |
| `SCAN_PROXY` | No | HTTP proxy URL for outbound scan requests |
| `PORT` | No | Server port (default: 8000, Railway sets automatically) |

## API

| Endpoint | Description |
|----------|-------------|
| `GET /` | Landing page with scanner |
| `GET /api/scan/{domain}` | Full scan (up to 26 checks), returns JSON with issues, fixes, score, grade, AI explanations |
| `GET /guides/{slug}` | Educational guide page (25 guides) |
| `GET /why/{slug}` | Problem/symptom page (9 pages) |
| `GET /sitemap.xml` | Auto-generated sitemap |
| `GET /health` | Health check |

Rate limit: 10 requests/minute per IP on `/api/scan/`.

## License

MIT
