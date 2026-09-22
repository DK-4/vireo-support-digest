# Submission form — draft answers

Fill in the bracketed items ([...]) before submitting. Everything else is
ready to paste as-is.

---

### What did you build, and what business outcome does it move? State the
### number and the money.

A pipeline that turns Vireo's 18-month ticket export into a weekly digest,
an agent leaderboard, and a Finance watchlist. The number it moves: **orders
compensated for more than they cost — 178 of 5,063 ticketed orders (3.5%),
worth Rs 45,000–75,000 a quarter (central estimate ~Rs 62,000) to bring down
to 1.0%.** This is a policy breach already written into Vireo's own support
policy (section 5: never both a refund and a replacement on one order); it's
invisible today because the two events are usually weeks apart on different
tickets. Full calculation, including the 8 worked examples I checked before
committing to this number, is in `decisions.md` (D13).

### What does one run cost, and what would a month cost at Vireo's volume
### (roughly 650 tickets a week)? Show the arithmetic. If you used no paid
### calls, say so.

I made real paid calls — 9 tickets successfully classified against Gemini's
`gemini-flash-latest` before I hit that model's free-tier rate limit (10
requests/minute) and paused rather than keep spending time against a free
quota. From those 9 real calls, measured (not estimated): **~784 input /
~32 output tokens per ticket**, at Gemini's published rate of $0.30 / $2.50
per million tokens:

- Per ticket: ~$0.0003 (~Rs 0.03)
- One run of the 96-ticket gold set: ~$0.03 (~Rs 2.92)
- Weekly at Vireo's ~650 tickets: ~$0.21 (~Rs 20)
- **Monthly at Vireo's volume: ~$0.89 (~Rs 86)**
- One-time backfill of all 11,875 historical tickets: ~$3.74 (~Rs 361)

At this ticket volume, classification cost is not a real constraint — free-
tier *rate* limits are. Full log of every attempt, success and failure, is in
`COST_LOG.md` and `out/llm_calls.jsonl`.

### How do you know it works? Sample size, how you checked, error rate, and
### the kind of case it gets wrong.

Two separate things were checked, honestly kept separate:

1. **The business number** (the money above) is pure arithmetic over the
   ticket/order/policy data — no model involved, verified twice (once in
   Phase 1, once by checking it survives the 653-row deduplication
   unchanged), and covered by tests.
2. **The theme classifier** — I hand-labelled 96 tickets myself, blind (no
   model prediction visible while labelling), stratified so every one of 13
   categories has at least 6 examples. Scored against the keyword-fallback
   placeholder (the only thing I could fully complete against a rate limit):
   **67.7% accuracy, 95% CI 57.8–76.2%.** It fails worst on ambiguous
   payment/refund-adjacent messages and over-uses the "unclear" catch-all
   (12 predicted, only 1 actually belonged there) — full confusion matrix in
   `out/eval_report.md`. This number describes the placeholder, not a real
   model; a real model run is one command away once rate limits allow it.

### Did you change, narrow, or push back on the client's ask?

Yes, four times, each recorded with the reasoning in `decisions.md`:
- The requested leaderboard (tickets closed/week) is shipped exactly as
  asked, but I added a second, corrected view ranked within team — the raw
  version mostly measures which team an agent sits in, not skill, and
  ranking Tier 2 warranty agents on it directly contradicts the client's own
  support policy.
- The business goal target is 1.0%, not 0%, because the policy itself allows
  a small legitimate exception (goodwill credits) — 0% would overstate the
  saving.
- I gave a range (Rs 45k–75k), not a single number, because part of the
  pattern is arithmetically certain and part depends on which remedy was the
  "correct" one, which the data can't fully resolve.
- I stopped chasing a live classifier run against a free-tier rate limit
  rather than spend disproportionate time on a number that doesn't move the
  business goal.

### What is wrong with what you are handing us? Be specific: bugs, shortcuts,
### things you know are off.

- Theme classification in the shipped digest is still MOCK (keyword
  fallback), clearly watermarked throughout — a live run is one command,
  blocked today by free-tier rate limits, not by the code.
- A "replacement" in the data is a Y/N flag with no dispatch date or order
  ID — the business goal leans on this being accurate; if it's set without a
  unit actually shipping, the saving shrinks. Flagged in `README.md`.
- 720 tickets (out of 4,023 with a blank order_id) can't be joined to a
  single order via the fallback join — left unassigned rather than guessed,
  which means order-level totals are a slight undercount.
- The 3.52%→1.0% target's low end assumes the flagged compensation should
  have gone to the *cheaper* remedy; I couldn't verify that from the data,
  only estimate a range.
