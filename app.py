"""
didyouship.com web app.

GET /                   landing page with the scanner
GET /api/scan/{domain}  run every check, return issues + fixes + score
GET /guides[/{slug}]    fix guides          (rendered at startup by pages.py)
GET /why/{slug}         symptom pages       (rendered at startup by pages.py)
GET /health             health check
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from didyouship.scanner import CHECK_COUNT, is_valid_domain, normalize_domain, scan
from pages import render_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("didyouship")

STATIC = os.path.join(os.path.dirname(__file__), "static")
PAGES = render_all()


def client_ip(request: Request) -> str:
    """Real visitor IP behind Cloudflare + Railway's proxy."""
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=client_ip)

app = FastAPI(
    title="didyouship.com",
    description=f"You shipped. But did you check? {CHECK_COUNT} production readiness checks in seconds.",
    version="2.0.0",
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


@app.get("/api/scan/{domain}")
@limiter.limit("10/minute")
async def public_scan(domain: str, request: Request):
    """Full production readiness scan. Returns issues with fixes, score and grade."""
    domain = normalize_domain(domain)
    if not is_valid_domain(domain):
        raise HTTPException(400, "Invalid domain")

    log.info("scan started domain=%s ip=%s", domain, client_ip(request))
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(loop.run_in_executor(_executor, scan, domain), timeout=25)
    except asyncio.TimeoutError:
        log.warning("scan timeout domain=%s", domain)
        raise HTTPException(504, "Scan timed out - the domain may be unreachable")

    log.info("scan complete domain=%s score=%d grade=%s issues=%d",
             domain, result.score, result.grade, len(result.issues))
    return result.to_dict()


def _page(path: str) -> HTMLResponse:
    body = PAGES.get(path)
    if body is None:
        raise HTTPException(404)
    return HTMLResponse(body)


@app.get("/guides")
async def guides_index():
    return _page("/guides")


@app.get("/guides/{slug}")
async def guide_page(slug: str):
    return _page(f"/guides/{slug}")


@app.get("/why/{slug}")
async def problem_page(slug: str):
    return _page(f"/why/{slug}")


@app.get("/robots.txt")
async def robots():
    return Response(PAGES["/robots.txt"], media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap():
    return Response(PAGES["/sitemap.xml"], media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "didyouship"}


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return FileResponse(os.path.join(STATIC, "404.html"), status_code=404)


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC, "index.html"))
