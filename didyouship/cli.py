"""Command-line interface: `didyouship example.com`."""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .scanner import CHECK_COUNT, ScanResult, is_valid_domain, normalize_domain, scan

SEVERITIES = ["critical", "high", "medium", "low"]
_COLORS = {"critical": "31", "high": "33", "medium": "36", "low": "2", "pass": "32", "dim": "2", "bold": "1"}


def _paint(text: str, kind: str, color: bool) -> str:
    return f"\033[{_COLORS[kind]}m{text}\033[0m" if color else text


def format_text(r: ScanResult, color: bool = False) -> str:
    """Human-readable report: grade line, issues by severity with fixes, notes, passes."""
    out = [_paint(f"{r.domain}  {r.score}/100  grade {r.grade}", "bold", color), ""]
    issues = sorted(r.issues, key=lambda i: SEVERITIES.index(i.severity) if i.severity in SEVERITIES else 9)
    for i in issues:
        out.append(f"{_paint(i.severity.upper().ljust(8), i.severity, color)} [{i.category}] {i.title}")
        out.append(f"         {i.detail}")
        if i.fix:
            out.extend(f"         {_paint('fix:', 'dim', color) if n == 0 else '    '} {line}"
                       for n, line in enumerate(i.fix.splitlines()))
        out.append("")
    for note in r.notes:
        out.append(f"{_paint('NOTE', 'dim', color)}     {note}")
        out.append("")
    out.append(_paint(f"{len(r.passed)} passed", "pass", color) + _paint(
        f" · {len(r.issues)} issues · {CHECK_COUNT} checks", "dim", color))
    return "\n".join(out)


def fails(r: ScanResult, threshold: str) -> bool:
    """True if any issue is at or above `threshold` severity ("none" never fails)."""
    if threshold == "none":
        return False
    limit = SEVERITIES.index(threshold)
    return any(i.severity in SEVERITIES and SEVERITIES.index(i.severity) <= limit for i in r.issues)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="didyouship",
        description=f"Production readiness scan: {CHECK_COUNT} checks across email, SSL, secrets, "
                    "DNS, headers, SEO and performance, using public data only.",
    )
    parser.add_argument("domain", help="domain, URL or email address, e.g. example.com")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument("--fail-on", choices=SEVERITIES + ["none"], default="none",
                        help="exit with status 2 if any issue is at or above this severity (for CI)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    domain = normalize_domain(args.domain)
    if not is_valid_domain(domain):
        print(f"didyouship: not a public domain name: {args.domain!r}", file=sys.stderr)
        return 1

    result = scan(domain)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
        print(format_text(result, color=color))
    return 2 if fails(result, args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(main())
