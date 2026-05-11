"""Check every source URL in the database and report which are unreachable.

Usage:
    python -m pipeline.verify_sources          # report only
    python -m pipeline.verify_sources --fix    # set confidence=low on dead sources
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from pipeline.schema import connect

TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 (datacenter-map source verifier)"}


def check_url(url: str) -> tuple[str, int, str]:
    try:
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return url, r.status, ""
    except urllib.error.HTTPError as e:
        return url, e.code, str(e.reason)
    except Exception as e:
        return url, 0, str(e)[:80]


def run(fix: bool = False) -> None:
    conn = connect()
    rows = conn.execute("SELECT id, name, source_urls, confidence FROM datacenters").fetchall()

    url_to_ids: dict[str, list[str]] = {}
    for row in rows:
        urls = []
        try:
            urls = json.loads(row["source_urls"] or "[]")
        except Exception:
            pass
        for u in urls:
            url_to_ids.setdefault(u, []).append(row["id"])

    all_urls = list(url_to_ids)
    if not all_urls:
        print("No source URLs in database.")
        return

    print(f"Checking {len(all_urls)} unique source URLs…\n")
    dead: list[tuple[str, int, str]] = []
    ok: int = 0

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(check_url, u): u for u in all_urls}
        for f in as_completed(futures):
            url, status, reason = f.result()
            if status and 200 <= status < 400:
                ok += 1
            else:
                dead.append((url, status, reason))
                ids = ", ".join(url_to_ids[url])
                print(f"  DEAD [{status}]  {url}")
                print(f"         -> affects: {ids}")
                if reason:
                    print(f"         -> reason:   {reason}")

    print(f"\n{ok} OK  |  {len(dead)} dead")

    if fix and dead:
        dead_urls = {u for u, _, _ in dead}
        for row in rows:
            urls = []
            try:
                urls = json.loads(row["source_urls"] or "[]")
            except Exception:
                pass
            if any(u in dead_urls for u in urls):
                conn.execute(
                    "UPDATE datacenters SET confidence='low' WHERE id=?", (row["id"],)
                )
                print(f"  -> set confidence=low for {row['id']}")
        conn.commit()
        print("Done.")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Downgrade confidence on dead sources")
    args = parser.parse_args()
    run(fix=args.fix)
