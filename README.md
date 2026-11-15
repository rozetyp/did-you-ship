# didyouship

**You shipped your app. But did you check?**

A production readiness scanner for the stuff nobody teaches: email that lands in spam, keys shipped to the browser, a `.env` file anyone can download, broken link previews, a `www.` that shows an error page. It runs 28 checks against a domain in about 5-15 seconds, using only public data (DNS, TLS, HTTP), and tells you what breaks and how to fix it.

- **Web:** [didyouship.com](https://didyouship.com), free, no signup, nothing stored
- **CLI:** `didyouship example.com`, with JSON output and a CI exit code
- **Self-host:** a small FastAPI app, MIT licensed

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

The hosted version runs on Railway (`railway.toml`) behind Cloudflare.

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
