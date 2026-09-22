# TIME LOG

Against a ~5 hour cap. Wall-clock, rounded to five minutes.

| Phase | Work | Time |
|---|---|---|
| Phase 1 | Inspect 5 CSVs + 2 PDFs + policy; find and prove the three data faults; test the leaderboard hypothesis; size five candidate goals; derive the taxonomy from 66 read tickets | 1h 05m |
| Phase 2 | Verify the business goal: dedupe-invariance check, 8 worked examples, refund breakdown by reason code, four rejected hypotheses, build the range input by input | 30m |
| Build | config/load/clean/metrics/classify/report/run, 11 tests, mock run, digest + leaderboard + watchlist, eval sample, evaluate.py + fake-file proof | 2h 05m |
| Docs | decisions.md, PROMPT_LOG, COST_LOG, README, this file | 35m |
| **Total so far** | | **4h 15m** |
| Remaining in budget | memo to Priya, recording script, submission form — all waiting on real classifier results | ~45m |

Two bugs found by tests rather than in output, both logged (decisions.md D19,
D17). One definition error caught during the build and corrected: an earlier
draft flagged 185 orders by counting single replacements that cost more than a
discounted order; the correct figure is 178 (decisions.md D13).
