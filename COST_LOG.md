# COST LOG

What has actually been spent on this project so far. Where a figure has not
been measured it says so; nothing here is an estimate presented as a fact.

---

## Model and tool usage to date

| Tool | Purpose | Calls | Input tokens | Output tokens | Cost |
|---|---|---|---|---|---|
| Claude (this assistant) | Data inspection, verification, writing the tool | not separately metered | not measured | not measured | not measured — covered by an existing subscription, no per-call billing visible to me |
| Classifier LLM (`classify.py`, live mode) | Theme labelling of 11,875 tickets | **0** | **0** | **0** | **Rs 0 — no API key has been used in this project** |
| Classifier MOCK mode | Theme labelling, keyword fallback | 11,875 local calls | n/a | n/a | Rs 0 |

Every number in `out/metrics.json`, `out/digest.md` and `out/leaderboard.md`
was computed by pandas. None of them cost anything to produce and none of them
came from a model.

## Measured token usage

None. `out/llm_calls.jsonl` is the file that will hold it — one JSON line per
call with `input_tokens`, `output_tokens`, latency and outcome — and it does
not yet exist because no live call has been made.

## What a live run will cost

**Not yet measured.** What is known, from the data rather than from a price
list:

| Input | Measured value |
|---|---|
| Tickets to label | 11,875 |
| Mean `customer_message` length | 134 characters |
| Max `customer_message` length | 362 characters |
| System prompt (classify_v1 + injected taxonomy) | 2,089 characters |
| Calls per ticket | 1 (plus up to 2 retries on invalid output) |
| Re-runs | free — results cache to `out/cache/labels_classify_v1.parquet` |

To turn that into rupees you need the per-token price of whichever model is set
in `LLM_MODEL`, which is a published figure I have deliberately not written
down here because I have not verified it today and it changes. The honest
procedure, which costs about one rupee:

```bash
python run.py --stage classify --mode live --limit 20
python -c "
import json;rows=[json.loads(l) for l in open('out/llm_calls.jsonl')]
ok=[r for r in rows if r.get('ok')]
i=sum(r['input_tokens'] for r in ok);o=sum(r['output_tokens'] for r in ok)
print(f'{len(ok)} calls: {i} in, {o} out -> per ticket {i/len(ok):.0f} in / {o/len(ok):.0f} out')
print(f'projected for 11875: {i/len(ok)*11875:,.0f} in / {o/len(ok)*11875:,.0f} out')"
```

Multiply the projected totals by your model's published rate. Record the result
in this file as a measured figure, replacing this section.

## Billing shape

Arjun asked (8 Sep) for no per-ticket model bill that turns up as a surprise in
November. The design answer: labels are cached on disk keyed by ticket_id plus
prompt version, so the full corpus is paid for once. A weekly run thereafter
labels only that week's new tickets — roughly 150 on the observed mean, with a
range of 46 to 240 across the 79 weeks in the export.
