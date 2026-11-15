"""Render the guide pages, problem pages, sitemap and robots.txt.

Everything is rendered once, in memory, when the web app starts (a few
milliseconds). Content lives in guides_meta.py and problems_meta.py; the
templates are static/guide.html and static/problem.html.
"""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from didyouship.scanner import CHECK_COUNT
from guides_meta import ALL_SLUGS, GUIDES_META, NAV
from problems_meta import ALL_PROBLEM_SLUGS, PROBLEMS

BASE_URL = "https://didyouship.com"
LASTMOD = "2026-11-15"  # bump when guide/problem content changes

_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "static")), autoescape=False)


def _ld(obj: dict) -> str:
    return f'<script type="application/ld+json">{json.dumps(obj)}</script>'


def _guide_to_problems() -> dict[str, list[dict]]:
    """guide slug -> problem pages whose causes link to it."""
    mapping: dict[str, list[dict]] = {}
    for prob_slug, prob in PROBLEMS.items():
        for cause in prob.get("causes", []):
            g = cause.get("guide", "")
            entry = {"slug": prob_slug, "h1": prob["h1"]}
            if g and entry not in mapping.setdefault(g, []):
                mapping[g].append(entry)
    return mapping


def _sidebar_nav() -> list[dict]:
    return [
        {"cat": group["cat"], "guides": [
            {"slug": s, "title": GUIDES_META[s]["title"]} for s in group["guides"] if s in GUIDES_META
        ]}
        for group in NAV
    ]


def _related_guides() -> dict[str, list[dict]]:
    """guide slug -> other guides in the same NAV category."""
    mapping = {}
    for group in NAV:
        slugs = [s for s in group["guides"] if s in GUIDES_META]
        for slug in slugs:
            mapping[slug] = [{"slug": s, "title": GUIDES_META[s]["title"]} for s in slugs if s != slug]
    return mapping


def _guide_schema(slug: str, meta: dict) -> str:
    steps = meta.get("how_steps", [])
    if not steps:
        return ""
    howto = {
        "@context": "https://schema.org", "@type": "HowTo",
        "name": "How to fix: " + meta["seo_title"].split("|")[0].strip(),
        "description": meta["description"],
        "step": [{"@type": "HowToStep", "text": s, "position": i + 1} for i, s in enumerate(steps)],
    }
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": meta.get("category", "Guide"),
             "item": f"{BASE_URL}/guides/{slug}"},
        ],
    }
    return _ld(howto) + "\n" + _ld(breadcrumb)


def _problem_schema(slug: str, page: dict) -> str:
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in page["faqs"]
        ],
    }
    article = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": page["h1"], "description": page["description"],
        "url": f"{BASE_URL}/why/{slug}",
        "publisher": {"@type": "Organization", "name": "didyouship.com", "url": BASE_URL},
    }
    return _ld(faq) + "\n" + _ld(article)


_EMPTY_GUIDE = {
    "schema": "", "guide_title": "", "guide_summary": "", "guide_severity": "",
    "guide_category": "", "guide_what": "", "guide_why": "", "guide_how": "",
    "guide_providers": "", "related_problems": [], "related_guides": [], "index_groups": [],
}


def render_all() -> dict[str, str]:
    """Return {url path: body} for every generated page, e.g. "/guides/spf-record"."""
    guide = _env.get_template("guide.html")
    problem = _env.get_template("problem.html")
    sidebar = _sidebar_nav()
    to_problems = _guide_to_problems()
    related = _related_guides()
    out: dict[str, str] = {}

    for slug in ALL_SLUGS:
        meta = GUIDES_META[slug]
        out[f"/guides/{slug}"] = guide.render(**{
            **_EMPTY_GUIDE,
            "slug": slug,
            "canonical_url": f"{BASE_URL}/guides/{slug}",
            "title": meta["seo_title"],
            "description": meta["description"],
            "schema": _guide_schema(slug, meta),
            "guide_title": meta.get("title", ""),
            "guide_summary": meta.get("summary", ""),
            "guide_severity": meta.get("severity", ""),
            "guide_category": meta.get("category", ""),
            "guide_what": meta.get("what", ""),
            "guide_why": meta.get("why", ""),
            "guide_how": meta.get("how", ""),
            "guide_providers": meta.get("providers", ""),
            "related_problems": to_problems.get(slug, []),
            "related_guides": related.get(slug, []),
            "sidebar_nav": sidebar,
            "check_count": CHECK_COUNT,
        })

    out["/guides"] = guide.render(**{
        **_EMPTY_GUIDE,
        "slug": "",
        "canonical_url": f"{BASE_URL}/guides",
        "title": "Production Readiness Guides | didyouship.com",
        "description": "Guides for SPF, DKIM, DMARC, SSL, security headers, SEO, and performance.",
        "sidebar_nav": sidebar,
        "check_count": CHECK_COUNT,
        "index_groups": [
            {"cat": g["cat"], "guides": [
                {"slug": s, "title": GUIDES_META[s]["title"], "summary": GUIDES_META[s]["summary"],
                 "severity": GUIDES_META[s]["severity"]}
                for s in g["guides"] if s in GUIDES_META
            ]}
            for g in NAV
        ],
    })

    for slug in ALL_PROBLEM_SLUGS:
        page = PROBLEMS[slug]
        out[f"/why/{slug}"] = problem.render(
            slug=slug,
            title=page["seo_title"],
            description=page["description"],
            schema=_problem_schema(slug, page),
            page=page,
            other_problems=[{"slug": s, "h1": PROBLEMS[s]["h1"]} for s in ALL_PROBLEM_SLUGS if s != slug],
            check_count=CHECK_COUNT,
        )

    urls = ["/", "/guides"] + [f"/guides/{s}" for s in ALL_SLUGS] + [f"/why/{s}" for s in ALL_PROBLEM_SLUGS]
    out["/sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{BASE_URL}{u}</loc><lastmod>{LASTMOD}</lastmod></url>\n" for u in urls)
        + "</urlset>"
    )
    out["/robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n"
    return out