- `.env`-based config with no `python-dotenv` — a minor convenience gap, not
  a correctness issue; documented in the README.

### What did you deliberately leave out, and why that rather than something
### else?

No dashboard or UI (the client explicitly said "I don't need a platform").
No database — 5 CSVs and 12k rows is a pandas problem, not an infrastructure
one. No embeddings or topic clustering — a fixed, auditable 13-label taxonomy
scores against a human gold set; clusters don't. No multi-label
classification, despite ~4% of tickets genuinely touching multiple themes —
single-label keeps an 80–100 sample evaluation actually scoreable. No
sentiment/urgency scoring — nothing in the support policy prices either, so
there'd be no way to check or act on the output. Full list with reasoning in
`README.md`.

### Anything you built or found that nobody asked for?

- **The goodwill-cap breach**: 37 of 42 goodwill credits exceed the policy's
  own Rs 500-per-ticket cap, worth ~Rs 3,000/quarter — small, but a clean,
  policy-documented, easily fixable leak nobody asked me to look for.
- **The leaderboard actually clears the fast-closers of the "they must be
  cutting corners" suspicion** — once you control for which team an agent
  sits in, closing more tickets correlates with *better* satisfaction, not
  worse. That's a genuinely useful, unrequested finding for whoever manages
  the leaderboard's reputation internally.
- **`breach_watchlist.csv`** — a ready-to-use, ticket-ID-linked list for
  Finance, not explicitly requested but the natural output of the business
  goal finding.

### What did you use AI for? Which tools and models, where they helped,
### where they wasted your time, what you threw away. Link your
### three-minute screen recording here.

Built with an AI coding assistant (Claude) for data inspection, the pipeline
code, and this documentation — logged honestly in `PROMPT_LOG.md`. Real,
measured use of Gemini (`gemini-flash-latest`) for ticket classification: 9
tickets succeeded before I hit a free-tier rate limit. Time genuinely lost:
diagnosing that rate limit (initially masked as generic call failures),
fixing a URL-construction bug that broke non-Anthropic providers, and a
second model (`gemini-2.5-flash-lite`) that returned 404s I didn't have time
to fully chase down — all logged with real error codes in `COST_LOG.md`,
not smoothed over. What I threw away: an earlier version of the
double-compensation metric that flagged 185 orders instead of 178 by
counting single replacements that cost more than a discounted order — caught
by a test, corrected before it reached this document.

Recording: **[paste your Google Drive video link here]**

### Your Public Google Drive Link

**[paste link here — upload the project zip or point to your GitHub repo,
plus the recording if not linked separately above]**

### Someone picks this up on Monday and you are unreachable. The three
### things they need to know.

1. **The business number is solid and ships as-is** — it's pure arithmetic,
   tested, and doesn't depend on anything unfinished. `breach_watchlist.csv`
   is ready for Finance today.
2. **The classifier needs one thing to go from MOCK to real: a working API
   key without a tight free-tier rate limit.** Run
   `python run.py --stage classify --mode live --eval-only` then
   `python evaluate.py --gold out/eval_sample_filled.csv` — takes under 10
   minutes and costs under a rupee. `gemini-flash-latest` is confirmed
   working; `gemini-2.5-flash-lite` returned 404s and needs checking against
   the account's enabled models first.
3. **Before this goes to Finance, ask Arjun one question**: whether these
   over-compensated orders are already being caught downstream in a system
   outside this export. If yes, the saving is smaller than stated — it's the
   single biggest unverified assumption in the goal calculation (`README.md`,
   limitation #5).

### Honest hours spent. One number.

**[fill in your own total — I can't see your real-world clock, especially
across the breaks you took. What's documented and measurable: ~4h15m of
active build time logged in TIME_LOG.md before the Gemini/rate-limit
debugging session. Add your own honest sense of everything since, including
setup, waiting on the 96-ticket runs, and the back-and-forth debugging.]**

### Github Repo Link

**[create a repo, push this project, paste the link here — see quick
commands below]**

---

## Quick commands if you haven't pushed to GitHub yet

```bash
cd vireo_digest
git init
git add .
git commit -m "Vireo Audio support digest and leaderboard"
```
Then create an empty repo on github.com (don't initialize it with a README),
and run the two commands it shows you, something like:
```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```
Your `.gitignore` already excludes `.env`, `out/cache/`, and
`out/llm_calls.jsonl` — so your API key and bulky generated files won't be
pushed. Double check `.env` isn't tracked with `git status` before you push.
