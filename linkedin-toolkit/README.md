# linkedin-toolkit

Two small stdlib-only Python tools using LinkedIn's **official** APIs:

- `post.py` – publish human-approved posts to your personal profile (Share on LinkedIn / Posts API).
- `analytics.py` – pull Ads and Company Page analytics into SQLite + CSV.

No scraping, no browser automation. Messages, connection requests and profile editing are not available via public API and are out of scope.

## Setup (once)
1. Create an app at https://developer.linkedin.com/ (needs a LinkedIn Page to associate).
2. Products: **Share on LinkedIn** and **Sign In with LinkedIn using OpenID Connect** (self-serve) for posting.
   For analytics also request **Advertising API** and/or **Community Management API** (approval required).
3. In the app's Auth tab add redirect URL `http://localhost:8080/callback`.
4. `cp .env.example .env` and fill in client id/secret, ad account IDs, org IDs.
5. On your own computer: `python3 auth.py post` and `python3 auth.py analytics`.
   Tokens last ~60 days; re-run to renew.

## Posting
Edit `posts/queue.json`, set `"approved": true`, then:
```
python3 post.py             # dry run
python3 post.py --publish   # publish approved + due posts
```
Run `--publish` from cron (e.g. daily 09:00) to post on schedule.

## Analytics
```
python3 analytics.py ads --days 30
python3 analytics.py page
```
Notes: API field names and the `LINKEDIN_VERSION` header change over time; this code
has not been run against live LinkedIn, so expect to adjust on first run.
