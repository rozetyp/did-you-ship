"""
AI-powered per-issue explanations using xAI Grok.
NOT a full report — short, specific explanations per issue.
"""

import os
import json
from openai import OpenAI

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")


def explain_issues(scan_result) -> dict[str, str]:
    """Generate a short plain-English explanation for each issue.
    Returns a dict: issue_title → explanation (2-3 sentences max)."""
    if not XAI_API_KEY:
        return {}

    if not scan_result.issues:
        return {}

    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

    issues_json = json.dumps([
        {"title": i.title, "detail": i.detail, "severity": i.severity, "category": i.category}
        for i in scan_result.issues
    ])

    prompt = f"""Domain: {scan_result.domain}

Here are the issues found in a website production readiness scan. For each issue, write a short explanation (2-3 sentences MAX) that:
1. Tells a non-technical person what could go wrong in plain English
2. Gives the ONE specific action to fix it

Return a JSON object where keys are the issue titles and values are the explanations. Keep each explanation under 50 words. Be direct — no filler, no "it's important to note", no corporate language.

Issues:
{issues_json}"""

    try:
        response = client.chat.completions.create(
            model="grok-3-mini-fast",
            messages=[
                {"role": "system", "content": "You explain website security issues to non-technical founders in 2-3 sentences each. Be direct, specific, and actionable. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"_error": str(e)}


def generate_summary(scan_result) -> str | None:
    """One-liner summary of the overall state."""
    if not XAI_API_KEY:
        return None

    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

    critical = sum(1 for i in scan_result.issues if i.severity == "critical")
    high = sum(1 for i in scan_result.issues if i.severity == "high")

    prompt = f"""Domain {scan_result.domain} scored {scan_result.score}/100 (grade {scan_result.grade}).
{len(scan_result.issues)} issues found ({critical} critical, {high} high).
{len(scan_result.passed)} checks passing.

Write ONE sentence (max 20 words) summarizing the state. Be direct. Examples:
- "Your emails are going to spam because you're missing two DNS records."
- "Looking solid — just add security headers and you're production-ready."
- "Critical issues: anyone can spoof your email and your SSL expires in 3 days."
"""

    try:
        response = client.chat.completions.create(
            model="grok-3-mini-fast",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip().strip('"')
    except Exception:
        return None
