"""Extraction pipelines: naive, V1 (single-step), and V2 (normalize -> classify)."""

from __future__ import annotations

from llm import call_llm, parse_json
from models import MeetingOutput


# ── Naive Baseline ──────────────────────────────────────────────

def naive_extract(client, notes: str) -> str:
    """Original broken implementation: one vague prompt, free-form text."""
    return call_llm(
        client,
        f"Summarize the meeting and list all action items with owners.\n\nNotes:\n{notes}",
        max_tokens=1024,
    )


# ── V1: Single-Step Structured ──────────────────────────────────

_V1_PROMPT = """\
Analyze these meeting notes. Extract action items with classification.

CATEGORIES:
  committed  — explicit commitment by a named person
  suggested  — action mentioned but not firmly owned/committed
  risk_flag  — potential delay or problem that was flagged

CONFIDENCE:
  high   — named person + explicit verbal commitment
  medium — action is likely but ownership or certainty is soft
  low    — vague reference, no clear owner or timeline

RULES:
- If no one claimed ownership -> owner = "unassigned"
- PRESERVE uncertainty — do NOT upgrade hedging into firm commitments
- Include evidence (direct quote or close paraphrase from the notes)
- needs_clarification = true when owner, scope, or timeline is ambiguous
- Separate unresolved questions into open_questions (not action_items)
- Skip pure context/background that has no actionable component

Notes:
{notes}

Return ONLY valid JSON matching this schema:
{{
  "summary": "2-3 sentence meeting summary",
  "action_items": [
    {{
      "task": "clear description of what needs to be done",
      "owner": "person name or 'unassigned'",
      "confidence": "high|medium|low",
      "needs_clarification": true,
      "evidence": "quote from the notes",
      "category": "committed|suggested|risk_flag"
    }}
  ],
  "open_questions": [
    {{
      "question": "the unresolved question",
      "context": "why it matters",
      "raised_by": "person or null"
    }}
  ]
}}"""


def v1_extract(client, notes: str) -> MeetingOutput:
    """V1: One detailed prompt -> structured JSON. Better than naive, but struggles with messy input."""
    raw = call_llm(client, _V1_PROMPT.format(notes=notes))
    return MeetingOutput(**parse_json(raw))


# ── V2: Two-Step Pipeline (Normalize -> Classify) ───────────────

_NORM_PROMPT = """\
Break these meeting notes into discrete statements — one per topic.

Group related details about the SAME topic into a single statement.
For example, if someone flags a risk AND adds qualifiers about it,
combine those into one statement rather than splitting them apart.

CRITICAL: Preserve the original certainty level. If the notes say
"maybe", "sounds like", "not sure", or "I think" — keep that hedging
language in the extracted statement. Do NOT upgrade vague language
into firm claims.

Notes:
{notes}

Return ONLY a JSON array of strings."""


_CLASSIFY_PROMPT = """\
Classify these pre-extracted meeting statements into structured output.

Statements:
{statements}

Original notes (for evidence quotes):
{original}

STEP 1 — Assign each statement an ACTION CATEGORY:
  committed  — explicit pledge by a named person -> high confidence
  suggested  — action mentioned but not firmly owned -> medium/low confidence
  risk_flag  — potential delay, concern, or risk flagged, even if unconfirmed -> track it
  context    — pure background info -> OMIT from output entirely

STEP 2 — SEPARATELY, check if the statement also contains or implies an
unresolved question. A single statement can produce BOTH an action_item
AND an open_question.

EXAMPLE — dual output from one statement:
  Statement: "Sarah mentioned design might slip by a week, but she wasn't sure"
  -> action_item: category=risk_flag, task="Monitor design timeline — possible 1-week delay", owner="Sarah"
  -> open_question: "Will the design delay impact the launch timeline?"

RULES:
- owner = specific person's name, or "unassigned" if nobody claimed it
- confidence: "high" ONLY for explicit named commitments
- needs_clarification = true if owner, scope, or timeline is ambiguous
- evidence = quote from the ORIGINAL notes (not from the extracted statements)

Return ONLY valid JSON matching this schema:
{{
  "summary": "2-3 sentence summary of key discussion points and outcomes",
  "action_items": [
    {{
      "task": "clear description of what needs to be done",
      "owner": "person name or 'unassigned'",
      "confidence": "high|medium|low",
      "needs_clarification": true,
      "evidence": "quote from original notes",
      "category": "committed|suggested|risk_flag"
    }}
  ],
  "open_questions": [
    {{
      "question": "the unresolved question",
      "context": "why it came up or why it matters",
      "raised_by": "person or null"
    }}
  ]
}}"""


def v2_normalize(client, notes: str) -> list[str]:
    """Step 1: Raw notes -> clean, discrete statements with uncertainty preserved."""
    raw = call_llm(client, _NORM_PROMPT.format(notes=notes), max_tokens=1024)
    return parse_json(raw)


def v2_classify(client, stmts: list[str], original: str) -> MeetingOutput:
    """Step 2: Classify each normalized statement -> structured output."""
    numbered = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(stmts))
    raw = call_llm(
        client, _CLASSIFY_PROMPT.format(statements=numbered, original=original)
    )
    return MeetingOutput(**parse_json(raw))


def v2_extract(client, notes: str) -> tuple[list[str], MeetingOutput]:
    """Full V2 pipeline: normalize -> classify. Returns intermediate statements + result."""
    stmts = v2_normalize(client, notes)
    result = v2_classify(client, stmts, notes)
    return stmts, result
