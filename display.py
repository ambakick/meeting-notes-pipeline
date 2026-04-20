"""Display and formatting helpers for terminal output."""

from __future__ import annotations

import json

from models import MeetingOutput

W = 64


def header(text: str, char: str = "="):
    print(f"\n{char * W}")
    print(f"  {text}")
    print(char * W)


def show(out: MeetingOutput, label: str):
    header(label)
    print(f"\nSummary:\n  {out.summary}\n")

    print("Action Items:")
    for i, a in enumerate(out.action_items, 1):
        flag = "  ** NEEDS CLARIFICATION" if a.needs_clarification else ""
        print(f"  {i}. [{a.category.upper()}] {a.task}")
        print(f"     Owner: {a.owner} | Confidence: {a.confidence}{flag}")
        print(f'     Evidence: "{a.evidence}"')
        print()

    if out.open_questions:
        print("Open Questions:")
        for i, q in enumerate(out.open_questions, 1):
            by = f" (raised by {q.raised_by})" if q.raised_by else ""
            print(f"  {i}. {q.question}{by}")
            print(f"     Context: {q.context}")
            print()
