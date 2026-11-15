"""Offline fixtures: no test touches the network."""

from __future__ import annotations

import email.message
import io
import socket
import urllib.error

import dns.resolver
import pytest

from didyouship import scanner


class FakeResponse:
    def __init__(self, status=200, body="", headers=None):
        self.status = status
        self._body = body.encode() if isinstance(body, str) else body
        self.headers = email.message.Message()
        for k, v in (headers or {"Content-Type": "text/html"}).items():
            self.headers[k] = v

    def read(self, n=-1):
        return self._body if n is None or n < 0 else self._body[:n]


def http_error(url, code, body=""):
    return urllib.error.HTTPError(url, code, "error", email.message.Message(), io.BytesIO(body.encode()))


class Web:
    """Programmable stand-in for scanner._urlopen. Unknown URLs raise URLError."""

    def __init__(self):
        self.routes = {}
        self.calls = []

    def add(self, url, body="", status=200, headers=None):
        self.routes[url] = FakeResponse(status, body, headers)

    def fail(self, url, exc):
        self.routes[url] = exc

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        self.calls.append(url)
        hit = self.routes.get(url)
        if hit is None:
            raise urllib.error.URLError("offline")
        if isinstance(hit, Exception):
            raise hit
        if hit.status >= 400:
            raise http_error(url, hit.status, hit._body.decode())
        return hit


@pytest.fixture
def offline(monkeypatch):
    """Cut every network path the scanner uses. Returns the fake web."""
    def no_dns(*a, **k):
        raise dns.resolver.NXDOMAIN()

    def no_socket(*a, **k):
        raise OSError("network disabled in tests")

    web = Web()
    monkeypatch.setattr(scanner, "dns_query", no_dns)
    monkeypatch.setattr(dns.resolver, "resolve", no_dns)
    monkeypatch.setattr(scanner, "_ssl_connect", no_socket)
    monkeypatch.setattr(scanner, "_urlopen", web)
    monkeypatch.setattr(socket.socket, "connect", no_socket)
    return web


class TXT:
    def __init__(self, text):
        self.text = text

    def to_text(self):
        return f'"{self.text}"'


@pytest.fixture
def dns_records(monkeypatch):
    """Serve fixed TXT records: dns_records({("example.com", "TXT"): ["v=spf1 ..."]})."""
    def install(records: dict):
        def fake(qname, qtype, lifetime=None):
            if (qname, qtype) in records:
                return [TXT(t) for t in records[(qname, qtype)]]
            raise dns.resolver.NXDOMAIN()
        monkeypatch.setattr(scanner, "dns_query", fake)
    return install


@pytest.fixture
def result():
    r = scanner.ScanResult(domain="example.com", url="https://example.com")
    r.raw = {k: {} for k in ("email", "ssl", "headers", "dns", "seo", "performance", "secrets", "breakage")}
    return r
