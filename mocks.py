"""Mock data for --mock demo mode (no API key needed).

Hand-crafted realistic responses that demonstrate the differences
between naive, V1, and V2 approaches.
"""

from models import ActionItem, MeetingOutput, OpenQuestion

# ── Naive Baseline ──────────────────────────────────────────────

MOCK_NAIVE = {
    "A": (
        "Summary:\n"
        "The team discussed the Q2 launch timeline and potential delays.\n\n"
        "Action Items:\n"
        "- Follow up with vendor about pricing\n"
        "- Alex to check with finance on budget\n"
        "- Landing page ownership needs to be decided"
    ),
    "B": (
        "Summary:\n"
        "The team discussed Q2 launch timing and several open items.\n\n"
        "Action Items:\n"
        "- Follow up with vendor on pricing\n"
        "- Alex to check with finance on budget approval\n"
        "- Determine landing page ownership"
    ),
}

# ── V1: Single-Step Structured ──────────────────────────────────

MOCK_V1 = {
    "A": MeetingOutput(
        summary=(
            "The team reviewed the Q2 launch timeline. Sarah flagged a "
            "potential one-week design delay. Several items remain unowned."
        ),
        action_items=[
            ActionItem(
                task="Check with finance on budget approval",
                owner="Alex",
                confidence="high",
                needs_clarification=False,
                evidence="Alex will check with finance on budget approval",
                category="committed",
            ),
            ActionItem(
                task="Follow up with vendor about pricing",
                owner="unassigned",
                confidence="medium",
                needs_clarification=True,
                evidence="Someone needs to follow up with the vendor about pricing",
                category="suggested",
            ),
            ActionItem(
                task="Monitor design timeline for potential one-week slip",
                owner="Sarah",
                confidence="medium",
                needs_clarification=True,
                evidence="Sarah mentioned design might slip by a week",
                category="risk_flag",
            ),
        ],
        open_questions=[
            OpenQuestion(
                question="Who will own the landing page?",
                context="Ownership was raised but no one was assigned",
                raised_by=None,
            ),
        ],
    ),
    # V1 on messy input — note the subtle problems vs. V2:
    #   1. Vendor follow-up gets "medium" confidence (should be "low")
    #   2. Design risk drops the "not confirmed" qualifier
    #   3. Misses the "who committed to vendor follow-up?" open question
    "B": MeetingOutput(
        summary=(
            "The team discussed Q2 launch timing. Design may slip by a "
            "week per Sarah. Vendor pricing follow-up is pending. Alex "
            "will check on budget."
        ),
        action_items=[
            ActionItem(
                task="Check with finance on budget approval",
                owner="Alex",
                confidence="high",
                needs_clarification=False,
                evidence="alex said he's got the budget thing, he's gonna check with finance",
                category="committed",
            ),
            ActionItem(
                task="Follow up with vendor about pricing",
                owner="unassigned",
                confidence="medium",  # <-- V1 gives medium; V2 corrects to low
                needs_clarification=True,
                evidence="someone said they'd follow up but i honestly don't remember who",
                category="suggested",
            ),
            ActionItem(
                task="Design timeline may slip by one week",  # <-- drops uncertainty
                owner="Sarah",
                confidence="medium",
                needs_clarification=True,
                evidence="sarah brought up that design is behind, sounds like maybe a week",
                category="risk_flag",
            ),
        ],
        open_questions=[
            OpenQuestion(
                question="Who will own the landing page?",
                context="Nobody volunteered to take ownership",
                raised_by=None,
            ),
            # V1 MISSES: "Who committed to the vendor follow-up?"
        ],
    ),
}

# ── V2: Two-Step Pipeline ───────────────────────────────────────

MOCK_V2_STMTS = {
    "A": [
        "The team discussed the Q2 launch timeline.",
        "Sarah mentioned that design might slip by approximately one week.",
        "Someone needs to follow up with the vendor about pricing, but no specific person was named.",
        "Alex will check with finance on budget approval.",
        "It is unclear who is owning the landing page.",
    ],
    "B": [
        "The main discussion topic was Q2 launch timing.",
        "Sarah brought up that design is behind, possibly by about a week, but she did not say it is definitely slipping \u2014 it felt more like an early heads-up.",
        "Vendor pricing is still open and was discussed at length.",
        "Someone said they would follow up on vendor pricing, but the note-taker does not remember who it was.",
        "Alex said he will check with finance on the budget.",
        "The landing page came up again, but nobody actually volunteered to own it \u2014 everyone seemed to assume someone else was handling it.",
    ],
}

MOCK_V2 = {
    "A": MeetingOutput(
        summary=(
            "The team reviewed the Q2 launch timeline. Sarah flagged a "
            "potential one-week design slip. Alex is handling budget "
            "approval, but vendor pricing and landing page ownership "
            "remain unresolved."
        ),
        action_items=[
            ActionItem(
                task="Check with finance on budget approval",
                owner="Alex",
                confidence="high",
                needs_clarification=False,
                evidence="Alex will check with finance on budget approval",
                category="committed",
            ),
            ActionItem(
                task="Follow up with vendor about pricing",
                owner="unassigned",
                confidence="medium",
                needs_clarification=True,
                evidence="Someone needs to follow up with the vendor about pricing",
                category="suggested",
            ),
            ActionItem(
                task="Track design timeline \u2014 potential one-week delay",
                owner="Sarah",
                confidence="medium",
                needs_clarification=True,
                evidence="Sarah mentioned design might slip by a week",
                category="risk_flag",
            ),
        ],
        open_questions=[
            OpenQuestion(
                question="Who will own the landing page?",
                context="Ownership was raised but no one was assigned or volunteered",
                raised_by=None,
            ),
        ],
    ),
    # V2 on messy input — key improvements over V1:
    #   1. Vendor follow-up correctly at "low" confidence
    #   2. Design risk preserves "(not confirmed, early warning)"
    #   3. Surfaces "who committed to vendor follow-up?" as open question
    "B": MeetingOutput(
        summary=(
            "The team discussed Q2 launch timing. Sarah gave a soft "
            "warning that design may slip ~1 week but did not confirm. "
            "Alex committed to checking budget with finance. Vendor "
            "pricing follow-up and landing page ownership are both "
            "unresolved."
        ),
        action_items=[
            ActionItem(
                task="Check with finance on budget approval",
                owner="Alex",
                confidence="high",
                needs_clarification=False,
                evidence="alex said he's got the budget thing, he's gonna check with finance",
                category="committed",
            ),
            ActionItem(
                task="Follow up with vendor on pricing",
                owner="unassigned",
                confidence="low",  # <-- correctly low
                needs_clarification=True,
                evidence="someone said they'd follow up but i honestly don't remember who",
                category="suggested",
            ),
            ActionItem(
                task="Monitor design timeline \u2014 Sarah flagged a possible ~1 week slip (not confirmed, early warning only)",
                owner="Sarah",
                confidence="medium",
                needs_clarification=True,
                evidence="she didn't say it's definitely slipping but it felt like a heads up",
                category="risk_flag",
            ),
        ],
        open_questions=[
            OpenQuestion(
                question="Who will own the landing page?",
                context="It came up again but nobody volunteered \u2014 everyone assumed someone else was handling it",
                raised_by=None,
            ),
            OpenQuestion(
                question="Who committed to the vendor pricing follow-up?",
                context="Someone said they'd handle it but the note-taker cannot remember who",
                raised_by=None,
            ),
        ],
    ),
}