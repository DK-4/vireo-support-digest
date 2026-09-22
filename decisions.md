# DECISIONS

Running log. Every entry is a choice that could reasonably have gone another
way. Where a warning in the brief or the policy did **not** turn out to be a
real problem in this data, that is recorded too — a check that came back clean
is still a decision.

---

## Phase 1 — data inspection

**D1. Dedupe on `ticket_id`, keeping the `helpdesk` row.**
653 ticket_ids appear exactly twice, always one `helpdesk` + one `legacy_fd`
row (the Sep-2025 re-import, policy §9). Column-by-column comparison: the pairs
differ on `resolved_at` (618 pairs) and `csat_score` (333 pairs) and are
identical everywhere else. The helpdesk copy carries the correct convention for
both. 12,528 → 11,875 rows. Nothing else is dropped anywhere in the pipeline.

**D2. Add 5:30 to `resolved_at` on `legacy_fd` rows only.**
On all 618 dup pairs with both timestamps, helpdesk − legacy = exactly 5.5
hours, with no exceptions. Independently: 1,874 rows had `resolved_at` before
`created_at`, which is impossible; after the shift, 0. Also 0 rows where
`resolved_at < first_response_at`. `created_at` and `first_response_at` are
identical across pairs, so only `resolved_at` is affected — consistent with
policy §9 ("resolution timestamps … reconstructed from the legacy event log,
which stores UTC"). Implemented as an assertion in `clean.fix_legacy_timezone`:
if the fix ever leaves an impossible timestamp the run fails rather than
publishing a number.

**D3. `csat_score` 0 → null on legacy rows.**
2,083 legacy rows carry 0; helpdesk rows carry blank (4,856) and never 0. On
dup pairs the crosstab is perfectly diagonal — every legacy 0 pairs with a
helpdesk blank. Policy §8 is explicit that a blank "must be excluded from
averages, not treated as zero". Keeping the zeros gives mean 2.49; correcting
gives 3.32 with a 44.4% response rate, matching the policy's "around 45%".

**D4. No currency conversion on refunds — checked and rejected.**
Policy §9 warns the legacy tool stored money "in its own native unit". Tested:
on the 120 dup pairs carrying a refund on both sides, the value is *identical*
every time, and the two source distributions match (medians 2,374 vs 2,499,
both max 13,998). There is no paise/rupee scaling in this extract. No
conversion is applied. Re-test this on any future export.

**D5. Collapse the agent roster to one row per agent anyway.**
README says agents.csv is one row per assignment and an agent may have several.
In this extract there are 44 rows and 44 unique agent_ids — no fan-out exists
today, and all 44 `to_date` values are blank. `load.load_agents` still collapses
to the newest assignment per agent so a future export with a real second
assignment row cannot silently double-count. Covered by a test.

**D6. Open/pending tickets excluded from closure and CSAT metrics.**
609 tickets have no `resolved_at` (376 open, 233 pending). 285 of them carry a
CSAT score even though policy §8 surveys on resolution. Recorded as an anomaly
in `out/clean_report.json` rather than used or quietly dropped.

**D7. "Same issue" for repeat contacts = same category within 30 days.**
Policy §10 does not define "same issue". Three readings are computed and all
three are in `metrics.json`: same category 13.2%, same product 29.3%, any
reason 34.4%. The conservative reading is headline. The spread is a factor of
2.6, so this is a definitional choice, not a measurement, and it is labelled as
such in the digest.

**D8. Per-channel contact costs from §4; Rs 290 blended where a channel is not
known.** Arjun used Rs 180 in the email thread; Priya corrected him to the Rs
290 blended policy figure on 9 Sep. The policy figure is used.

**D9. Leaderboard ranked within team and tier.**
Raw "tickets closed per week" is dominated by queue, not performance. Team
means: Logistics 5.30, Returns Desk 5.26, Billing 5.13, Email Frontline 3.52,
Chat Frontline 3.07, Voice Frontline 2.78, Escalations & Warranty 1.99. Median
handle time by channel: chat 35 min, voice 75, social 129, email 288 — an email
agent cannot out-close a chat agent. Tier 1 mean 3.81/wk vs Tier 2 mean 1.99;
all six Tier 2 agents land in the bottom seven of 44, which policy §6 forbids
("Tier 2 agents are not to be compared with Tier 1 on volume metrics").

**Important negative finding.** The obvious story — that high closers cut
corners — is not supported. Raw across 38 Tier 1 agents: closes/week vs repeat
rate r = +0.332 (p=0.042), vs CSAT r = −0.362 (p=0.025). But standardising
*within team* to remove the queue-mix confound, the repeat correlation collapses
to −0.199 (p=0.23, not significant) and CSAT flips **positive** to +0.342
(p=0.035). Within a team, closing more goes with *better* satisfaction. The
leaderboard is invalid because it ranks queues while appearing to rank people,
not because anyone is gaming it. Both views ship side by side (Priya, 9 Sep:
"the leaderboard stays, I want to see it").

**D10. Auto-closed tickets counted as attendance, shown in their own column.**
Policy §8 says a 72-hour auto-close "count[s] as a completed attendance". 1,107
tickets (9.8%). Included in the total because the policy says so, broken out
because it is not a human resolution.

**D11. Ambiguous fallback joins flagged, never silently resolved.**
`order_id` is blank on 4,023 tickets (33.9%). Using the README's
`customer_id` + `product_sku` fallback, 3,303 resolve to exactly one order and
**720 resolve to more than one**. Those 720 are never assigned to a first match.

**D12. Bot-category accuracy quoted only as disagreement with unambiguous
text.** On tickets whose text matches exactly one theme family, the bot agrees
79.1% (Connectivity), 73.9% (Audio Quality), 65.5% (Charging), 57.9% (App &
Firmware). This is a *signal*, not an error rate. The real error rate waits for
the human gold labels.

---

## This phase — verification, taxonomy, build

### D13. Business goal — verification and final definition

The brief asked me to switch away from goal 1 if more than 2 of 8 worked
examples looked like legitimate separate remedies, or if the counts moved
materially after the dedupe check. **Neither trigger fired**, so goal 1 stands
— but the verification surfaced a bigger, arithmetically provable pattern that
contains it, and the metric is defined on that instead.

**Dedupe check.** Double-compensated orders before dedupe: 103. After dedupe:
103. The *sets are identical*. The dedupe does not create or destroy a single
case. Denominator: 5,063 orders that generated at least one ticket.

**The 8 worked examples** (all ticket IDs post-dedupe):

| # | Order | Tickets | What happened | Verdict |
|---|---|---|---|---|
| 1 | VR883328 | TK-250483 (22 Feb 26) | Rs 2,878 refund, code DOA-REPL, **and** `replacement_issued=Y` on the same ticket. Order value Rs 2,878. | Clear §5 breach |
| 2 | VR885453 | TK-252411 (18 Apr 26), TK-253273 (14 May 26) | Rs 3,499 refund RETURN-QC-OK + replacement on the same ticket; order value Rs 3,499. | Clear §5 breach |
| 3 | VR886748 | TK-242214, TK-242279, TK-242337, TK-242463 (24 May – 7 Jun 25) | Refunded Rs 2,374 **twice** (both RETURN-QC-OK) *and* two replacement flags. Order value Rs 2,374 → paid out 2× the order plus goods. | Clear overpayment |
| 4 | VR902405 | TK-241193, TK-241236, TK-241296, TK-241494 (27 Mar – 15 Apr 25) | Rs 4,999 + Rs 1,000 refunds (both RETURN-QC-OK) + replacement. Order value Rs 4,999. | Clear overpayment |
| 5 | VR881415 | TK-245682, TK-245696, TK-245826, TK-248293, TK-253436 (14 Oct 25 – 18 May 26) | Rs 850 + Rs 4,249 DUP-PAYMENT, then Rs 4,249 DOA-REPL, plus a replacement. Order value Rs 4,249 → Rs 9,348 refunded. | Clear overpayment |
| 6 | VR909414 | TK-245921, TK-245983, TK-246295, TK-247538 (20 Oct – 30 Nov 25) | Rs 5,199 refunded **twice**, both RETURN-QC-OK, plus a replacement. Order value Rs 5,199. | Clear overpayment |
| 7 | VR880243 | TK-241323, TK-241975, TK-242051, TK-242561 (3 Apr – 13 Jun 25) | Rs 1,050 DUP-PAYMENT (a partial payment correction) then two replacements for an audio fault. | **Ambiguous — plausibly legitimate.** A duplicate-charge refund is not a product remedy. Two replacements on one order is odd but not a §5 breach. |
| 8 | VR880806 | TK-250741, TK-251249, TK-252294 (1 Mar – 15 Apr 26) | Rs 153 DUP-PAYMENT (10% of a Rs 1,529 order) then a replacement for an audio fault six weeks later. | **Ambiguous — plausibly legitimate.** Payment correction plus a separate fault remedy. |

Exactly **2 of 8** look like legitimate separate remedies, and both are the two
I deliberately selected as ambiguous. The trigger was "more than 2". It did not
fire.

**How a replacement was identified.** `replacement_issued == 'Y'`, the Y/N flag
the agent sets (README). There is no replacement date or replacement order ID
in the export, so a replacement is attributed to the ticket carrying the flag
and, for order-level roll-ups, to the order that ticket points at. This is the
weakest link in the chain and is stated as such in the README limitations.

**Exact definitions used.**
- *Refund* = `refund_amount_inr` is non-null on a ticket. 2,105 tickets. All
  2,105 carry a reason code; none are uncoded.
- *Replacement* = `replacement_issued == 'Y'`. 1,272 tickets.
- *Replacement cost* = `products.unit_cost_inr` + Rs 340 (policy §5). No
  refurbishment recovery assumed, as §5 requires.
- *Order value* = `orders.order_value_inr`.
- *Total compensation* (per order) = sum of refunds on all its tickets + the
  replacement cost once if any ticket flagged one.
- *Excess* = max(0, total compensation − order value).
- *Flagged* = excess > 0 **and** more than one remedy was given. A single
  remedy is never a breach even when it costs more than the order sold for —
  a discounted sale can leave unit_cost + Rs 340 above the sale price. This
  exclusion removes 7 orders that an earlier draft wrongly counted (185 → 178)
  and is covered by a test.

**The range, input by input** (window = 545 days = 5.97 quarters):

| Input | Value |
|---|---|
| Ticketed orders (denominator) | 5,063 |
| Flagged orders | 178 = **3.52%**, 29.8 per quarter |
| Total excess over order value | Rs 515,705 → **Rs 86,345 / quarter** |
| — of which refund-side (orders refunded more than once) | Rs 62,204 / quarter |
| — of which replacement-side | Rs 24,141 / quarter |
| Goodwill refunds over the §5 Rs 500 cap (37 of 42 GW-OTHER tickets) | Rs 18,071 / quarter |
| Target | 1.0% → a 71.6% reduction |
| **Low** (only the unarguable refund-side excess × 71.6%) | **Rs 44,511 / quarter** |
| **Mid** (all excess × 71.6%) | **Rs 61,829 / quarter** |
| **High** (all excess + goodwill cap enforcement × 71.6%) | **Rs 74,716 / quarter** |

**Refund cost by reason code** (deduped, 5.97 quarters):

| Code | Tickets | Total Rs | Rs / quarter | Mean Rs |
|---|---|---|---|---|
| RETURN-QC-OK | 837 | 2,438,350 | 408,256 | 2,913 |
| DUP-PAYMENT | 531 | 1,461,223 | 244,654 | 2,752 |
| CANCEL | 296 | 822,382 | 137,692 | 2,778 |
| PRICE-ADJ | 120 | 342,718 | 57,382 | 2,856 |
| DOA-REPL | 136 | 342,055 | 57,271 | 2,515 |
| LOST-TRANSIT | 91 | 285,621 | 47,822 | 3,139 |
| WTY-BUYBACK | 52 | 172,495 | 28,881 | 3,317 |
| GW-OTHER | 42 | 128,075 | 21,444 | 3,049 |
| **Total** | **2,105** | **5,992,919** | **1,003,402** | |

**What else I examined in refunds and rejected:**
- *Refund exceeding the order value on a single ticket* — **0 of 1,352**. The
  helpdesk appears to cap a single refund at order value. Rejected as a lever;
  it is also why the multi-ticket pattern is the only way to overpay.
- *DUP-PAYMENT as leakage* (531 tickets, Rs 244,654/qtr) — **rejected**. These
  are payment corrections, not remedies; refunding a duplicate charge is
  correct behaviour and excluding them is what keeps the goal honest.
- *PRICE-ADJ at a mean of Rs 2,856* — looks high for a "price or coupon
  adjustment" but §5 sets no cap on it, so there is no rule to measure it
  against. **Not counted.** Worth a question to Priya, not a number in a memo.
- *DOA-REPL coded but `replacement_issued=N`* — 135 tickets. Under §5 a DOA
  customer *chooses* refund or replacement, so a DOA refund with no replacement
  is correct. **Not a finding.**
- *Goodwill over the Rs 500 cap* — 37 of 42 GW-OTHER tickets exceed it, max Rs
  10,798, Rs 18,071/qtr of excess. This is a genuine §5 breach but a small and
  separate one. **Reported as the high end of the range only**, not folded into
  the headline.

**D13b. Target is 1.0%, not 0%.** Three reasons the floor is not zero. (i) §5
permits a goodwill credit up to Rs 500 on top of another remedy with Team Lead
approval, so a small excess can be legitimate. (ii) `order_value_inr` does not
obviously include shipping or return freight, so a refund that legitimately
covers postage can push total compensation past it. (iii) Finance may already
recover some of these downstream in a system not in this export. 1.0% leaves
roughly 5 orders a quarter of headroom for approved exceptions.

**What would make the saving zero:** if these excesses are already clawed back
by Finance outside the helpdesk; if `replacement_issued=Y` is being set on
tickets where no unit actually shipped (there is no replacement date or
dispatch record in the export to check this against); or if `order_value_inr`
is net of a discount that was separately refunded, making the arithmetic
comparison wrong. All three are stated in the README limitations. The first is
answerable with one question to Arjun and should be asked before the memo goes
out.

**Final goal statement:**
> **Cut orders compensated for more than they cost from 3.5% to 1.0% of
> ticketed orders — worth about Rs 45,000 to Rs 75,000 a quarter, central
> estimate Rs 62,000.**

### D14. Taxonomy is 13 labels, not 12 — flagged

The instruction was: add "Pre-sales / compatibility (no fault)" as an 11th
theme, split "Payment, invoice & account access" into two, and end with 12
labels including Unclear/other. Those two changes applied to the Phase 1 set
(10 themes + Unclear = 11 labels) give **13**, not 12:

  10 themes + Pre-sales = 11 themes; split Payment/Account = 12 themes;
  + Unclear/other = **13 labels**.

I implemented both substantive changes and accepted 13, on the grounds that the
two named changes are specific and reasoned while "12" reads as an arithmetic
slip. Nothing depends on the count — if you want 12, the cheapest merge is to
fold "Account access / login" (316 tickets, 2.7% of volume, 0.3% repeat rate)
back into "Payment & invoice"; that is a one-line change in `config.TAXONOMY`
and the eval sample would need regenerating. **Flagged rather than silently
resolved because it changes what you will be labelling against.**

### D15. Pre-sales excluded from fault-cost work
`config.NO_FAULT_LABELS` marks it. It reports in the digest volume section and
is kept out of anything that prices a fault.

### D16. Mock mode is watermarked, not merely noted
`classify.run` tags every mock label `label_source="MOCK"`, `report.py` prints
a block-quote warning at the top of any digest built on mock labels and repeats
"theme counts are MOCK" inline in the movers section, and `evaluate.py` prints
its own warning. Deterministic figures (volume, SLA, repeats, transfers,
business goal) are unaffected by mock mode and say so in the same document.

### D17. Partial final week excluded from every comparison
The export ends on 30 Jun 2026, a Tuesday. The final part-week holds 46 tickets
against 199 in the last full week, which renders as a −76.9% collapse that did
not happen. `metrics.weekly` marks each week complete/incomplete against the
last timestamp, nulls the change figure on incomplete weeks, and the digest
picks the last *complete* week and says the part-week was excluded. Covered by
a test.

### D18. Batch size is 1 ticket per call
Batching several tickets per call is cheaper but makes a single malformed
response poison a whole batch and makes the cache key ambiguous. At ~12k
tickets and a one-off run the saving is not worth the failure mode. The
`batch_size` parameter exists for a future change; it is 1 today.

### D19. Single-agent teams score 0, not NaN
Standardising within team divides by the team's standard deviation. A
one-agent team has no spread. The first implementation raised
`TypeError: boolean value of NA is ambiguous`; found by a test, not in
production. A one-agent team now scores 0 on every z-component.

### D20. The digest never receives a computed number from a model
`report.py` reads `out/metrics.json` and nothing else. When a real key is
present the model is handed that JSON plus labels and asked for prose only —
`prompts/digest_v1.txt` forbids adding, averaging, rounding, projecting or
inferring any figure. The deterministic writer in `report.py` is the default
and is what produced the shipped sample.
