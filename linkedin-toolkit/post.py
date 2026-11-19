"""Publish approved posts from posts/queue.json to your personal LinkedIn profile.

  python3 post.py              # dry run: shows what WOULD be published
  python3 post.py --publish    # actually publish approved posts that are due

A post is published only if "approved": true, it is not already published, and
"scheduled_for" (ISO local time, optional) is in the past. Run from cron/a
scheduler for recurring posting.
"""
import datetime as dt
import json
import sys

from common import HERE, API, load_token, request, rest_headers

QUEUE = HERE / "posts" / "queue.json"
# Characters LinkedIn treats as markup in "commentary". '#' is left alone so hashtags work.
RESERVED = "\\|{}@[]()<>*_~"


def escape(text):
    return "".join("\\" + c if c in RESERVED else c for c in text)


def due(p, now):
    if not p.get("approved") or p.get("status") == "published":
        return False
    when = p.get("scheduled_for")
    return not when or dt.datetime.fromisoformat(when) <= now


def main():
    publish = "--publish" in sys.argv
    posts = json.loads(QUEUE.read_text())
    now = dt.datetime.now()
    todo = [p for p in posts if due(p, now)]
    if not todo:
        print("Nothing due.")
        return
    token = load_token("post") if publish else None
    author = None
    for p in todo:
        print(f"--- {p['id']} ---\n{p['text']}\n")
        if not publish:
            continue
        if author is None:
            _, _, me = request("GET", f"{API}/v2/userinfo", token)
            author = f"urn:li:person:{me['sub']}"
        body = {
            "author": author,
            "commentary": escape(p["text"]),
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED",
                             "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        _, hdr, _ = request("POST", f"{API}/rest/posts", token, body, rest_headers())
        p["status"] = "published"
        p["published_urn"] = hdr.get("x-restli-id") or hdr.get("X-RestLi-Id")
        p["published_at"] = now.isoformat(timespec="seconds")
        QUEUE.write_text(json.dumps(posts, indent=2) + "\n")  # save after each post
        print("Published:", p["published_urn"])
    if not publish:
        print("Dry run only. Re-run with --publish to post.")


if __name__ == "__main__":
    main()
