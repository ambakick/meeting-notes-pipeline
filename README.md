# Meeting Notes -> Action Items: Write-Up

## 1. Diagnosis: What's Broken

The naive implementation has one core problem: a single underspecified prompt is doing too many jobs simultaneously — parsing informal language, identifying actions, classifying commitment levels, attributing owners, and summarizing — all with no guidance on what "good" looks like.

This leads to:

### No structured output

Free-form text can't be parsed, filtered by owner, sorted by confidence, or piped into a task tracker. The output is a dead end — you can read it, but you can't do anything programmatic with it.

### No classification taxonomy

The prompt says "list all action items with owners" but never defines what an action item *is*. "Alex will check with finance" (firm commitment with a named owner) looks identical to "someone needs to follow up with the vendor" (unowned vague suggestion). The system flattens commitment certainty into a flat bullet list.

### No separation between actions and open questions

When the notes say "not sure who is owning the landing page," that's an unresolved question, not a tracked task. The naive system presents it as a normal action item, giving a reader no signal that this is actually an **unresolved gap**.

**Note on model capability:** Modern Claude models are capable enough that even the naive prompt produces reasonable-looking output — identifying some owners, flagging unassigned items, even adding recommendations. The problems are structural: the output is free-form text that can't be acted on programmatically, and there's no consistent schema for downstream systems to consume.

---

## 2. Redesign: V1 — Single-Step Structured Extraction

### What it does

V1 replaces the vague naive prompt with one detailed prompt that includes explicit classification rules and a JSON output schema. The prompt defines:

- **Categories**: `committed` (firm pledge by a named person), `suggested` (action mentioned but not owned), `risk_flag` (delay or concern raised)
- **Confidence levels**: `high` (named person + explicit commitment), `medium` (likely but soft), `low` (vague, no clear owner)
- **Rules**: preserve uncertainty, include evidence quotes, flag items needing clarification, separate open questions from action items

### What it solves

V1 is a significant improvement over naive:

- **Machine-readable output** — Pydantic-validated JSON that can feed a task tracker, Slack bot, or dashboard
- **Classification taxonomy** — every item gets a category, confidence level, and owner
- **Evidence trail** — every extraction traces back to what was actually said
- **Open questions separated** — unresolved items aren't masquerading as action items

### Where it falls short

V1 works well on clean, bullet-point notes (Input A). On messy, stream-of-consciousness notes (Input B), it handles most cases correctly but has one structural limitation: the single prompt is simultaneously parsing informal language AND classifying it. This means there's no intermediate representation to inspect when something goes wrong — it's a black box.

---

## 3. Redesign: V2 — Two-Step Pipeline

### Why add a second step?

The motivation for V2 isn't primarily accuracy on small inputs — V1 already handles these test cases reasonably well. The motivation is **observability, debuggability, and scalability**:

1. **You can see where it breaks.** When V2 misclassifies something, you inspect the normalized statements and immediately know: did the normalizer misparse the input, or did the classifier mislabel a clean statement? With V1, you see wrong output and have no idea which part of the reasoning failed.

2. **You can fix each step independently.** The normalizer doesn't know about categories. The classifier doesn't need to parse messy language. If classification is wrong but normalization is good, the fix is isolated to the classify prompt.

3. **It scales to harder inputs.** These test inputs are short. On a 30-minute meeting transcript, a single prompt doing parsing + classification simultaneously will degrade faster than a pipeline. The normalization step becomes more valuable as input complexity grows.

4. **The intermediate output is independently useful.** Clean normalized statements can feed different downstream tasks — action items, decision logs, risk registers — without re-parsing raw notes each time.

### Architecture

```
Raw Notes --> [Step 1: Normalize] --> Clean Statements --> [Step 2: Classify] --> Structured Output
```

**Step 1 — Normalize** (1 LLM call)

Takes raw meeting notes and extracts clean statements — one per topic, grouping related details together. The critical instruction: *preserve the original certainty level*. If the notes say "maybe a week," the statement must say "maybe a week," not "one week."

**Step 2 — Classify & Structure** (1 LLM call)

