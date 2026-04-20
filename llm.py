"""LLM client helpers."""

from __future__ import annotations

import json

MODEL = "claude-sonnet-4-20250514"


def call_llm(client, prompt: str, max_tokens: int = 2048) -> str:
    """Single-turn prompt to Claude; returns text."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def parse_json(raw: str):
    """Strip optional markdown fences and parse JSON."""
    t = raw.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1]
    if t.endswith("```"):
        t = t.rsplit("```", 1)[0]
    return json.loads(t.strip())
