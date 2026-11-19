"""Shared helpers: .env loading, token storage, tiny HTTP client (stdlib only)."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
API = "https://api.linkedin.com"


def load_env():
    env_file = HERE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()


def cfg(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and not v:
        raise SystemExit(f"Missing {name}. Set it in {HERE/'.env'}")
    return v


def token_path(kind):
    return HERE / f".token.{kind}.json"


def load_token(kind):
    p = token_path(kind)
    if not p.exists():
        raise SystemExit(f"No {kind} token. Run: python3 auth.py {kind}")
    return json.loads(p.read_text())["access_token"]


def request(method, url, token=None, body=None, headers=None, form=None):
    h = {"User-Agent": "linkedin-toolkit/0.1"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, dict(r.headers), (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} from {url}\n{e.read().decode(errors='replace')}")


def rest_headers():
    return {
        "LinkedIn-Version": cfg("LINKEDIN_VERSION", "202511"),
        "X-Restli-Protocol-Version": "2.0.0",
    }
