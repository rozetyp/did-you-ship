import json

import pytest

from didyouship import cli
from didyouship.scanner import Issue, ScanResult


def fake_result(*severities):
    r = ScanResult(domain="example.com", url="https://example.com", score=70, grade="B")
    r.issues = [Issue("email", s, f"{s} problem", "what breaks", "line one\nline two") for s in severities]
    r.passed = ["SPF record configured correctly"]
    r.notes = ["something was skipped"]
    return r


@pytest.fixture
def scanned(monkeypatch):
    def install(result):
        monkeypatch.setattr(cli, "scan", lambda domain: result)
    return install


@pytest.mark.parametrize("severities,threshold,code", [
    (["high"], "none", 0),
    (["high"], "critical", 0),
    (["high"], "high", 2),
    (["low"], "medium", 0),
    (["low"], "low", 2),
    ([], "low", 0),
])
def test_exit_codes(scanned, severities, threshold, code):
    scanned(fake_result(*severities))
    assert cli.main(["example.com", "--fail-on", threshold]) == code


def test_invalid_domain_exits_1(capsys):
    assert cli.main(["localhost"]) == 1
    assert "not a public domain" in capsys.readouterr().err


def test_json_output(scanned, capsys):
    scanned(fake_result("critical"))
    cli.main(["https://www.example.com/", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["grade"] == "B" and data["critical_count"] == 1 and data["notes"] == ["something was skipped"]


def test_text_output_has_fixes_notes_and_no_color_when_piped(scanned, capsys):
    scanned(fake_result("medium", "critical"))
    cli.main(["example.com"])
    out = capsys.readouterr().out
    assert "\033[" not in out
    assert out.index("CRITICAL") < out.index("MEDIUM")
    assert "fix: line one" in out and "line two" in out
    assert "NOTE" in out and "1 passed" in out
