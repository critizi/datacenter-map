"""Tenant enrichment agent.

Extracts named tenant/workload relationships for each datacenter using the
row's capacity_use as context and fetched source URL bodies as evidence.
Rows are inserted only when the evidence quote can be found in fetched source
text, which keeps the tenant table source-cited by construction.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from enrichment.agents import TENANTS_SCHEMA, call_claude_with_schema
from pipeline.schema import connect, init_db

MAX_SOURCE_CHARS = 12000
FETCH_TIMEOUT_SECONDS = 18
VALID_CONFIDENCE = {"low", "medium", "high"}


def rows_needing_tenants(limit: int = 30) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT d.* FROM datacenters d "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM datacenter_tenants t WHERE t.datacenter_id = d.id"
            ") "
            "AND (d.capacity_use IS NOT NULL OR d.source_urls IS NOT NULL) "
            "ORDER BY d.last_updated ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _source_urls(row: dict[str, Any]) -> list[str]:
    try:
        urls = json.loads(row.get("source_urls") or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(urls, list):
        return []
    return [u for u in urls if isinstance(u, str) and u.startswith(("http://", "https://"))]


def _clean_text(html_or_text: str, content_type: str) -> str:
    if "html" in content_type.lower():
        soup = BeautifulSoup(html_or_text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = soup.get_text(" ")
    else:
        text = html_or_text
    return re.sub(r"\s+", " ", text).strip()


def fetch_source(url: str) -> dict[str, str]:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "datacenter-map tenant enrichment/1.0"},
            timeout=FETCH_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        text = _clean_text(resp.text, resp.headers.get("content-type", ""))
        return {"url": url, "text": text[:MAX_SOURCE_CHARS], "error": ""}
    except Exception as exc:
        return {"url": url, "text": "", "error": str(exc)}


def fetch_sources(urls: list[str]) -> list[dict[str, str]]:
    return [fetch_source(url) for url in urls]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _quote_source_url(quote: str, sources: list[dict[str, str]], preferred: str | None) -> str | None:
    q = _norm(quote)
    if not q:
        return None

    ordered = sources
    if preferred:
        ordered = sorted(sources, key=lambda s: 0 if s["url"] == preferred else 1)

    for source in ordered:
        if q and q in _norm(source.get("text", "")):
            return source["url"]
    return None


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _valid_tenant(raw: dict[str, Any], sources: list[dict[str, str]]) -> dict[str, Any] | None:
    tenant_name = _norm(str(raw.get("tenant_name") or ""))
    quote = _norm(str(raw.get("evidence_quote") or ""))
    source_url = _quote_source_url(quote, sources, raw.get("source_url"))
    if not tenant_name or not quote or not source_url:
        return None

    confidence = raw.get("confidence")
    if confidence not in VALID_CONFIDENCE:
        confidence = "low"

    return {
        "tenant_name": tenant_name,
        "parent_company": raw.get("parent_company"),
        "ticker": raw.get("ticker"),
        "workload": raw.get("workload"),
        "share_pct": _float_or_none(raw.get("share_pct")),
        "dollars_committed": raw.get("dollars_committed"),
        "evidence_quote": quote,
        "confidence": confidence,
        "source_url": source_url,
    }


def _tenant_list(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return [t for t in result if isinstance(t, dict)]
    if isinstance(result, dict):
        tenants = result.get("tenants", [])
        if isinstance(tenants, list):
            return [t for t in tenants if isinstance(t, dict)]
    return []


def enrich_one(row: dict[str, Any]) -> int:
    urls = _source_urls(row)
    if not urls:
        return 0

    sources = fetch_sources(urls)
    source_blocks = []
    for source in sources:
        if source["text"]:
            source_blocks.append(
                f"SOURCE URL: {source['url']}\nSOURCE TEXT:\n{source['text']}"
            )
        else:
            source_blocks.append(
                f"SOURCE URL: {source['url']}\nSOURCE FETCH ERROR: {source['error']}"
            )

    user = (
        f"Data center id: {row['id']}\n"
        f"Name: {row['name']}\n"
        f"Operator: {row['operator']}\n"
        f"Location: {row.get('region') or ''}, {row.get('country') or ''}\n"
        f"Capacity use context, not proof unless repeated in source text:\n"
        f"{row.get('capacity_use') or ''}\n\n"
        "Fetched source material:\n\n"
        + "\n\n---\n\n".join(source_blocks)
        + "\n\nExtract named tenants and workloads. The evidence_quote must be copied "
        "verbatim from SOURCE TEXT above; do not quote the capacity_use context unless "
        "the same sentence appears in SOURCE TEXT. Drop any tenant without such a quote."
    )
    result = call_claude_with_schema(user, TENANTS_SCHEMA, max_tokens=2500)
    tenants = [
        t for t in (_valid_tenant(raw, sources) for raw in _tenant_list(result))
        if t is not None
    ]

    conn = connect()
    try:
        conn.execute("DELETE FROM datacenter_tenants WHERE datacenter_id = ?", (row["id"],))
        if tenants:
            conn.executemany(
                "INSERT INTO datacenter_tenants ("
                "datacenter_id, tenant_name, parent_company, ticker, workload, "
                "share_pct, dollars_committed, evidence_quote, confidence, source_url"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["id"],
                        t["tenant_name"],
                        t["parent_company"],
                        t["ticker"],
                        t["workload"],
                        t["share_pct"],
                        t["dollars_committed"],
                        t["evidence_quote"],
                        t["confidence"],
                        t["source_url"],
                    )
                    for t in tenants
                ],
            )
            conn.execute(
                "UPDATE datacenters SET last_updated = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), row["id"]),
            )
        conn.commit()
    finally:
        conn.close()
    return len(tenants)


def run(limit: int = 30) -> int:
    init_db()
    rows = rows_needing_tenants(limit)
    print(f"Tenant enrichment: {len(rows)} rows needing tenant extraction")
    total = 0
    for row in rows:
        try:
            n = enrich_one(row)
            total += n
            print(f"  {'+' if n else '-'} {row['id']}: {n} tenants")
        except Exception as exc:
            print(f"  ! failed {row['id']}: {exc}")
    return total


if __name__ == "__main__":
    n = run()
    print(f"Tenant enrichment agent: inserted {n} tenant rows")
