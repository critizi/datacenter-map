"""Build orchestrator: SQLite -> dist/

Reads every row from the datacenters table, computes derived fields, then
renders frontend/template.html with the data embedded as JSON.

Usage:
    python -m pipeline.build
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pipeline.schema import connect, init_db
from pipeline.seed import seed_database

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
DIST = ROOT / "dist"
IMAGES_SRC = ROOT / "data" / "images"


def load_records() -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM datacenters").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def compute_derived(records: list[dict]) -> list[dict]:
    """Compute fields the frontend needs but we don't want to store."""
    for r in records:
        start = r.get("construction_start_date")
        end = r.get("actual_completion_date")
        if start and end and not r.get("build_duration_months"):
            try:
                d1 = datetime.fromisoformat(start)
                d2 = datetime.fromisoformat(end)
                r["build_duration_months"] = round((d2 - d1).days / 30.44, 1)
            except Exception:
                pass
    return records


def render(records: list[dict]) -> str:
    template = (FRONTEND / "template.html").read_text(encoding="utf-8")
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    js = (FRONTEND / "globe.js").read_text(encoding="utf-8")
    data_json = json.dumps(records, default=str, ensure_ascii=False)
    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return (template
            .replace("__INLINE_CSS__", css)
            .replace("__INLINE_JS__", js)
            .replace("__DC_DATA_JSON__", data_json)
            .replace("__BUILD_DATE__", build_date))


def write_dist(html: str, records: list[dict]) -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "index.html").write_text(html, encoding="utf-8")
    (DIST / "data.json").write_text(
        json.dumps(records, default=str, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Copy locally cached images, if any
    if IMAGES_SRC.exists():
        dest = DIST / "images"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(IMAGES_SRC, dest)


def build(seed_if_empty: bool = True) -> int:
    init_db()
    records = load_records()
    if not records and seed_if_empty:
        print("DB empty — seeding starter dataset…")
        seed_database()
        records = load_records()

    records = compute_derived(records)
    html = render(records)
    write_dist(html, records)
    return len(records)


if __name__ == "__main__":
    n = build()
    print(f"Built dist/index.html with {n} datacenters")
