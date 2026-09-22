# PROMPT LOG

Real history only. A version appears here when it was actually written and run.
No entry is added retrospectively to make the progression look tidier than it
was. "Measured result" stays empty until a number exists.

---

## classify_v1  —  2026-09-21

**What it is.** First and only classifier prompt written. Single ticket in,
one JSON object out: `{theme, confidence, evidence_phrase}`.

**Design choices made up front, and why:**
- The 13-label taxonomy is injected from `config.TAXONOMY` rather than typed
  into the prompt, so the prompt and the pydantic validator can never disagree
  about what a legal label is.
- Ticket text is wrapped in `<<<TICKET>>>` delimiters with an explicit rule
  that the contents are customer data and never instructions. Ticket free text
  is untrusted input.
- Rule 1 ("classify the primary problem, not every topic") exists because of
  what I read in the 66-ticket sample: messages routinely open with a purchase
  date, name a product, and demand a refund while the actual fault is something
  else. Example seen: *"ordered my pulse last month. firmware update is stuck
  at 67%"* carries the bot tag Charging & Battery.
- Rule 2 exists for the same reason in reverse: "I want my money back" appears
  in messages about login failures, app crashes and delivery delays. Taken at
  face value it would collapse half the taxonomy into refunds.
- Rule 6 forbids the model emitting any number except confidence. Numbers are
  computed in `metrics.py`.

**What changed vs a previous version.** Nothing. This is v1.

**Measured result.** *Not yet measured.* No live run has been made — no API key
has been used in this project. Accuracy is unknown until the 96-ticket gold set
is labelled and `evaluate.py` is run against real predictions.

**Kept / discarded.** Kept, untested.

---

## digest_v1  —  2026-09-21

**What it is.** Prose-only prompt for the weekly digest. Receives the frozen
`out/metrics.json` and writes the narrative around numbers that already exist.

**Design choices:**
- Rule 1 forbids adding, averaging, rounding, projecting, converting or
  inferring any figure, and forbids writing a sentence whose number is not in
  the JSON. This is the whole point of freezing metrics to disk first.
- Rule 3 requires a count and up to three example ticket IDs after every claim,
  so any line in the digest can be traced back to rows in the export.
- Rule 6 makes the model declare a MOCK section in capitals rather than
  presenting fallback labels as findings.

**Measured result.** *Not yet measured.* The shipped sample digest was produced
by the deterministic writer in `report.py`, not by a model, so this prompt has
not yet been run.

**Kept / discarded.** Kept, untested.

---

## Discarded before it was written

- **Multi-label classification.** Rejected: 3.8% of tickets match three or more
  theme keyword families, so multi-label is defensible, but it makes an
  80–100 sample eval unscoreable and the digest ambiguous about what to count.
  Single label plus confidence instead.
- **Batching several tickets per call.** See decisions.md D18.
- **Asking the model to score severity or sentiment.** Nothing in the support
  policy prices either, so there would be no way to check the output or act on
  it.
