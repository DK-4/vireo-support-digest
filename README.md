# Vireo Audio — weekly support digest and agent leaderboard

Turns the 18-month ticket export into (a) a weekly digest of what customers are
complaining about, (b) an agent leaderboard, and (c) a weekly watchlist of
orders that were compensated for more than they cost, for Finance.

Numbers are computed in pandas and frozen to `out/metrics.json`. A language
model is used for exactly one thing: putting a theme label on a customer's free
text. It never sees, computes or emits a figure.

---

## Setup on a clean machine

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The five CSVs and the policy PDF are already in `data/`. No database, no
services, no API key needed to run the whole pipeline.

## Run it

```bash
python run.py --stage all          # clean -> classify -> eval sample -> report
```

Or a stage at a time:

| Command | What it does | Writes |
|---|---|---|
| `python run.py --stage clean` | Loads, validates enums, applies the three corrections, asserts the invariants | `out/tickets_clean.parquet`, `out/clean_report.json` |
| `python run.py --stage classify` | Theme labels. MOCK unless a key is set | `out/cache/labels_classify_v1.parquet` |
| `python run.py --stage eval-sample` | 96-ticket blind gold set, PII stripped | `out/eval_sample.csv` |
| `python run.py --stage report` | All metrics, digest, leaderboard, watchlist | `out/metrics.json`, `out/digest.md`, `out/digest.csv`, `out/leaderboard.md`, `out/breach_watchlist.csv` |

Tests:

```bash
python -m pytest tests/ -q          # 11 tests, ~1 second
```

## Running classification for real

Copy `.env.example` to `.env`, fill it in, and export it. Provider-agnostic —
anything with an OpenAI-compatible `/v1/chat/completions` or the Anthropic
`/v1/messages` endpoint works.

```bash
export LLM_PROVIDER=anthropic           # or: openai
export LLM_API_KEY=sk-...
export LLM_MODEL=<model string>
export LLM_BASE_URL=https://api.anthropic.com    # or any compatible host

python run.py --stage classify --mode live --limit 20   # measure cost first
python run.py --stage classify --mode live              # the full 11,875
python run.py --stage report
```

`--mode live` fails loudly rather than silently falling back to MOCK. Results
cache to `out/cache/labels_classify_v1.parquet` keyed by ticket_id + prompt
version, so re-runs are free and only new tickets are ever billed. Per-call
tokens and latency land in `out/llm_calls.jsonl`. See `COST_LOG.md` for how to
turn that into a rupee figure — it has not been measured yet and is not
guessed here.

## Producing and labelling the evaluation set

```bash
python run.py --stage eval-sample        # -> out/eval_sample.csv, 96 tickets
```

The file has three columns: `ticket_id`, `customer_message` (PII stripped) and
an empty `human_label`. It deliberately contains **no model prediction and no
bot category**, so labelling is blind. Every one of the 13 labels has at least
6 tickets; the row order is shuffled.

Fill `human_label` with one of the 13 labels exactly as printed by the command
(they are also listed in `vireo/config.py`), save as
`out/eval_sample_filled.csv`, then:

```bash
python evaluate.py --gold out/eval_sample_filled.csv
```

You get accuracy with a Wilson 95% interval, per-theme precision/recall/F1, the
top five confusions, schema-valid and invalid-output rates, and every
disagreement listed with its ticket ID. Rows left blank are reported and
skipped. A `human_label` outside the taxonomy stops the run rather than being
counted as wrong.

## Layout

```
vireo/config.py      policy constants and the taxonomy — every Rs figure traces to a section
vireo/load.py        CSV readers, pydantic row contract, enum validation
vireo/clean.py       the three corrections, each with a self-check
vireo/metrics.py     every number; writes the frozen metrics.json
vireo/classify.py    LLM client, schema, retries, cache, PII stripping, MOCK mode
vireo/report.py      digest and leaderboard, reading metrics.json only
run.py               pipeline entry point
evaluate.py          scores your gold labels against cached predictions
prompts/             classify_v1.txt, digest_v1.txt
tests/               11 tests
decisions.md         every judgement call, including the checks that came back clean
PROMPT_LOG.md        real prompt history only
COST_LOG.md          what has actually been spent (so far: nothing)
```

