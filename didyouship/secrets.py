"""Secret detection shared by the HTML and JS-bundle checks.

Only patterns that are secret by design are flagged. Publishable keys
(Stripe pk_live_, Firebase AIza..., the Supabase anon key) are meant to
ship to browsers and are never reported. Matched values are never returned,
only a label describing what was found.
"""

from __future__ import annotations

import base64
import json
import re

SECRET_PATTERNS = [
    (r"sk_live_[a-zA-Z0-9]{20,}", "Stripe secret key"),
    (r"sk_test_[a-zA-Z0-9]{20,}", "Stripe test secret key"),
    (r"rk_live_[a-zA-Z0-9]{20,}", "Stripe restricted key"),
    (r"AKIA[A-Z0-9]{16}", "AWS access key"),
    (r"sk-ant-[a-zA-Z0-9\-_]{20,}", "Anthropic API key"),
    (r"sk-proj-[a-zA-Z0-9\-_]{40,}", "OpenAI API key"),
    (r"sk-[a-zA-Z0-9]{40,}", "OpenAI API key"),
    (r"xai-[a-zA-Z0-9]{20,}", "xAI API key"),
    (r"ghp_[a-zA-Z0-9]{36,}", "GitHub personal access token"),
    (r"gho_[a-zA-Z0-9]{36,}", "GitHub OAuth token"),
    (r"github_pat_[a-zA-Z0-9_]{60,}", "GitHub personal access token"),
    (r"glpat-[a-zA-Z0-9\-_]{20,}", "GitLab personal access token"),
    (r"SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}", "SendGrid API key"),
    (r"xox[bp]-[0-9a-zA-Z\-]{20,}", "Slack token"),
    (r"sb_secret_[a-zA-Z0-9_\-]{20,}", "Supabase secret key"),
    # The header alone appears inside crypto libraries; require key material after it.
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:\\n|\\r|\s)*[A-Za-z0-9+/]{64}", "Private key"),
]

# scheme://user:password@host, the credentials being what makes it a secret.
_DB_URL = re.compile(
    r"\b(postgres(?:ql)?|mongodb(?:\+srv)?|mysql|redis|rediss)://"
    r"([^:/\s\"'<>@]+):([^@\s\"'<>/]+)@([^\s\"'<>/:]+)",
    re.IGNORECASE,
)
_PLACEHOLDER_PASSWORDS = {
    "password", "pass", "passwd", "pwd", "secret", "changeme", "user",
    "username", "xxx", "xxxx", "xxxxx", "example", "your_password",
    "yourpassword", "mypassword", "postgres", "root", "admin", "test",
}
_PLACEHOLDER_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "host", "hostname", "example.com", "db", "server"}

_DB_LABELS = {"redis": "Redis connection string", "rediss": "Redis connection string"}

_JWT = re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.(eyJ[A-Za-z0-9_\-]{10,})\.[A-Za-z0-9_\-]{10,}")


def jwt_role(token: str) -> str | None:
    """Return the `role` claim of a JWT (unverified), or None if unreadable."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (ValueError, json.JSONDecodeError):
        return None
    role = data.get("role") if isinstance(data, dict) else None
    return role if isinstance(role, str) else None


def _is_placeholder_db_url(user: str, password: str, host: str) -> bool:
    pw = password.lower()
    return (
        pw in _PLACEHOLDER_PASSWORDS
        or user.lower() == pw
        or host.lower() in _PLACEHOLDER_HOSTS
        or any(c in password for c in "${}<>*")
        or set(pw) <= {"x", "*", "."}
    )


def find_secrets(text: str) -> list[str]:
    """Return de-duplicated labels for every secret found in `text`."""
    found: list[str] = []
    for pattern, label in SECRET_PATTERNS:
        if label not in found and re.search(pattern, text):
            found.append(label)

    for m in _DB_URL.finditer(text):
        scheme, user, password, host = m.groups()
        if _is_placeholder_db_url(user, password, host):
            continue
        label = _DB_LABELS.get(scheme.lower(), "Database connection string")
        if label not in found:
            found.append(label)

    for m in _JWT.finditer(text):
        if jwt_role(m.group(0)) == "service_role":
            if "Supabase service_role key" not in found:
                found.append("Supabase service_role key")
            break

    return found