Takes the clean statements and performs two parallel operations on each:
1. Assigns an action category (`committed`, `suggested`, `risk_flag`, or `context`)
2. Checks if the statement also implies an unresolved question

A single statement can produce both an action item and an open question.

### Output Schema

```json
{
  "summary": "2-3 sentence summary",
  "action_items": [
    {
      "task": "what needs to be done",
      "owner": "person or 'unassigned'",
      "confidence": "high|medium|low",
      "needs_clarification": true,
      "evidence": "quote from the notes",
      "category": "committed|suggested|risk_flag"
    }
  ],
  "open_questions": [
    {
      "question": "the unresolved question",
      "context": "why it matters",
      "raised_by": "person or null"
    }
  ]
}
```

### Tradeoffs

| Decision | Upside | Downside |
|---|---|---|
| 2 LLM calls vs. 1 | Debuggable pipeline, scales to longer inputs | ~2x latency and token cost |
| Pydantic schema validation | Always-parseable, typed output | Extra dependency; constrains free-form context |
| Evidence field on every item | Full traceability — verify any extraction | More verbose output |
| Preserving uncertainty | Honest, trustworthy output | Looks less "polished" than fabricated certainty |

---

## 4. Iteration: Debugging the V2 Pipeline

Building V2 required two rounds of prompt debugging. Both illustrate how the two-step architecture makes problems diagnosable.

### Problem 1: Normalization granularity

**What happened:** The initial normalization prompt said "one statement per fact." The model took this literally and split Sarah's design concern into three separate fragments:

```
2. Sarah brought up that design is behind
3. It sounds like maybe a week behind on design
4. Sarah didn't say it's definitely slipping but it felt like a heads up
```

The landing page got similar treatment (three fragments). By the time the classifier saw these, it lost the compound signal — that Sarah's concern was a single risk with hedging, not three separate observations. The classifier treated them as background context and dropped the risk_flag entirely.

**Diagnosis:** The normalization step was working (preserving hedging language) but at the wrong granularity. Splitting related facts about the same topic into atomic statements destroyed the context the classifier needed.

**Fix:** Changed the normalization prompt from "one statement per fact" to "one statement per topic — group related details about the same topic into a single statement." Result: 4 consolidated statements instead of 12, each carrying full context:

```
1. Sarah brought up that design is behind, sounds like maybe a week, and she didn't
   say it's definitely slipping but it felt like a heads up regarding Q2 launch timing.
2. Pricing is still open for the vendor situation and someone said they'd follow up
   but I honestly don't remember who.
3. Alex said he's got the budget thing and he's gonna check with finance.
4. The landing page came up again, I think everyone assumed someone else was handling
   it, but nobody actually said 'I'll do it'.
```

### Problem 2: Single-label routing in the classifier

**What happened:** After fixing normalization, the classifier still dropped Sarah's design risk as an action item. It only appeared as an open question. Meanwhile, V1 (single-step) correctly captured it as a `risk_flag`. V2 was doing *worse* than V1 on this specific case.

**Diagnosis:** The classify prompt listed five categories including `open_question` at the same level as `risk_flag`:

```
CLASSIFY each statement as one of:
  committed     — explicit pledge by a named person
  suggested     — action mentioned but not firmly owned
  risk_flag     — delay or concern raised
  open_question — unresolved, needs a decision
  context       — background info only
```

The phrase **"as one of"** created a single-label routing decision. The model picked exactly one destination per statement. Sarah's design concern — full of hedging language preserved by the normalizer — matched "unresolved, needs a decision" (`open_question`) better than "delay or concern raised" (`risk_flag`). So the model routed it to `open_question` and never created a `risk_flag` action item.

The prompt did have a rule saying "If a statement implies BOTH an action AND an unresolved question, create entries in both" — but this was buried in the RULES section and couldn't override the single-label framing already established by "as one of."

V1 didn't have this problem because it only listed three action categories (`committed`/`suggested`/`risk_flag`). Open questions were handled by a separate rule, so there was no competing `open_question` label to steal items from `risk_flag`.

**Fix:** Restructured the classify prompt to make classification and question-extraction two parallel operations instead of one routing decision:

