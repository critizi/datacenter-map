"""Shared utilities for scrapers."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Iterable

import requests

from pipeline.schema import connect

USER_AGENT = "DatacenterMapBot/0.1 (+https://github.com/Critizi/datacenter-map)"
TIMEOUT = 20

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def polite_get(url: str, sleep_seconds: float = 1.0) -> requests.Response:
    """GET with a UA, timeout, and a sleep to be a good citizen."""
    resp = session.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    time.sleep(sleep_seconds)
    return resp


def upsert_datacenters(records: Iterable[dict], source: str) -> tuple[int, int]:
    """Upsert datacenter records. Returns (added, updated)."""
    conn = connect()
    added = updated = 0
    try:
        for rec in records:
            existing = conn.execute(
                "SELECT id FROM datacenters WHERE id = ?", (rec["id"],)
            ).fetchone()
            rec.setdefault("last_updated", datetime.now(timezone.utc).isoformat())
            if isinstance(rec.get("source_urls"), list):
                rec["source_urls"] = json.dumps(rec["source_urls"])
            cols = list(rec.keys())
            placeholders = ",".join(f":{c}" for c in cols)
            col_list = ",".join(cols)
            update_clause = ",".join(f"{c}=excluded.{c}" for c in cols if c != "id")
            sql = (
                f"INSERT INTO datacenters ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT(id) DO UPDATE SET {update_clause}"
            )
            conn.execute(sql, rec)
            if existing:
                updated += 1
            else:
                added += 1
        conn.commit()
    finally:
        conn.close()
    return added, updated


def log_scrape_run(source: str, added: int, updated: int, error: str | None = None) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO scrape_runs (source, started_at, finished_at, records_added, records_updated, error) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (source, datetime.now(timezone.utc).isoformat(),
             datetime.now(timezone.utc).isoformat(), added, updated, error),
        )
        conn.commit()
    finally:
        conn.close()
