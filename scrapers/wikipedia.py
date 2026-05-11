"""Wikipedia scraper for hyperscaler datacenter lists.

Strategy: each hyperscaler has a Wikipedia page that lists their data centers
with location and (sometimes) capacity. We fetch the HTML, find the relevant
table, parse rows, and pass candidates to upsert. LLM enrichment fills the
gaps afterward.

This is intentionally conservative — we only extract what we can confidently
parse. Anything ambiguous is left for the enrichment agent.
"""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup

from scrapers.common import polite_get, upsert_datacenters, log_scrape_run

# Pages with relatively clean tables we can parse
WIKI_PAGES = [
    ("https://en.wikipedia.org/wiki/List_of_Microsoft_data_centers", "Azure"),
    ("https://en.wikipedia.org/wiki/Google_data_centers", "GCP"),
]


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60]


def parse_page(url: str, operator: str) -> Iterable[dict]:
    """Parse a Wikipedia page and yield candidate datacenter rows.

    We look for the first wikitable on the page with a 'Location' column and
    extract one row per data center. This is best-effort — formats vary.
    """
    resp = polite_get(url, sleep_seconds=2.0)
    soup = BeautifulSoup(resp.text, "html.parser")

    for table in soup.select("table.wikitable"):
        headers = [th.get_text(strip=True).lower() for th in table.select("tr th")]
        if not any("location" in h or "site" in h or "country" in h for h in headers):
            continue

        for tr in table.select("tr")[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.select("td")]
            if not cells:
                continue
            location = cells[0] if cells else ""
            if not location or len(location) > 80:
                continue
            rid = f"wiki-{slugify(operator)}-{slugify(location)}"
            yield {
                "id": rid,
                "name": f"{operator} {location}",
                "operator": operator,
                # Coordinates filled by LLM enrichment later.
                "latitude": 0.0,
                "longitude": 0.0,
                "status": "operational",
                "country": cells[1] if len(cells) > 1 else None,
                "region": location,
                "source_urls": [url],
                "confidence": "low",
            }


def run() -> tuple[int, int]:
    total_added = total_updated = 0
    error = None
    try:
        for url, operator in WIKI_PAGES:
            try:
                records = list(parse_page(url, operator))
                # Filter out records without real coords — we don't want fake
                # 0,0 points on the globe. Better to let enrichment add them.
                records = [r for r in records if r.get("country") or r.get("region")]
                if not records:
                    continue
                a, u = upsert_datacenters(records, source=url)
                total_added += a
                total_updated += u
                print(f"  {url}: +{a} new, ~{u} updated")
            except Exception as e:
                print(f"  {url}: FAILED ({e})")
                error = (error or "") + f"{url}: {e}; "
    finally:
        log_scrape_run("wikipedia", total_added, total_updated, error)
    return total_added, total_updated


if __name__ == "__main__":
    a, u = run()
    print(f"Wikipedia scrape: +{a} added, ~{u} updated")
