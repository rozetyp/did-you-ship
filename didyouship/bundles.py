"""JS bundle scanning: secrets shipped to the browser, and exposed source maps.

Only the site's own scripts are fetched (same host or a subdomain of it).
Third-party CDNs are skipped. Everything here reads public files exactly as a
browser would. Found keys are never used.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from urllib.parse import urljoin, urlparse

from .secrets import find_secrets

MAX_BUNDLES = 15
MAX_BUNDLE_BYTES = 5 * 1024 * 1024
MAX_MAP_BYTES = 64 * 1024

# fetch(url, max_bytes) -> (status, text). May raise on network errors.
Fetch = Callable[[str, int], "tuple[int, str]"]

_SCRIPT_SRC = re.compile(r"<script\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_PRELOAD = re.compile(r"<link\b[^>]*?\brel\s*=\s*[\"']?modulepreload[\"']?[^>]*>", re.IGNORECASE)
_HREF = re.compile(r"\bhref\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_SOURCEMAP = re.compile(r"//[#@]\s*sourceMappingURL=(\S+)\s*$")


def _same_site(url: str, domain: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == domain or host.endswith("." + domain)


def script_urls(html: str, page_url: str, domain: str) -> list[str]:
    """Absolute URLs of the site's own scripts, in page order, capped at MAX_BUNDLES."""
    raw = _SCRIPT_SRC.findall(html)
    for tag in _PRELOAD.findall(html):
        m = _HREF.search(tag)
        if m:
            raw.append(m.group(1))

    urls: list[str] = []
    for src in raw:
        absolute = urljoin(page_url, src.strip()).split("#", 1)[0]
        if urlparse(absolute).scheme not in ("http", "https"):
            continue
        if _same_site(absolute, domain) and absolute not in urls:
            urls.append(absolute)
    return urls[:MAX_BUNDLES]


def _map_url(bundle_url: str, body: str) -> str | None:
    m = _SOURCEMAP.search(body[-1000:])
    if m:
        target = m.group(1)
        return None if target.startswith("data:") else urljoin(bundle_url, target)
    if urlparse(bundle_url).path.endswith(".js"):
        return bundle_url + ".map"
    return None


_SOURCES = re.compile(r'"sources"\s*:\s*\[')
_JSON_STR = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _is_source_map(status: int, text: str) -> bool:
    """A public source map that reveals the site's own code.

    Maps with no sources, or only third-party/bundler code (node_modules,
    webpack runtime, framework polyfills), reveal nothing worth reporting.
    """
    head = text.lstrip()
    if status != 200 or not head.startswith("{") or '"version"' not in head:
        return False
    m = _SOURCES.search(head)
    if not m:
        return False
    rest = head[m.end():]
    end = rest.find("]")
    if end == -1:
        return True  # source list longer than we read: plenty of real files
    sources = _JSON_STR.findall(rest[:end])
    return any("node_modules" not in s and not s.startswith(("webpack/", "turbopack:///[")) for s in sources)


def scan_bundles(html: str, page_url: str, domain: str, fetch: Fetch) -> dict:
    """Fetch the page's own bundles; report secrets and exposed source maps.

    Returns {"bundles": [url], "secrets": {label: [bundle_url]}, "source_maps": [map_url]}.
    """
    urls = script_urls(html, page_url, domain)
    report: dict = {"bundles": urls, "secrets": {}, "source_maps": []}
    if not urls:
        return report

    def inspect(url: str):
        try:
            status, body = fetch(url, MAX_BUNDLE_BYTES)
        except Exception:
            return url, [], None
        if status != 200:
            return url, [], None
        labels = find_secrets(body)
        map_url = _map_url(url, body)
        exposed = None
        if map_url and _same_site(map_url, domain):
            try:
                if _is_source_map(*fetch(map_url, MAX_MAP_BYTES)):
                    exposed = map_url
            except Exception:
                pass
        return url, labels, exposed

    with ThreadPoolExecutor(max_workers=6) as pool:
        for url, labels, exposed in pool.map(inspect, urls):
            for label in labels:
                report["secrets"].setdefault(label, []).append(url)
            if exposed:
                report["source_maps"].append(exposed)
    return report
