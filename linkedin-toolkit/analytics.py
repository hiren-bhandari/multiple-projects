"""Pull LinkedIn Ads and Company Page analytics into a local SQLite DB + CSV.

  python3 analytics.py ads   --days 30     # daily metrics per campaign
  python3 analytics.py page                # follower + share statistics per Page

Needs the analytics token (python3 auth.py analytics) and your app approved for
the Advertising API / Community Management API. IDs come from .env.
"""
import argparse
import csv
import datetime as dt
import json
import sqlite3
import urllib.parse

from common import HERE, API, cfg, load_token, request, rest_headers

DB = HERE / "linkedin.db"
OUT = HERE / "out"
AD_FIELDS = ["dateRange", "pivotValues", "impressions", "clicks", "costInLocalCurrency",
             "landingPageClicks", "externalWebsiteConversions", "likes", "comments",
             "shares", "follows"]


def ids(name):
    return [x.strip() for x in cfg(name, "").split(",") if x.strip()]


def urn_q(urn):
    return urllib.parse.quote(urn, safe="")


def ads(days):
    token = load_token("analytics")
    accounts = ids("LINKEDIN_AD_ACCOUNT_IDS")
    if not accounts:
        raise SystemExit("Set LINKEDIN_AD_ACCOUNT_IDS in .env")
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    acc = ",".join(urn_q(f"urn:li:sponsoredAccount:{a}") for a in accounts)
    # Rest.li query syntax: structural ()/, must NOT be percent-encoded.
    url = (f"{API}/rest/adAnalytics?q=analytics&pivot=CAMPAIGN&timeGranularity=DAILY"
           f"&dateRange=(start:(year:{start.year},month:{start.month},day:{start.day}),"
           f"end:(year:{end.year},month:{end.month},day:{end.day}))"
           f"&accounts=List({acc})&fields={','.join(AD_FIELDS)}")
    _, _, data = request("GET", url, token, headers=rest_headers())
    rows = []
    for e in data.get("elements", []):
        s = e["dateRange"]["start"]
        rows.append({
            "date": f"{s['year']:04d}-{s['month']:02d}-{s['day']:02d}",
            "campaign": (e.get("pivotValues") or [""])[0],
            **{k: e.get(k, 0) for k in AD_FIELDS if k not in ("dateRange", "pivotValues")},
        })
    con = sqlite3.connect(DB)
    cols = list(rows[0]) if rows else []
    if rows:
        con.execute(f"CREATE TABLE IF NOT EXISTS ad_daily ({', '.join(c + ' ' for c in cols)}, "
                    "PRIMARY KEY(date, campaign))")
        for r in rows:
            con.execute(f"INSERT OR REPLACE INTO ad_daily VALUES ({','.join('?'*len(cols))})",
                        list(r.values()))
        con.commit()
        OUT.mkdir(exist_ok=True)
        with open(OUT / "ad_daily.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    print(f"Ads: {len(rows)} rows -> {DB.name}, out/ad_daily.csv")


def page():
    token = load_token("analytics")
    orgs = ids("LINKEDIN_ORG_IDS")
    if not orgs:
        raise SystemExit("Set LINKEDIN_ORG_IDS in .env")
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS page_raw "
                "(fetched_at, org, endpoint, payload)")
    now = dt.datetime.now().isoformat(timespec="seconds")
    for o in orgs:
        urn = urn_q(f"urn:li:organization:{o}")
        for name, ep in {
            "followers": f"organizationalEntityFollowerStatistics?q=organizationalEntity&organizationalEntity={urn}",
            "shares": f"organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity={urn}",
            "page": f"organizationPageStatistics?q=organization&organization={urn}",
        }.items():
            _, _, data = request("GET", f"{API}/rest/{ep}", token, headers=rest_headers())
            con.execute("INSERT INTO page_raw VALUES (?,?,?,?)", (now, o, name, json.dumps(data)))
            print(f"Page {o} {name}: {len(data.get('elements', []))} elements")
    con.commit()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["ads", "page"])
    ap.add_argument("--days", type=int, default=30)
    a = ap.parse_args()
    ads(a.days) if a.what == "ads" else page()
