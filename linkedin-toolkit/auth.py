"""One-time OAuth (authorization code flow). Run this on YOUR computer, since it
opens a browser and listens on localhost for the redirect.

  python3 auth.py post        # scopes: openid profile w_member_social
  python3 auth.py analytics   # scopes: r_ads r_ads_reporting r_organization_social
"""
import http.server
import json
import secrets
import sys
import time
import urllib.parse
import webbrowser

from common import cfg, request, token_path

SCOPES = {
    "post": "openid profile w_member_social",
    "analytics": "r_ads r_ads_reporting r_organization_social rw_organization_admin",
}


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    if kind not in SCOPES:
        raise SystemExit(__doc__)
    cid = cfg("LINKEDIN_CLIENT_ID", required=True)
    secret = cfg("LINKEDIN_CLIENT_SECRET", required=True)
    redirect = cfg("LINKEDIN_REDIRECT_URI", "http://localhost:8080/callback")
    state = secrets.token_urlsafe(16)
    url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(
        {"response_type": "code", "client_id": cid, "redirect_uri": redirect,
         "state": state, "scope": SCOPES[kind]})
    result = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Done. You can close this tab.")

        def log_message(self, *a):
            pass

    port = urllib.parse.urlparse(redirect).port or 8080
    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    print("Opening browser. If it doesn't open, visit:\n", url)
    webbrowser.open(url)
    srv.handle_request()
    if result.get("state") != state or "code" not in result:
        raise SystemExit(f"Authorization failed: {result}")
    _, _, tok = request("POST", "https://www.linkedin.com/oauth/v2/accessToken", form={
        "grant_type": "authorization_code", "code": result["code"],
        "redirect_uri": redirect, "client_id": cid, "client_secret": secret})
    tok["obtained_at"] = int(time.time())
    p = token_path(kind)
    p.write_text(json.dumps(tok))
    p.chmod(0o600)
    days = tok.get("expires_in", 0) // 86400
    print(f"Saved {p.name}. Token valid ~{days} days; re-run this command to renew.")


if __name__ == "__main__":
    main()
