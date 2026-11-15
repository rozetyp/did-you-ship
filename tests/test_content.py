"""Cross-file consistency: links between scanner, frontend, content and README."""

import re
from pathlib import Path

from didyouship.scanner import CHECK_COUNT
from guides_meta import ALL_SLUGS, GUIDES_META
from problems_meta import PROBLEMS

ROOT = Path(__file__).resolve().parent.parent


def test_nav_and_meta_agree():
    assert set(ALL_SLUGS) == set(GUIDES_META)


def test_problem_causes_link_to_real_guides():
    for slug, page in PROBLEMS.items():
        for cause in page.get("causes", []):
            if cause.get("guide"):
                assert cause["guide"] in GUIDES_META, (slug, cause["guide"])


def test_frontend_issue_to_guide_map_points_at_real_guides():
    html = (ROOT / "static" / "index.html").read_text()
    block = re.search(r"const GUIDES = \{(.*?)\};", html, re.DOTALL).group(1)
    slugs = re.findall(r":\s*'([a-z0-9-]+)'", block)
    assert slugs and set(slugs) <= set(GUIDES_META)


def test_readme_states_the_real_check_count():
    readme = (ROOT / "README.md").read_text()
    assert f"{CHECK_COUNT} checks" in readme
    stale = {int(n) for n in re.findall(r"\b(\d+) checks\b", readme)} - {CHECK_COUNT}
    assert not stale, f"README mentions stale check counts: {stale}"
