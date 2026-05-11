# Datacenter Map

Interactive 3D globe showing the world's hyperscaler data centers — capacity, status, build timelines, and where the capacity flows.

**Live site:** _(will be `https://<username>.github.io/datacenter-map/` once GitHub Pages is enabled)_

## What it is

A self-contained static website that:

- Renders ~30+ hyperscaler datacenters (AWS, Azure, GCP, Meta, Oracle, Apple, ByteDance) as colored points on a 3D Earth.
- Clicking a point opens a side panel with: capacity (MW), build timeline, what the capacity serves, source citations, and a photo when one is available.
- Refreshes weekly via GitHub Actions — scrapes operator press releases, runs LLM agents to extract structured data, regenerates the site, redeploys.

## Architecture

```
data/datacenters.db   <- SQLite source of truth
   ↑
   ├─ pipeline/seed.py            (curated hyperscaler anchors)
   ├─ scrapers/wikipedia.py       (best-effort table parsing)
   ├─ scrapers/operator_press.py  (RSS → staging table)
   ├─ enrichment/llm_discovery.py (press articles → DC rows, via Claude API)
   └─ enrichment/llm_enrich.py    (fill missing fields, via Claude API)
   ↓
pipeline/build.py    -> dist/index.html  (single self-contained HTML)
   ↓
GitHub Pages (deployed by .github/workflows/deploy.yml)
```

## Local development

```bash
pip install -r requirements.txt

# Just build with the seed data (no API key needed)
python -m pipeline.build

# Full weekly refresh (scrape + LLM + build) — needs ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=sk-ant-...
python -m pipeline.refresh

# Open the result
open dist/index.html   # macOS
start dist\index.html  # Windows
xdg-open dist/index.html  # Linux
```

## Deploying to GitHub Pages

1. Push this repo to GitHub.
2. In **Settings → Pages**, set Source to "GitHub Actions".
3. In **Settings → Secrets and variables → Actions**, add `ANTHROPIC_API_KEY` (optional — the pipeline runs without it, just without LLM enrichment).
4. Run the **Build and deploy** workflow manually once to seed the site, then it'll refresh every Monday at 06:00 UTC.

Your site will live at `https://<your-github-username>.github.io/datacenter-map/`.

## Agents

This project uses two distinct types of agents — see `plans/i-am-wanting-to-atomic-muffin.md` for the full breakdown:

- **Build-time agents** (Claude Code subagents that constructed the project): data-pipeline, llm-enrichment, frontend, devops.
- **Runtime agents** (Python scripts using the Claude API, triggered weekly):
  - `llm_discovery.py` — turns press releases into structured DC rows
  - `llm_enrich.py` — fills missing fields (capacity, dates, images)
  - _(planned)_ status-update — promotes `under_construction` → `operational`
  - _(planned)_ image-finder — locates and caches public photos
  - _(planned)_ verification — flags conflicting source claims

## Costs

- **GitHub Pages, Actions, hosting:** free.
- **Claude API:** ~$5–15 per weekly run with prompt caching. Adjustable via `DISCOVERY_LIMIT` and `ENRICH_LIMIT` env vars in the workflow.

## Roadmap

- [ ] Image-finder agent (Wikipedia Commons + operator press kits)
- [ ] Status-update agent (auto-promote completed builds)
- [ ] Verification agent (flag conflicting source claims)
- [ ] Arcs showing operator HQ → DC connections
- [ ] Time-slider to scrub through years of buildout
- [ ] Long-tail colocation operators beyond hyperscalers
