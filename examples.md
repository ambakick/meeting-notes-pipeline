# Example Inputs & Outputs

All outputs below are from real Claude API calls (claude-sonnet-4), not mocked.

---

## Inputs

### Input A — Clean (bullet points)

```
- We talked about the Q2 launch timeline
- Sarah mentioned design might slip by a week
- Someone needs to follow up with the vendor about pricing
- Alex will check with finance on budget approval
- Not sure who is owning the landing page yet
```

### Input B — Messy (stream-of-consciousness)

```
ok so the main thing was Q2 launch timing. sarah brought up that design is behind,
sounds like maybe a week? she didn't say it's definitely slipping but it felt like
a heads up. we talked about the vendor situation for a while — pricing is still open
and someone said they'd follow up but i honestly don't remember who. alex said he's
got the budget thing, he's gonna check with finance. oh and the landing page came up
again, i think everyone assumed someone else was handling it. nobody actually said
"i'll do it" though.
```

---

## Naive Baseline Output (Input B)

Free-form markdown. No schema, no confidence levels, no evidence trail.

```
Action Items:

| Action Item                     | Owner      | Status                               |
|---------------------------------|------------|--------------------------------------|
| Follow up on vendor pricing     | UNASSIGNED | Someone committed but not identified |
| Check budget with finance       | Alex       | Open                                 |
| Handle landing page development | UNASSIGNED | No owner identified                  |

Critical Issues:
- Two action items lack clear owners
- Design timeline risk needs clarification with Sarah
- Consider follow-up meeting to assign unresolved items
```

---

## V1 Output — Single-Step Structured (Input B)

One detailed prompt with classification rules. Structured JSON output.

```
Action Items:
  1. [COMMITTED] Check with finance on budget
     Owner: alex | Confidence: high
     Evidence: "alex said he's got the budget thing, he's gonna check with finance"

  2. [SUGGESTED] Follow up on vendor pricing
     Owner: unassigned | Confidence: low  ** NEEDS CLARIFICATION
     Evidence: "someone said they'd follow up but i honestly don't remember who"

  3. [SUGGESTED] Handle landing page development/ownership
     Owner: unassigned | Confidence: low  ** NEEDS CLARIFICATION
     Evidence: "i think everyone assumed someone else was handling it.
               nobody actually said 'i'll do it' though"

  4. [RISK_FLAG] Design schedule may slip approximately one week
     Owner: sarah | Confidence: medium  ** NEEDS CLARIFICATION
     Evidence: "sarah brought up that design is behind, sounds like maybe a week?
               she didn't say it's definitely slipping but it felt like a heads up"

Open Questions:
  1. Who will take ownership of the landing page work?
  2. Who committed to following up on vendor pricing?
```

---

## V2 Output — Two-Step Pipeline (Input B)

### Step 1: Normalized Statements

Raw messy notes broken into one clean statement per topic, with hedging language preserved.

```
1. Sarah brought up that design is behind, sounds like maybe a week, and she didn't
   say it's definitely slipping but it felt like a heads up regarding Q2 launch timing.
2. Pricing is still open for the vendor situation and someone said they'd follow up
   but I honestly don't remember who.
3. Alex said he's got the budget thing and he's gonna check with finance.
4. The landing page came up again, I think everyone assumed someone else was handling
   it, but nobody actually said 'I'll do it'.
```

### Step 2: Classified Structured Output

```json
{
  "summary": "Meeting focused on Q2 launch timing with design potentially running a week behind. Several vendor and budget items were discussed but ownership remains unclear for key tasks.",
  "action_items": [
    {
      "task": "Monitor design timeline — possible 1-week delay affecting Q2 launch",
      "owner": "Sarah",
      "confidence": "medium",
      "needs_clarification": true,
      "evidence": "sarah brought up that design is behind, sounds like maybe a week? she didn't say it's definitely slipping but it felt like a heads up",
      "category": "risk_flag"
    },
    {
      "task": "Follow up on vendor pricing",
      "owner": "unassigned",
      "confidence": "low",
      "needs_clarification": true,
      "evidence": "pricing is still open and someone said they'd follow up but i honestly don't remember who",
      "category": "suggested"
    },
    {
      "task": "Check with finance on budget",
      "owner": "Alex",
      "confidence": "high",
      "needs_clarification": false,
      "evidence": "alex said he's got the budget thing, he's gonna check with finance",
      "category": "committed"
    },
    {
      "task": "Handle landing page development",
      "owner": "unassigned",
      "confidence": "low",
      "needs_clarification": true,
      "evidence": "the landing page came up again, i think everyone assumed someone else was handling it. nobody actually said \"i'll do it\" though",
      "category": "suggested"
    }
  ],
  "open_questions": [
    {
      "question": "Will the design delay impact the Q2 launch timeline?",
      "context": "Design is potentially running a week behind schedule",
      "raised_by": "Sarah"
    },
    {
      "question": "Who is responsible for following up on vendor pricing?",
      "context": "Someone committed to follow up but the person wasn't clearly identified",
      "raised_by": null
    },
    {
      "question": "Who will actually handle the landing page work?",
      "context": "Task keeps coming up but no one has claimed ownership",
      "raised_by": null
    }
  ]
}
```

---

## Key Differences Across Versions (Input B)

| | Naive | V1 | V2 |
|---|---|---|---|
| Output format | Free-form markdown | Structured JSON | Structured JSON |
| Action items | 3 | 4 | 4 |
| Design risk captured | Mentioned in notes only | risk_flag action item | risk_flag action item + open question |
| Vendor confidence | No confidence level | low | low |
| Landing page | Action item (no owner) | suggested, low confidence | suggested, low confidence + open question |
| Open questions | None separated | 2 | 3 |
| Evidence quotes | None | Yes | Yes |
| Intermediate output | None | None | Normalized statements (inspectable) |
