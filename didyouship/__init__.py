"""didyouship: production readiness scanner for anything you just shipped."""

__version__ = "2.0.0"

from .scanner import CHECK_COUNT, CHECKS, Issue, ScanResult, scan  # noqa: E402

__all__ = ["scan", "ScanResult", "Issue", "CHECKS", "CHECK_COUNT", "__version__"]
