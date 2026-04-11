"""
didyouship.com — production readiness scanner.

GET /             → landing page
GET /api/scan/{domain} → run 26 checks, return issues + fixes + score
GET /health       → health check
"""

import os
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_ipaddr
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("didyouship")

limiter = Limiter(key_func=get_ipaddr)

app = FastAPI(
    title="didyouship.com",
    description="You shipped. But did you check? 26 production readiness checks in 8 seconds.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class HSTSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(HSTSMiddleware)

_executor = ThreadPoolExecutor(max_workers=20)
_templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "static"))
_dist = os.path.join(os.path.dirname(__file__), "dist")


def _static_file(path: str):
    """Serve a pre-built static file from dist/, or None if it doesn't exist."""
    full = os.path.join(_dist, path)
    if os.path.isfile(full):
        return FileResponse(full, media_type="text/html")
    return None


@app.get("/api/scan/{domain}")
@limiter.limit("10/minute")
async def public_scan(domain: str, request: Request):
    """Full production readiness scan.
    26 checks across 9 categories: email, SSL, secrets, DNS, security,
    SEO, performance, breakage, polish.
    Returns issues with fixes, score, and grade."""
    from scanner import scan

    domain = domain.strip().lower()
    if "." not in domain or len(domain) > 255:
        raise HTTPException(400, "Invalid domain")

    log.info("scan started domain=%s ip=%s", domain, get_ipaddr(request))

    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, scan, domain),
            timeout=25,
        )
    except asyncio.TimeoutError:
        log.warning("scan timeout domain=%s", domain)
        raise HTTPException(504, "Scan timed out — the domain may be unreachable")

    log.info(
        "scan complete domain=%s score=%d grade=%s issues=%d",
        domain, result.score, result.grade, len(result.issues),
    )

    issues_list = [
        {
            "category": i.category,
            "severity": i.severity,
            "title": i.title,
            "detail": i.detail,
            "fix": i.fix,
        }
        for i in result.issues
    ]

    return {
        "domain": result.domain,
        "score": result.score,
        "grade": result.grade,
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


def _build_guide_to_problems_map():
    """Build reverse map: guide_slug → list of {slug, h1} problem pages that reference it."""
    from problems_meta import PROBLEMS
    mapping: dict[str, list[dict]] = {}
    seen: dict[str, set] = {}
    for prob_slug, prob in PROBLEMS.items():
        for cause in prob.get("causes", []):
            guide = cause.get("guide", "")
            if guide:
                if guide not in mapping:
                    mapping[guide] = []
                    seen[guide] = set()
                if prob_slug not in seen[guide]:
                    seen[guide].add(prob_slug)
                    mapping[guide].append({"slug": prob_slug, "h1": prob["h1"]})
    return mapping


def _build_sidebar_nav():
    from guides_meta import GUIDES_META, NAV
    return [
        {"cat": group["cat"], "guides": [
            {"slug": s, "title": GUIDES_META[s]["title"]}
            for s in group["guides"] if s in GUIDES_META
        ]}
        for group in NAV
    ]


def _build_related_guides_map():
    from guides_meta import GUIDES_META, NAV
    mapping = {}
    for group in NAV:
        cat_slugs = [s for s in group["guides"] if s in GUIDES_META]
        for slug in cat_slugs:
            mapping[slug] = [
                {"slug": s, "title": GUIDES_META[s]["title"]}
                for s in cat_slugs if s != slug
            ]
    return mapping


def _render_guides_index(request):
    from guides_meta import GUIDES_META, NAV
    sidebar_nav = _build_sidebar_nav()
    groups = [{"cat": g["cat"], "guides": [
        {"slug": s, "title": GUIDES_META[s]["title"], "summary": GUIDES_META[s]["summary"], "severity": GUIDES_META[s]["severity"]}
        for s in g["guides"] if s in GUIDES_META
    ]} for g in NAV]
    return _templates.TemplateResponse(request, "guide.html", {
        "slug": "", "canonical_url": "https://didyouship.com/guides",
        "title": "Production Readiness Guides (2026) | didyouship.com",
        "description": "Educational guides for SPF, DKIM, DMARC, SSL, security headers, SEO, and performance.",
        "schema": "", "guide_title": "", "guide_summary": "", "guide_severity": "",
        "guide_category": "", "guide_what": "", "guide_why": "", "guide_how": "",
        "guide_providers": "", "related_problems": [], "related_guides": [],
        "sidebar_nav": sidebar_nav, "index_groups": groups,
    })


def _render_guide(slug, request):
    from guides_meta import GUIDES_META
    meta = GUIDES_META.get(slug)
    if not meta:
        raise HTTPException(404, "Guide not found")
    steps = meta.get("how_steps", [])
    schema = ""
    if steps:
        schema = '<script type="application/ld+json">' + json.dumps({
            "@context": "https://schema.org", "@type": "HowTo",
            "name": "How to fix: " + meta["seo_title"].split("|")[0].strip(),
            "description": meta["description"],
            "step": [{"@type": "HowToStep", "text": s, "position": i+1} for i, s in enumerate(steps)],
        }) + '</script>'
    return _templates.TemplateResponse(request, "guide.html", {
        "slug": slug, "canonical_url": f"https://didyouship.com/guides/{slug}",
        "title": meta["seo_title"], "description": meta["description"],
        "schema": schema, "guide_title": meta.get("title", ""),
        "guide_summary": meta.get("summary", ""), "guide_severity": meta.get("severity", ""),
        "guide_category": meta.get("category", ""), "guide_what": meta.get("what", ""),
        "guide_why": meta.get("why", ""), "guide_how": meta.get("how", ""),
        "guide_providers": meta.get("providers", ""),
        "related_problems": _build_guide_to_problems_map().get(slug, []),
        "related_guides": _build_related_guides_map().get(slug, []),
        "sidebar_nav": _build_sidebar_nav(), "index_groups": [],
    })


def _render_problem(slug, request):
    from problems_meta import PROBLEMS, ALL_PROBLEM_SLUGS
    page = PROBLEMS.get(slug)
    if not page:
        raise HTTPException(404, "Problem page not found")
    faq_schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
        for f in page["faqs"]
    ]}
    article_schema = {"@context": "https://schema.org", "@type": "Article",
        "headline": page["h1"], "description": page["description"],
        "url": f"https://didyouship.com/why/{slug}",
        "publisher": {"@type": "Organization", "name": "didyouship.com", "url": "https://didyouship.com"}}
    schema = (f'<script type="application/ld+json">{json.dumps(faq_schema)}</script>\n'
              f'<script type="application/ld+json">{json.dumps(article_schema)}</script>')
    other = [{"slug": s, "h1": PROBLEMS[s]["h1"]} for s in ALL_PROBLEM_SLUGS if s != slug]
    return _templates.TemplateResponse(request, "problem.html", {
        "slug": slug, "title": page["seo_title"], "description": page["description"],
        "schema": schema, "page": page, "other_problems": other,
    })


@app.get("/guides")
async def guides_index(request: Request):
    return _static_file("guides/index.html") or _render_guides_index(request)


@app.get("/guides/{slug}")
async def guide_page(slug: str, request: Request):
    return _static_file(f"guides/{slug}.html") or _render_guide(slug, request)


@app.get("/why/{slug}")
async def problem_page(slug: str, request: Request):
    return _static_file(f"why/{slug}.html") or _render_problem(slug, request)


@app.get("/robots.txt")
async def robots():
    f = _static_file("robots.txt")
    if f: return f
    return Response(content="User-agent: *\nAllow: /\nSitemap: https://didyouship.com/sitemap.xml\n", media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap():
    f = _static_file("sitemap.xml")
    if f: return f
    raise HTTPException(503, "Run build.py to generate sitemap")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "didyouship"}


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "404.html"),
        status_code=404,
    )


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.get("/")
async def root():
    f = _static_file("index.html")
    if f: return f
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
