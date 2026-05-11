"""Operator press release ingester.

Hyperscalers announce new data center builds on news/RSS feeds long before
those facilities appear on Wikipedia or commercial trackers. This scraper
fetches the feeds, filters items that mention 'data center'/'datacenter', and
stores raw article URLs in a staging table for the LLM discovery agent to
process.

We don't try to extract structured data here — that's the LLM's job. We just
collect candidate URLs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import feedparser

from pipeline.schema import connect

# Public RSS / news feeds. These change — keep this list updated.
FEEDS = [
    ("AWS", "https://aws.amazon.com/about-aws/whats-new/recent/feed/"),
    ("Azure", "https://azure.microsoft.com/en-us/blog/feed/"),
    ("GCP", "https://cloudblog.withgoogle.com/rss/"),
    ("Meta", "https://about.fb.com/news/feed/"),
]

KEYWORDS = ("data center", "datacenter", "data-center", "hyperscale", "gigawatt", "megawatt")


@dataclass
class PressItem:
    operator: str
    title: str
    url: str
    published: str | None
    summary: str


def _matches(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in KEYWORDS)


def fetch_feed(operator: str, url: str) -> Iterable[PressItem]:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        if not (_matches(title) or _matches(summary)):
            continue
        yield PressItem(
            operator=operator,
            title=title,
            url=entry.get("link", ""),
            published=entry.get("published") or entry.get("updated"),
            summary=summary[:1000],
        )


def ensure_staging_table() -> None:
    conn = connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS press_candidates (
                url TEXT PRIMARY KEY,
                operator TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                published TEXT,
                discovered_at TEXT NOT NULL,
                processed INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
    finally:
        conn.close()


def store_items(items: Iterable[PressItem]) -> int:
    ensure_staging_table()
    conn = connect()
    n = 0
    try:
        for it in items:
            if not it.url:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO press_candidates "
                "(url, operator, title, summary, published, discovered_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (it.url, it.operator, it.title, it.summary, it.published,
                 datetime.now(timezone.utc).isoformat()),
            )
            n += conn.total_changes
        conn.commit()
    finally:
        conn.close()
    return n


def run() -> int:
    total = 0
    for operator, url in FEEDS:
        try:
            items = list(fetch_feed(operator, url))
            stored = store_items(items)
            total += stored
            print(f"  {operator}: {len(items)} matched, {stored} new")
        except Exception as e:
            print(f"  {operator}: FAILED ({e})")
    return total


if __name__ == "__main__":
    n = run()
    print(f"Press scrape: {n} new candidate articles staged for LLM discovery")
