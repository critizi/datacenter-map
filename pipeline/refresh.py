"""Weekly refresh pipeline — chains all stages.

Run order:
1. Seed (idempotent — ensures core hyperscaler rows always present)
2. Scrape Wikipedia (cheap, no API key)
3. Scrape operator press feeds (cheap, no API key)
4. LLM discovery — turn press articles into structured DC rows
5. LLM enrichment — fill missing fields on existing rows
6. Build dist/

Steps 4 and 5 are skipped if ANTHROPIC_API_KEY is not set, so the pipeline
still produces a valid site without API access.
"""
from __future__ import annotations

import os
import traceback

from pipeline import build, seed
from scrapers import wikipedia, operator_press


def run() -> None:
    print("== Step 1: seed ==")
    seed.seed_database()

    print("\n== Step 2: Wikipedia ==")
    try:
        wikipedia.run()
    except Exception:
        traceback.print_exc()

    print("\n== Step 3: operator press feeds ==")
    try:
        operator_press.run()
    except Exception:
        traceback.print_exc()

    if os.environ.get("ANTHROPIC_API_KEY"):
        from enrichment import llm_discovery, llm_enrich
        print("\n== Step 4: LLM discovery ==")
        try:
            llm_discovery.run(limit=int(os.environ.get("DISCOVERY_LIMIT", "20")))
        except Exception:
            traceback.print_exc()

        print("\n== Step 5: LLM enrichment ==")
        try:
            llm_enrich.run(limit=int(os.environ.get("ENRICH_LIMIT", "20")))
        except Exception:
            traceback.print_exc()
    else:
        print("\n== Steps 4-5: LLM agents SKIPPED (ANTHROPIC_API_KEY not set) ==")

    print("\n== Step 6: NASA GIBS satellite imagery ==")
    try:
        from pipeline.fetch_images import run as fetch_images
        fetch_images()
    except Exception:
        traceback.print_exc()

    print("\n== Step 7: build dist/ ==")
    n = build.build()
    print(f"\nDone — {n} datacenters in dist/index.html")


if __name__ == "__main__":
    run()
