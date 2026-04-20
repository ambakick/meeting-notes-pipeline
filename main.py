"""
Meeting Notes -> Action Items Pipeline
=======================================
Nascent Agentic Ops Take-Home Assignment

All LLM calls use Claude via the Anthropic Python SDK.
Run with --mock for a no-API-key demo using pre-crafted responses.

Usage:
    pip install -r requirements.txt
    python main.py --mock              # demo with mock responses
    python main.py                     # real API (needs ANTHROPIC_API_KEY)
    python main.py -i notes.txt        # process a custom notes file
"""

from __future__ import annotations

import argparse
import json
import sys

from display import header, show
from extractors import naive_extract, v1_extract, v2_extract
from inputs import INPUT_A, INPUT_B
from mocks import MOCK_NAIVE, MOCK_V1, MOCK_V2, MOCK_V2_STMTS


W = 64


def main():
    ap = argparse.ArgumentParser(description="Meeting Notes -> Action Items")
    ap.add_argument("--mock", action="store_true", help="Mock mode (no API key)")
    ap.add_argument("-i", "--input", type=str, help="Custom meeting notes file")
    args = ap.parse_args()

    mock = args.mock
    client = None

    if not mock:
        try:
            from anthropic import Anthropic

            client = Anthropic()
        except Exception as e:
            print(f"Could not init Anthropic client: {e}")
            print("Set ANTHROPIC_API_KEY, or run with --mock for a demo.\n")
            sys.exit(1)

    # ── Custom input mode ──
    if args.input:
        if mock:
            print("Cannot combine --input with --mock.\n")
            sys.exit(1)
        notes = open(args.input).read()
        stmts, result = v2_extract(client, notes)
        print("\nNormalized Statements:")
        for i, s in enumerate(stmts, 1):
            print(f"  {i}. {s}")
        show(result, "V2 Pipeline Result")
        print("\nJSON:")
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
        return

    # ── Full demo mode ──
    if mock:
        print("\n[MOCK MODE] Using pre-crafted responses for demonstration.")
        print("[MOCK MODE] Run without --mock to use real Claude API calls.\n")

    print("#" * W)
    print("  MEETING NOTES -> ACTION ITEMS PIPELINE")
    print("  Nascent Agentic Ops Take-Home")
    print("#" * W)

    # ── 1. Naive Baseline ──
    header("SECTION 1: NAIVE BASELINE", "=")
    if mock:
        n_a, n_b = MOCK_NAIVE["A"], MOCK_NAIVE["B"]
    else:
        n_a = naive_extract(client, INPUT_A)
        n_b = naive_extract(client, INPUT_B)

    print("\n--- Input A (Clean) ---")
    print(n_a)
    print("\n--- Input B (Messy) ---")
    print(n_b)

    # ── 2. V1: Single-Step ──
    header("SECTION 2: V1 \u2014 SINGLE-STEP STRUCTURED", "=")
    if mock:
        v1_a, v1_b = MOCK_V1["A"], MOCK_V1["B"]
    else:
        v1_a = v1_extract(client, INPUT_A)
        v1_b = v1_extract(client, INPUT_B)

    show(v1_a, "V1 -> Input A (Clean)")
    show(v1_b, "V1 -> Input B (Messy)")

    # ── 3. V2: Two-Step Pipeline ──
    header("SECTION 3: V2 \u2014 TWO-STEP PIPELINE (NORMALIZE -> CLASSIFY)", "=")
    if mock:
        s_a, s_b = MOCK_V2_STMTS["A"], MOCK_V2_STMTS["B"]
        v2_a, v2_b = MOCK_V2["A"], MOCK_V2["B"]
    else:
        s_a, v2_a = v2_extract(client, INPUT_A)
        s_b, v2_b = v2_extract(client, INPUT_B)

    print("\n--- Step 1 Output: Normalized Statements (Input B, Messy) ---")
    print("    [Shows how the normalization step cleans messy notes while")
    print("     preserving uncertainty language]\n")
    for i, s in enumerate(s_b, 1):
        print(f"  {i}. {s}")

    show(v2_a, "V2 -> Input A (Clean)")
    show(v2_b, "V2 -> Input B (Messy)")

    # ── 4. Comparison: Before vs After ──
    header("SECTION 4: COMPARISON \u2014 NAIVE vs V2 (Input B, Messy)", "=")

    print("\n--- BEFORE (Naive) ---")
    print(n_b)

    print("\n--- AFTER (V2 Structured JSON) ---")
    print(json.dumps(v2_b.model_dump(), indent=2, ensure_ascii=False))

    # ── 5. V1 vs V2 Key Differences ──
    header("SECTION 5: ITERATION \u2014 V1 vs V2 ON MESSY INPUT", "=")
    print()
    print("  Problem 1: Vendor follow-up confidence")
    print("    V1: confidence = 'medium'")
    print("    V2: confidence = 'low'   <-- correct: note-taker forgot who committed")
    print()
    print("  Problem 2: Design risk loses uncertainty")
    print("    V1: 'Design timeline may slip by one week'")
    print("    V2: '...possible ~1 week slip (not confirmed, early warning only)'")
    print()
    print("  Problem 3: Missing open question")
    print("    V1: only surfaces 'Who will own the landing page?'")
    print("    V2: also catches 'Who committed to vendor pricing follow-up?'")
    print("         (the normalization step extracted this as a discrete fact,")
    print("          making it visible to the classifier)")
    print()


if __name__ == "__main__":
    main()
