"""Shared LLM agent infrastructure.

All five runtime agents (discovery, enrichment, status-update, image,
verification) share the same pattern: build a prompt with source context,
call Claude with a structured-output schema, write the result back to
SQLite with provenance.

Uses Anthropic's prompt caching to amortize the large system prompt across
many per-DC calls in one run.
"""
from __future__ import annotations

import json
import os
from typing import Any

from anthropic import Anthropic

MODEL = "claude-opus-4-7"
CLIENT_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """You are a data analyst specializing in cloud infrastructure and data center facilities.

Your job is to extract structured information about data centers from public sources
(press releases, news articles, Wikipedia, operator pages). You must:

1. Only assert facts that are directly supported by the source material.
2. Cite the source URL for every non-trivial field you populate.
3. Use ISO 8601 dates (YYYY-MM-DD) when a date is given.
4. Report capacity in megawatts (MW) of IT load when stated. Convert from kW (÷1000) or GW (×1000).
5. If a field is uncertain, leave it null. Do not guess.
6. Latitude/longitude should be the approximate centroid of the campus when
   the exact address is unknown.

Status definitions:
- operational: facility is live and serving production traffic
- under_construction: ground broken, construction in progress
- planned: announced but not yet started construction
- retired: decommissioned

Return JSON matching the requested schema. Do not include commentary."""


def _client() -> Anthropic:
    if not CLIENT_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
    return Anthropic(api_key=CLIENT_KEY)


def call_claude_with_schema(
    user_message: str,
    schema_description: str,
    max_tokens: int = 2000,
    cache_system: bool = True,
) -> dict[str, Any]:
    """Call Claude and parse JSON response.

    The system prompt is marked cacheable to keep per-call costs down when
    running many enrichment calls in a single batch.
    """
    client = _client()
    system_blocks = [
        {"type": "text", "text": SYSTEM_PROMPT,
         "cache_control": {"type": "ephemeral"} if cache_system else None},
        {"type": "text", "text": f"OUTPUT SCHEMA:\n{schema_description}"},
    ]
    # Strip None cache_control entries (older SDKs reject them)
    system_blocks = [
        {k: v for k, v in b.items() if v is not None} for b in system_blocks
    ]

    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user_message}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    # Best effort JSON extraction
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first '{' and last '}'
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise
