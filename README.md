# didyouship.dev

You shipped your app. But did you check? Free production readiness scanner — 24 checks in 8 seconds.

Built for developers who ship with Cursor, Replit, v0, and Bolt and forget to configure the boring stuff: email deliverability, SSL, exposed secrets, DNS, SEO meta tags, performance.

## What it checks

| Category | Checks | What breaks if you don't fix it |
|----------|--------|---------------------------------|
| **Email** | SPF, DMARC, DMARC reporting, MX vendors | Your emails go to spam, anyone can spoof your domain |
| **SSL** | Certificate validity/expiry, HTTP→HTTPS redirect | Chrome says "Not Secure", browsers block your site |
| **Secrets** | .env exposed, .git exposed, API keys in HTML source | Your database passwords and API keys are public |
| **DNS** | www resolves, www↔apex redirect | Half your visitors get an error page |
| **Security** | HSTS header | First visit can be intercepted on public WiFi |
| **SEO** | Title, meta description, OG tags, Twitter Cards, viewport, canonical, sitemap, favicon | Google can't rank you, links look ugly when shared, broken on mobile |
| **Performance** | Response time (cold start detection), compression | Users leave before the page loads |
| **Breakage** | Mixed content (HTTP resources on HTTPS pages) | Images and scripts silently don't load |
| **Polish** | Custom 404 page | Broken links show a bare error page |

Every issue includes a plain-English explanation and a copy-pasteable fix (DNS records, meta tags, config lines). Issues are sorted by priority — critical first.

## How it works

1. Enter a domain
2. Scanner runs 24 checks using public DNS queries, HTTP requests, and SSL connections
3. Each issue gets a severity (critical/high/medium/low) and an actionable fix
4. Optional: AI generates per-issue explanations via xAI Grok
5. Score = 100 minus weighted deductions (critical=20, high=12, medium=5, low=2)
6. Grade: A (80+), B (60+), C (40+), D (20+), F (<20)

All from public data. No server access needed. Nothing stored.

## Run locally

```bash
cd email-intel-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional: AI explanations
export XAI_API_KEY="your-xai-api-key"

# Start
uvicorn app:app --port 8000

# Open http://localhost:8000
```

## Deploy

```bash
# Railway
railway login && railway init && railway up

# Docker
docker build -t didyouship . && docker run -p 8000:8000 didyouship
```

## Project structure

```
email-intel-api/
├── app.py              # FastAPI — serves landing page + /api/scan endpoint
├── scanner.py          # 24 checks across 9 categories
├── ai_report.py        # Per-issue AI explanations via xAI Grok (optional)
├── static/
│   └── index.html      # Landing page + results UI
├── requirements.txt    # fastapi, uvicorn, dnspython, openai
├── Dockerfile
└── railway.toml
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `XAI_API_KEY` | No | xAI API key for AI-generated explanations and summaries |
| `PORT` | No | Server port (default: 8000) |

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Landing page |
| `GET /api/scan/{domain}` | Run all 24 checks, return issues + fixes + score |
| `GET /health` | Health check |
