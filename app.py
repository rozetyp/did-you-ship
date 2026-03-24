"""
didyouship.com — production readiness scanner.

GET /             → landing page
GET /api/scan/{domain} → run 24 checks, return issues + fixes + score
GET /health       → health check
"""

import os
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("didyouship")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="didyouship.com",
    description="You shipped. But did you check? 24 production readiness checks in 8 seconds.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_executor = ThreadPoolExecutor(max_workers=20)
_templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "static"))


@app.get("/api/scan/{domain}")
@limiter.limit("10/minute")
async def public_scan(domain: str, request: Request):
    """Full production readiness scan.
    24 checks across 9 categories: email, SSL, secrets, DNS, security,
    SEO, performance, breakage, polish.
    Returns issues with fixes, score, grade, and AI explanations."""
    from scanner import scan

    domain = domain.strip().lower()
    if "." not in domain or len(domain) > 255:
        raise HTTPException(400, "Invalid domain")

    log.info("scan started domain=%s ip=%s", domain, get_remote_address(request))

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, scan, domain)

    log.info(
        "scan complete domain=%s score=%d grade=%s issues=%d",
        domain, result.score, result.grade, len(result.issues),
    )

    # AI explanations (optional — needs XAI_API_KEY)
    explanations = {}
    summary = None
    try:
        from ai_report import explain_issues, generate_summary
        explanations = explain_issues(result)
        summary = generate_summary(result)
    except Exception:
        pass

    issues_list = []
    for i in result.issues:
        issue = {
            "category": i.category,
            "severity": i.severity,
            "title": i.title,
            "detail": i.detail,
            "fix": i.fix,
        }
        if i.title in explanations:
            issue["ai_explanation"] = explanations[i.title]
        issues_list.append(issue)

    return {
        "domain": result.domain,
        "score": result.score,
        "grade": result.grade,
        "summary": summary,
        "issues": issues_list,
        "passed": result.passed,
        "issue_count": len(result.issues),
        "critical_count": sum(1 for i in result.issues if i.severity == "critical"),
        "high_count": sum(1 for i in result.issues if i.severity == "high"),
        "email_vendors": result.email_vendors,
        "mx_vendors": result.mx_vendors,
        "ssl": result.raw.get("ssl", {}),
        "raw": result.raw,
    }


@app.get("/guides/{slug}")
async def guide_page(slug: str, request: Request):
    from guides_meta import GUIDES_META
    meta = GUIDES_META.get(slug)

    if meta:
        title = meta["seo_title"]
        description = meta["description"]
        steps = meta.get("how_steps", [])
        schema = ""
        if steps:
            schema = '<script type="application/ld+json">' + json.dumps({
                "@context": "https://schema.org",
                "@type": "HowTo",
                "name": "How to fix: " + title.split("|")[0].strip(),
                "description": description,
                "step": [
                    {"@type": "HowToStep", "text": s, "position": i + 1}
                    for i, s in enumerate(steps)
                ],
            }) + '</script>\n<script type="application/ld+json">' + json.dumps({
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://didyouship.com"},
                    {"@type": "ListItem", "position": 2, "name": meta.get("category", "Guide"), "item": "https://didyouship.com/guides/" + slug},
                ],
            }) + '</script>'
    else:
        title = "Production Readiness Guides — didyouship.com"
        description = "Educational guides for every production readiness issue: SPF, DKIM, DMARC, SSL, security headers, SEO, performance, and more."
        schema = ""

    return _templates.TemplateResponse(request, "guide.html", {
        "slug": slug,
        "title": title,
        "description": description,
        "schema": schema,
    })


@app.get("/why/{slug}")
async def problem_page(slug: str, request: Request):
    from problems_meta import PROBLEMS, ALL_PROBLEM_SLUGS
    page = PROBLEMS.get(slug)
    if not page:
        raise HTTPException(404, "Problem page not found")

    title = page["seo_title"]
    description = page["description"]

    # FAQ schema — the biggest SEO lever for symptom-driven queries
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq["q"],
                "acceptedAnswer": {"@type": "Answer", "text": faq["a"]},
            }
            for faq in page["faqs"]
        ],
    }
    # Article schema for general authority signals
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page["h1"],
        "description": description,
        "url": f"https://didyouship.com/why/{slug}",
        "publisher": {"@type": "Organization", "name": "didyouship.com", "url": "https://didyouship.com"},
    }
    schema = (
        '<script type="application/ld+json">' + json.dumps(faq_schema) + '</script>\n'
        '<script type="application/ld+json">' + json.dumps(article_schema) + '</script>'
    )

    # Other problems for internal linking
    other_problems = [
        {"slug": s, "h1": PROBLEMS[s]["h1"]}
        for s in ALL_PROBLEM_SLUGS
        if s != slug
    ]

    return _templates.TemplateResponse(request, "problem.html", {
        "slug": slug,
        "title": title,
        "description": description,
        "schema": schema,
        "page": page,
        "other_problems": other_problems,
    })


@app.get("/sitemap.xml")
async def sitemap():
    from guides_meta import ALL_SLUGS
    from problems_meta import ALL_PROBLEM_SLUGS
    base = "https://didyouship.com"
    urls = [base + "/"]
    for slug in ALL_SLUGS:
        urls.append(f"{base}/guides/{slug}")
    for slug in ALL_PROBLEM_SLUGS:
        urls.append(f"{base}/why/{slug}")
    body = '<?xml version="1.0" encoding="UTF-8"?>\n'
    body += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        body += f"  <url><loc>{url}</loc></url>\n"
    body += "</urlset>"
    return Response(content=body, media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "didyouship"}


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