## MOCK mode

Without an API key the classifier falls back to keyword rules so the pipeline
runs end to end. Mock labels are tagged `label_source="MOCK"`, the digest
carries a block-quote warning and repeats "theme counts are MOCK" inline, and
`evaluate.py` warns too. Mock labels must never reach the memo. Volume, SLA,
repeat-contact, transfer and business-goal figures do not depend on labels and
are unaffected — the digest says so on the page.

## Deliberately out of scope

No web UI or dashboard (Priya, 7 Sep: "keep it simple, I don't need a
platform"). No database — five CSVs and 12k rows is a pandas problem. No
embeddings, clustering or topic modelling: a fixed taxonomy can be audited
against a gold set, clusters cannot. No fine-tuning. No multi-label
classification (see decisions.md D18 and PROMPT_LOG). No sentiment or urgency
scoring — the support policy prices neither, so there would be no way to check
or act on them. No real-time pipeline; the requirement is a weekly batch. No
Docker — a `requirements.txt` and `python run.py` clears "starts from a README
on a clean machine". No automated agent coaching or performance action: the
leaderboard's job here is to show why the requested metric should not be used
that way.

## Known limitations

1. **A replacement has no date or dispatch record.** `replacement_issued` is a
   Y/N flag an agent sets. There is no replacement order ID, no dispatch
   confirmation and no way to verify a unit actually shipped. The business goal
   leans on this flag; if it is set on tickets where nothing shipped, the
   saving shrinks. This is the weakest link in the chain.
2. **"Same issue" is undefined in policy §10.** Repeat-contact rate is 13.2%,
   29.3% or 34.4% depending on the reading. All three are in `metrics.json`;
   the conservative one is headline (decisions.md D7).
3. **720 tickets cannot be joined to a single order.** `order_id` is blank on
   4,023 tickets; the README's `customer_id` + `product_sku` fallback resolves
   3,303 uniquely and leaves 720 ambiguous. They are never assigned to a first
   match, so order-level figures slightly understate.
4. **Classifier accuracy is unknown.** No live run has been made. The gold set
   exists and is unlabelled. Nothing in the digest depends on labels except
   theme counts, which are currently MOCK.
5. **Finance recovery is invisible.** If over-compensated orders are already
   clawed back in a system outside this export, the headline saving is zero.
   One question to Arjun settles it and it should be asked before the memo.
6. **The window ends mid-week.** 30 Jun 2026 is a Tuesday. The part-week is
   excluded from every comparison (decisions.md D17).
7. **18 months is 6 quarters, not a forecast.** Per-quarter figures are the
   observed rate over the window divided by 5.97. They are not seasonally
   adjusted and the desk's volume is not flat across the window.
8. **`agents.csv` has one row per agent here, not per assignment.** No agent
   has changed team or site in this extract and every `to_date` is blank, so
   tenure-weighted metrics cannot be checked against a real roster change.

## What is in `out/` in this bundle

Produced by `python run.py --stage all --mode mock` on 21 Sep 2026.

| File | Note |
|---|---|
| `metrics.json` | Every number, frozen. The only numeric input `report.py` reads. |
| `digest.md` / `digest.csv` | Sample weekly digest. Theme counts are MOCK and are watermarked as such; all other figures are real. |
| `leaderboard.md` | Requested ranking and corrected ranking side by side, Tier 2 separate. Fully deterministic — no model involvement. |
| `breach_watchlist.csv` | The 178 over-compensated orders for Finance, worst first, with every ticket ID. |
| `eval_sample.csv` | 96 blind tickets for you to label. |
| `eval_sample_filled.csv`      | Your real, hand-labelled gold set (96 tickets, blind).                                          |
| `eval_report.md` / `.json`    | Real evaluation: 67.7% accuracy (95% CI 57.8–76.2%) — scores the MOCK keyword fallback, not a live model. Full confusion matrix inside. |
| `clean_report.json` | What the three corrections touched. |
| `tickets_clean.parquet` | Cleaned tickets, regenerable. |
