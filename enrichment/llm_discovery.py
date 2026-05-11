"""Discovery agent.

Walks the press_candidates staging table populated by operator_press.py,
asks Claude to extract structured datacenter info per article, and inserts
new rows into the datacenters table.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from pipeline.schema import connect
from enrichment.agents import call_claude_with_schema
from scrapers.common import upsert_datacenters

SCHEMA = """
{
  "is_datacenter_announcement": bool,
  "datacenters": [
    {
      "name": "string — e.g. 'Meta Richland Parish' or 'AWS us-east-3'",
      "operator": "AWS|Azure|GCP|Meta|Oracle|Apple|ByteDance|Other",
      "approximate_latitude": float | null,
      "approximate_longitude": float | null,
      "status": "operational|under_construction|planned",
      "construction_start_date": "YYYY-MM-DD" | null,
      "expected_completion_date": "YYYY-MM-DD" | null,
      "actual_completion_date": "YYYY-MM-DD" | null,
      "capacity_mw": float | null,
      "capacity_use": "string — what the capacity serves",
      "country": "string",
      "region": "string — city/state",
      "confidence": "low|medium|high"
    }
  ]
}
"""


def fetch_unprocessed(limit: int = 50) -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT url, operator, title, summary, published "
            "FROM press_candidates WHERE processed = 0 ORDER BY discovered_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_processed(url: str) -> None:
    conn = connect()
    try:
        conn.execute("UPDATE press_candidates SET processed = 1 WHERE url = ?", (url,))
        conn.commit()
    finally:
        conn.close()


def slugify(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def process_one(item: dict) -> int:
    """Returns number of datacenter rows added/updated for this article."""
    user = (
        f"Operator: {item['operator']}\n"
        f"Article URL: {item['url']}\n"
        f"Title: {item['title']}\n"
        f"Published: {item.get('published') or 'unknown'}\n\n"
        f"Article summary:\n{item['summary']}\n\n"
        "Extract any data center facilities announced or mentioned in this article. "
        "If the article is not about a specific data center facility, set "
        "is_datacenter_announcement=false and return an empty datacenters array."
    )
    result = call_claude_with_schema(user, SCHEMA)
    if not result.get("is_datacenter_announcement"):
        return 0

    records = []
    for dc in result.get("datacenters", []):
        if dc.get("approximate_latitude") is None or dc.get("approximate_longitude") is None:
            continue  # skip if we can't place it on the globe
        rid = f"press-{slugify(dc['operator'])}-{slugify(dc.get('name', ''))}"
        records.append({
            "id": rid,
            "name": dc.get("name") or f"{dc['operator']} {dc.get('region', '')}",
            "operator": dc["operator"],
            "latitude": float(dc["approximate_latitude"]),
            "longitude": float(dc["approximate_longitude"]),
            "status": dc.get("status", "planned"),
            "construction_start_date": dc.get("construction_start_date"),
            "expected_completion_date": dc.get("expected_completion_date"),
            "actual_completion_date": dc.get("actual_completion_date"),
            "capacity_mw": dc.get("capacity_mw"),
            "capacity_use": dc.get("capacity_use"),
            "country": dc.get("country"),
            "region": dc.get("region"),
            "source_urls": json.dumps([item["url"]]),
            "confidence": dc.get("confidence", "low"),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        })
    if not records:
        return 0
    a, u = upsert_datacenters(records, source=item["url"])
    return a + u


def run(limit: int = 50) -> int:
    items = fetch_unprocessed(limit)
    print(f"Discovery: {len(items)} candidate articles to process")
    total = 0
    for it in items:
        try:
            n = process_one(it)
            total += n
            if n:
                print(f"  + {n} DCs from {it['url']}")
        except Exception as e:
            print(f"  ! failed {it['url']}: {e}")
        finally:
            mark_processed(it["url"])
    return total


if __name__ == "__main__":
    n = run()
    print(f"Discovery agent: {n} datacenter rows added/updated")
