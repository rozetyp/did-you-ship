#!/usr/bin/env python3
"""
Pre-generate static HTML files for every guide and problem page.
Run once after any content change:  python3 build.py

Output goes to dist/ — guides at dist/guides/, problems at dist/why/
Static assets (CSS, JS, images) stay in static/ and are served live.
"""

import json
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).parent
DIST = BASE / "dist"
STATIC = BASE / "static"

env = Environment(loader=FileSystemLoader(str(STATIC)), autoescape=False)


def render(template_name: str, context: dict) -> str:
    return env.get_template(template_name).render(**context)


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {path.relative_to(BASE)}")


def build_guide_to_problems_map():
    from problems_meta import PROBLEMS
    mapping = {}
    seen = {}
    for prob_slug, prob in PROBLEMS.items():
        for cause in prob.get("causes", []):
            g = cause.get("guide", "")
            if g:
                if g not in mapping:
                    mapping[g] = []
                    seen[g] = set()
                if prob_slug not in seen[g]:
                    seen[g].add(prob_slug)
                    mapping[g].append({"slug": prob_slug, "h1": prob["h1"]})
    return mapping


def build_sidebar_nav():
    from guides_meta import GUIDES_META, NAV
    return [
        {"cat": group["cat"], "guides": [
            {"slug": s, "title": GUIDES_META[s]["title"]}
            for s in group["guides"] if s in GUIDES_META
        ]}
        for group in NAV
    ]


def guide_schema(slug, meta):
    title = meta["seo_title"]
    description = meta["description"]
    steps = meta.get("how_steps", [])
    if not steps:
        return ""
    howto = {
        "@context": "https://schema.org", "@type": "HowTo",
        "name": "How to fix: " + title.split("|")[0].strip(),
        "description": description,
        "step": [{"@type": "HowToStep", "text": s, "position": i + 1} for i, s in enumerate(steps)],
    }
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://didyouship.com"},
            {"@type": "ListItem", "position": 2, "name": meta.get("category", "Guide"), "item": f"https://didyouship.com/guides/{slug}"},
        ],
    }
    return (f'<script type="application/ld+json">{json.dumps(howto)}</script>\n'
            f'<script type="application/ld+json">{json.dumps(breadcrumb)}</script>')


def problem_schema(slug, page):
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in page["faqs"]
        ],
    }
    article = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": page["h1"], "description": page["description"],
        "url": f"https://didyouship.com/why/{slug}",
        "publisher": {"@type": "Organization", "name": "didyouship.com", "url": "https://didyouship.com"},
    }
    return (f'<script type="application/ld+json">{json.dumps(faq)}</script>\n'
            f'<script type="application/ld+json">{json.dumps(article)}</script>')


def build():
    from guides_meta import GUIDES_META, ALL_SLUGS, NAV
    from problems_meta import PROBLEMS, ALL_PROBLEM_SLUGS

    guide_to_problems = build_guide_to_problems_map()
    sidebar_nav = build_sidebar_nav()

    # Guide pages
    print(f"Building {len(ALL_SLUGS)} guide pages...")
    for slug in ALL_SLUGS:
        meta = GUIDES_META[slug]
        html = render("guide.html", {
            "slug": slug,
            "title": meta["seo_title"],
            "description": meta["description"],
            "schema": guide_schema(slug, meta),
            "guide_title": meta.get("title", ""),
            "guide_summary": meta.get("summary", ""),
            "guide_severity": meta.get("severity", ""),
            "guide_category": meta.get("category", ""),
            "guide_what": meta.get("what", ""),
            "guide_why": meta.get("why", ""),
            "guide_how": meta.get("how", ""),
            "guide_providers": meta.get("providers", ""),
            "related_problems": guide_to_problems.get(slug, []),
            "sidebar_nav": sidebar_nav,
            "index_groups": [],
        })
        write(DIST / "guides" / f"{slug}.html", html)

    # Guides index
    groups = [
        {"cat": group["cat"], "guides": [
            {"slug": s, "title": GUIDES_META[s]["title"],
             "summary": GUIDES_META[s]["summary"],
             "severity": GUIDES_META[s]["severity"]}
            for s in group["guides"] if s in GUIDES_META
        ]}
        for group in NAV
    ]
    html = render("guide.html", {
        "slug": "", "title": "Production Readiness Guides (2026) | didyouship.com",
        "description": "Educational guides for SPF, DKIM, DMARC, SSL, security headers, SEO, and performance.",
        "schema": "", "guide_title": "", "guide_summary": "", "guide_severity": "",
        "guide_category": "", "guide_what": "", "guide_why": "", "guide_how": "",
        "guide_providers": "", "related_problems": [], "sidebar_nav": sidebar_nav,
        "index_groups": groups,
    })
    write(DIST / "guides" / "index.html", html)

    # Problem pages
    print(f"\nBuilding {len(ALL_PROBLEM_SLUGS)} problem pages...")
    other_all = [{"slug": s, "h1": PROBLEMS[s]["h1"]} for s in ALL_PROBLEM_SLUGS]
    for slug in ALL_PROBLEM_SLUGS:
        page = PROBLEMS[slug]
        html = render("problem.html", {
            "slug": slug,
            "title": page["seo_title"],
            "description": page["description"],
            "schema": problem_schema(slug, page),
            "page": page,
            "other_problems": [p for p in other_all if p["slug"] != slug],
        })
        write(DIST / "why" / f"{slug}.html", html)

    # Sitemap
    base = "https://didyouship.com"
    urls = [base + "/", base + "/guides"]
    urls += [f"{base}/guides/{s}" for s in ALL_SLUGS]
    urls += [f"{base}/why/{s}" for s in ALL_PROBLEM_SLUGS]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
    sitemap += "</urlset>"
    write(DIST / "sitemap.xml", sitemap)

    write(DIST / "robots.txt",
          "User-agent: *\nAllow: /\n\nSitemap: https://didyouship.com/sitemap.xml\n")

    print(f"\nDone — {len(ALL_SLUGS) + len(ALL_PROBLEM_SLUGS) + 3} files in dist/")


if __name__ == "__main__":
    build()
