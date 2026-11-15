# didyouship

[![CI](https://github.com/rozetyp/did-you-ship/actions/workflows/ci.yml/badge.svg)](https://github.com/rozetyp/did-you-ship/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**You shipped your app. But did you check?**

You built something with Cursor, Lovable, Bolt, Replit or v0. It works on your machine, it works on Vercel, you posted the link. Then over the next week:

- Signup and password reset emails land in spam, because the domain has no SPF, DKIM or DMARC.
- Your Supabase `service_role` key is sitting in the JavaScript bundle, and it bypasses every Row Level Security rule you wrote.
- `yourapp.com/.env` downloads your database password.
- The link you shared on Slack or X shows up as a bare URL with no preview.
- `www.yourapp.com` shows your host's error page instead of your app.
- The first visit takes 9 seconds because the free tier went to sleep.

None of that is a bug in your code, and none of it shows up when you test the app yourself. It's the setup around the app: DNS records, headers, what your build ships to the browser. Nobody teaches it, and the coding assistant usually doesn't mention it.

didyouship checks all of it in one scan. Give it a domain and it runs 28 checks in 5-15 seconds, from the outside, the way a visitor (or a bot looking for keys) would see your site. Every finding says what actually breaks and gives you the fix to paste: the DNS record, the header, the config line.

```
$ didyouship example.com
example.com  56/100  grade C

CRITICAL [email] Anyone can send emails pretending to be @example.com
         Your domain has no DMARC record. This means: (1) anyone can spoof your email, ...
         fix: Add a TXT record at _dmarc.example.com:
              v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com

HIGH     [email] Emails have no cryptographic signature (DKIM missing)
         ...
19 passed · 5 issues · 28 checks
```

Install the CLI below and run it before every launch, or self-host the web version. It's free, needs no signup and stores nothing.

## Who it's for

People who ship without an ops person: solo founders, indie hackers, vibe coders, agencies handing a site over to a client, anyone who just pointed a domain at Vercel, Netlify or Railway and moved on. If you know what DMARC is, it saves you ten minutes of checking. If you don't, it tells you why you should care, then exactly what to add.

It's not a pentest. If you have a security team, they have better tools. This covers the boring stuff that's easy to fix and embarrassing to miss.

## Why this one

Most free checkers do one thing: an SEO audit, a DMARC lookup, a header grader. You'd need five tabs to cover what this does in one run. The vibe-coding security scanners go deeper on code, but they skip email and SEO entirely, and the paid ones want a card before your first scan.

- Findings are written as what breaks ("your emails go to spam"), not as spec names.
- It's strict about false alarms. Keys that are meant to be public, placeholder values copied from docs and sites that simply block bots don't count against you. A wrong "critical" is worse than a missed one.
- It only reads what's already public, and it never uses a key it finds.
- It's open source, so you can read exactly what each check does, run it in CI or host your own.

Cleaning up this repo turned up two problems on the project's own hosted site. The scanner flagged its `www.` address returning a 404. And the hosted scanner had been quietly failing every page fetch for weeks, because its proxy login had expired. Both are fixed now.

## Install

```bash
pip install "git+https://github.com/rozetyp/did-you-ship"
didyouship yourdomain.com
```

The scanner itself depends only on `dnspython`. Python 3.10+.

```bash
didyouship yourdomain.com --json                # full result, including raw data per check
didyouship https://www.yourdomain.com/pricing   # URLs and emails are normalized to the domain
didyouship yourdomain.com --fail-on critical    # exit 2 if anything critical is found
```

### In CI

Fail a deploy pipeline when something critical shows up on production:

```yaml
- run: pip install "git+https://github.com/rozetyp/did-you-ship"
- run: didyouship yourdomain.com --fail-on critical
```

Exit codes: `0` ok, `1` invalid domain, `2` an issue at or above `--fail-on`.

### As a library

```python
from didyouship import scan

r = scan("example.com")
print(r.score, r.grade)
for issue in r.issues:
    print(issue.severity, issue.title, issue.fix)
```

## What it checks

| Category | Checks |
|---|---|
| **Email** | SPF (and dangerous `+all`/`?all`), DMARC policy, DMARC reporting (`rua=`), MX and provider detection, DKIM on 16 common selectors, mail server IP on Spamhaus / Barracuda / SpamCop |
| **SSL** | Certificate validity, issuer, expiry (warns under 30 days), HTTP → HTTPS redirect |
| **Secrets** | Public `/.env`, public `/.git/config`, secret keys in the page HTML, secret keys in the site's own JS bundles, public source maps |
| **DNS** | `www.` resolves, `www.` doesn't show an error page, www and apex don't serve duplicate sites |
| **Security** | HSTS header |
| **SEO & sharing** | Title, meta description, Open Graph, Twitter/X card, viewport, canonical URL, `sitemap.xml` (falls back to `robots.txt`), favicon |
| **Performance** | Response time with cold-start detection (two requests), gzip/brotli compression |
| **Breakage** | Mixed content (`http://` scripts, images, styles on an HTTPS page) |
| **Polish** | Custom 404 page |

### Secret detection

The HTML and the site's own JS bundles (same host or subdomains, up to 15, third-party CDNs skipped) are matched against keys that are secret by design:

- **Payments and cloud:** Stripe secret and restricted keys, AWS access keys.
- **AI APIs:** OpenAI, Anthropic, xAI.
- **Code hosting:** GitHub and GitLab tokens.
- **Messaging and email:** SendGrid, Slack tokens.
- **Supabase:** `sb_secret_` keys, and JWTs whose `role` claim is `service_role`.
- **Other:** private keys, and database URLs with real credentials.

Keys that are meant to be public are not flagged:
- Stripe `pk_`
- Firebase `AIza…`
- the Supabase anon key

Placeholder connection strings like `postgres://user:password@localhost` aren't flagged either. Found keys are never printed, only what kind of key and which file.

A source map is reported only when it's public **and** reveals your own code. Maps with no sources, or only `node_modules` and bundler runtime, are ignored.

### Scoring

Starts at 100. Each issue deducts by severity: critical −20, high −12, medium −5, low −2. Grades: A ≥ 80, B ≥ 60, C ≥ 40, D ≥ 20, F below.

## Limitations

- **Outside view only.** It sees what any visitor sees. It doesn't read your repo, test authentication, or probe your database. A leaked Supabase key is reported, but it isn't used to check your Row Level Security.
- **Bot protection.** Sites behind a Cloudflare challenge or a WAF often block automated requests. When that happens, page-level checks are skipped with a note instead of being counted against you. DNS, email and TLS checks still run.
- **DKIM** is found by probing 16 common selectors. A custom selector shows as missing.
- **JS bundles** are the scripts referenced by the homepage. Code loaded only on other routes isn't scanned.
- **Point-in-time.** It's a scan, not monitoring.

## Self-hosting the web app

```bash
git clone https://github.com/rozetyp/did-you-ship.git && cd did-you-ship
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[web]"
uvicorn app:app --port 8000      # http://localhost:8000
```

| Endpoint | |
|---|---|
| `GET /` | Scanner UI |
| `GET /api/scan/{domain}` | Scan result as JSON. Rate limited to 10/min per client IP (`CF-Connecting-IP`, then `X-Forwarded-For`) |
| `GET /guides`, `/guides/{slug}` | 25 fix guides: what it is, why it matters, how to fix it per provider |
| `GET /why/{slug}` | 9 symptom pages ("why are my emails going to spam?") linking to the guides |
| `GET /sitemap.xml`, `/robots.txt`, `/health` | |

| Env var | |
|---|---|
| `SCAN_PROXY` | Optional `http://user:pass@host:port` proxy for the scanner's outbound HTTP. DNS always goes direct. |
| `PORT` | Server port (Railway sets it) |

`railway.toml` deploys it to Railway as is. Requests to a `www.` host are redirected to the bare domain. The guide pages, sitemap and social preview tags carry the original site's address: change `BASE_URL` in `pages.py` and the URLs in `static/*.html` to serve them under your own domain.

## Project layout

```
didyouship/        the scanner package (no web dependencies)
  scanner.py       scan(), every check, scoring, CHECKS registry
  bundles.py       JS bundle discovery, secret scan, source maps
  secrets.py       secret patterns and Supabase JWT role decoding
  cli.py           the `didyouship` command
app.py             FastAPI app
pages.py           renders guides, symptom pages and sitemap in memory at startup
guides_meta.py     guide content
problems_meta.py   symptom page content
static/            index.html (vanilla JS UI), page templates, assets
tests/             offline test suite (no network)
```

## Development

```bash
pip install -e ".[web,dev]"
pytest                              # offline, about 2s
pytest tests/test_bundles.py -k map # one area
pyflakes didyouship app.py pages.py tests
```

Tests never touch the network: `tests/conftest.py` stubs DNS, HTTP and TLS. CI runs on Python 3.10, 3.12 and 3.13.

To add a check:
1. Add it to `CHECKS` in `didyouship/scanner.py`.
2. Write it as a `_check_*` function that writes only its own `r.raw[...]` key.
3. Submit it in `scan()`.
4. Update the count in this README; a test fails if it's stale.

## License

[MIT](LICENSE)
