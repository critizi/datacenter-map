"""SQLite schema for the datacenter map.

Single source of truth. Imported by every scraper, enrichment agent, and the
build orchestrator. Re-running init_db() is idempotent.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "datacenters.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS datacenters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    operator TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('operational','under_construction','planned','retired')),
    construction_start_date TEXT,
    expected_completion_date TEXT,
    actual_completion_date TEXT,
    build_duration_months REAL,
    capacity_mw REAL,
    capacity_use TEXT,
    address TEXT,
    country TEXT,
    region TEXT,
    primary_image_url TEXT,
    primary_image_local_path TEXT,
    source_urls TEXT,
    confidence TEXT CHECK (confidence IN ('low','medium','high')),
    last_updated TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dc_operator ON datacenters(operator);
CREATE INDEX IF NOT EXISTS idx_dc_status ON datacenters(status);
CREATE INDEX IF NOT EXISTS idx_dc_country ON datacenters(country);

CREATE TABLE IF NOT EXISTS datacenter_tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datacenter_id TEXT NOT NULL REFERENCES datacenters(id),
    tenant_name TEXT NOT NULL,
    parent_company TEXT,
    ticker TEXT,
    workload TEXT,
    share_pct REAL,
    dollars_committed TEXT,
    evidence_quote TEXT NOT NULL,
    confidence TEXT CHECK (confidence IN ('low','medium','high')),
    source_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_tenants_dc ON datacenter_tenants(datacenter_id);
CREATE INDEX IF NOT EXISTS idx_tenants_name ON datacenter_tenants(tenant_name);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    records_added INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    error TEXT
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized {DB_PATH}")