```
STEP 1 — Assign each statement an ACTION CATEGORY:
  committed  — explicit pledge by a named person
  suggested  — action mentioned but not firmly owned
  risk_flag  — potential delay, concern, or risk flagged, even if unconfirmed
  context    — pure background info -> OMIT

STEP 2 — SEPARATELY, check if the statement also contains or implies
an unresolved question. A single statement can produce BOTH an action_item
AND an open_question.
```

Added a few-shot example demonstrating dual output for exactly the design-risk scenario. This locked in the multi-label behavior.

### Result

After both fixes, V2 on messy Input B produces:

- **4 action items**: design risk (`risk_flag`), vendor follow-up (`suggested`), budget check (`committed`), landing page (`suggested`)
- **3 open questions**: design delay impact, vendor pricing ownership, landing page ownership
- Sarah's design concern correctly appears as **both** a `risk_flag` action item and an open question — something V1's single-pass architecture can't express

---

## 5. Before vs. After Comparison

### Input B (Messy) — Naive Output

```
Action Items:

| Action Item                    | Owner       | Status                             |
|--------------------------------|-------------|------------------------------------|
| Follow up on vendor pricing    | UNASSIGNED  | Someone committed but not identified |
| Check budget with finance      | Alex        | Open                               |
| Handle landing page development| UNASSIGNED  | No owner identified                |

Critical Issues:
- Two action items lack clear owners
- Design timeline risk needs clarification with Sarah
- Consider follow-up meeting to assign unresolved items
```

The naive output is actually more structured than you might expect — modern Claude is capable enough to add tables and flag issues even with a vague prompt. But the output is still free-form markdown: no confidence levels, no categories, no evidence trail, no clear separation between action items and open questions, and no machine-readable schema for downstream systems.

### Input B (Messy) — V2 Output

```json
{
  "summary": "Meeting focused on Q2 launch timing with design potentially running
    a week behind. Several vendor and budget items were discussed but ownership
    remains unclear for key tasks.",
  "action_items": [
    {
      "task": "Monitor design timeline — possible 1-week delay affecting Q2 launch",
      "owner": "Sarah",
      "confidence": "medium",
      "needs_clarification": true,
      "evidence": "sarah brought up that design is behind, sounds like maybe a week?
        she didn't say it's definitely slipping but it felt like a heads up",
      "category": "risk_flag"
    },
    {
      "task": "Follow up on vendor pricing",
      "owner": "unassigned",
      "confidence": "low",
      "needs_clarification": true,
      "evidence": "pricing is still open and someone said they'd follow up but i
        honestly don't remember who",
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
      "evidence": "the landing page came up again, i think everyone assumed someone
        else was handling it. nobody actually said 'i'll do it' though",
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

### What improved

1. **Sarah's design warning** is captured as a `risk_flag` action item with uncertainty preserved, AND as an open question about timeline impact
2. **Vendor follow-up** is honestly marked `confidence: "low"` with `owner: "unassigned"`
3. **Landing page** is correctly a `suggested` action item with an associated open question about ownership
4. **Evidence trail** — every item traces back to what was actually said
5. **Three open questions** surfaced — design impact, vendor ownership gap, and landing page ownership
6. **Machine-readable** — the JSON output can feed a task tracker, dashboard, or Slack bot

---

## 6. What I'd Do Next

If this were moving toward production:

1. **Eval suite**: Build 20-30 meeting note examples with ground-truth labels. Measure extraction recall and classification precision across pipeline changes. LLM outputs vary between runs — an eval suite would catch regressions and validate that prompt changes actually improve consistency.
2. **Confidence calibration**: Validate that "high confidence" items are actually firm commitments >90% of the time by running against a labeled dataset.
3. **User feedback loop**: Let users correct misclassifications and use those corrections to refine prompts (few-shot examples from real corrections).
4. **Longer input testing**: These test inputs are short. The two-step architecture is designed to scale to longer transcripts — test with 30+ minute meeting notes to validate the normalization step's value at scale.
5. **Output integration**: Pipe structured output into Slack, Linear, or Notion — the schema is designed for this.
