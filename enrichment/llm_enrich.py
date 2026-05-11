"""Enrichment agent: fill missing fields on existing datacenter rows.

Walks the datacenters table, finds rows with missing critical fields
(capacity_mw, construction_start_date, expected_completion_date, address),
and asks Claude to fill them in using the row's source URLs as context.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from pipeline.schema import connect
from enrichment.agents import call_claude_with_schema

CRITICAL_FIELDS = (
    "capacity_mw",
    "construction_start_date",
    "expected_completion_date",
    "actual_completion_date",
    "address",
    "capacity_use",
)

SCHEMA = """
{
  "capacity_mw": float | null,
  "construction_start_date": "YYYY-MM-DD" | null,
  "expected_completion_date": "YYYY-MM-DD" | null,
  "actual_completion_date": "YYYY-MM-DD" | null,
  "address": "string" | null,
  "capacity_use": "string — what the capacity serves" | null,
  "primary_image_url": "string — direct URL to a public photo" | null,
  "notes": "string — any caveats or conflicting source info"
}
"""


def rows_needing_enrichment(limit: int = 30) -> list[dict]:
    conn = connect()
    try:
        missing_clause = " OR ".join(f"{f} IS NULL" for f in CRITICAL_FIELDS)
        rows = conn.execute(
            f"SELECT * FROM datacenters WHERE {missing_clause} "
            "ORDER BY last_updated ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def enrich_one(row: dict) -> int:
    sources = []
    try:
        sources = json.loads(row.get("source_urls") or "[]")
    except json.JSONDecodeError:
        pass
    if not sources:
        return 0

    user = (
        f"Data center: {row['name']}\n"
        f"Operator: {row['operator']}\n"
        f"Location: {row.get('region') or ''}, {row.get('country') or ''}\n"
        f"Coordinates: {row['latitude']}, {row['longitude']}\n"
        f"Current known fields: {json.dumps({k: row.get(k) for k in CRITICAL_FIELDS})}\n\n"
        f"Source URLs:\n" + "\n".join(f"- {u}" for u in sources) + "\n\n"
        "Using the sources above, fill in any missing fields. Do not change "
        "fields that already have a value unless the sources clearly contradict them. "
        "Leave fields null if no source supports a value."
    )
    result = call_claude_with_schema(user, SCHEMA)

    # Only update fields that are currently null and the agent provided a value
    updates = {}
    for f in CRITICAL_FIELDS + ("primary_image_url",):
        if row.get(f) is None and result.get(f) is not None:
            updates[f] = result[f]
    if not updates:
        return 0

    updates["last_updated"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [row["id"]]
    conn = connect()
    try:
        conn.execute(f"UPDATE datacenters SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()
    return len(updates) - 1  # don't count last_updated


def run(limit: int = 30) -> int:
    rows = rows_needing_enrichment(limit)
    print(f"Enrichment: {len(rows)} rows needing enrichment")
    total_fields = 0
    for row in rows:
        try:
            n = enrich_one(row)
            total_fields += n
            if n:
                print(f"  ~ {row['id']}: filled {n} fields")
        except Exception as e:
            print(f"  ! failed {row['id']}: {e}")
    return total_fields


if __name__ == "__main__":
    n = run()
    print(f"Enrichment agent: filled {n} fields")
