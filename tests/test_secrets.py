import base64
import json

import pytest

from didyouship.secrets import find_secrets, jwt_role


def make_jwt(payload: dict) -> str:
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64(payload)}.c2lnbmF0dXJlc2lnbmF0dXJl"


SERVICE_ROLE = make_jwt({"iss": "supabase", "ref": "abcdefghijklmnop", "role": "service_role"})
ANON = make_jwt({"iss": "supabase", "ref": "abcdefghijklmnop", "role": "anon"})


@pytest.mark.parametrize("text,label", [
    ('const k="sk_live_' + "a" * 24 + '"', "Stripe secret key"),
    ('rk_live_' + "b" * 24, "Stripe restricted key"),
    ("AKIA" + "ABCDEFGHIJKLMNOP", "AWS access key"),
    ("sk-ant-api03-" + "x" * 30, "Anthropic API key"),
    ("sk-proj-" + "Ab_-" * 12, "OpenAI API key"),
    ("ghp_" + "a" * 36, "GitHub personal access token"),
    ("SG." + "a" * 22 + "." + "b" * 43, "SendGrid API key"),
    ("xoxb-" + "1" * 24, "Slack token"),
    ("sb_secret_" + "z" * 30, "Supabase secret key"),
    ('"' + SERVICE_ROLE + '"', "Supabase service_role key"),
    ("postgres://app:S3cr3tPw@db.prod.internal/app", "Database connection string"),
    ("redis://default:hunter2xyz@cache.example.net:6379", "Redis connection string"),
    ('"-----BEGIN RSA PRIVATE KEY-----\\nMIIEow' + "A" * 80 + '"', "Private key"),
])
def test_detects_real_secrets(text, label):
    assert label in find_secrets(text)


@pytest.mark.parametrize("text", [
    "pk_live_" + "a" * 24,                                   # Stripe publishable
    "AIzaSyA" + "b" * 32,                                    # Firebase web key
    '"' + ANON + '"',                                        # Supabase anon key
    "postgres://user:password@localhost:5432/db",            # docs placeholder
    "postgresql://postgres:postgres@db:5432/postgres",       # docker-compose default
    "mongodb+srv://<user>:<password>@cluster0.mongodb.net",  # template
    "mysql://root:${DB_PASS}@prod.example.org/app",          # interpolation
    'e.PEM_HEADER="-----BEGIN RSA PRIVATE KEY-----";',       # header constant in a crypto lib
    "the word sk- followed by short text",
])
def test_ignores_publishable_keys_and_placeholders(text):
    assert find_secrets(text) == []


def test_jwt_role():
    assert jwt_role(SERVICE_ROLE) == "service_role"
    assert jwt_role(ANON) == "anon"
    assert jwt_role("not.a.jwt") is None
    assert jwt_role("garbage") is None


def test_labels_are_deduplicated_and_never_contain_the_secret():
    secret = "sk_live_" + "q" * 30
    found = find_secrets(f"{secret} {secret}")
    assert found == ["Stripe secret key"]
    assert all(secret not in label for label in found)
