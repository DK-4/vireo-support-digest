#!/usr/bin/env python3
"""Vireo support digest pipeline.

    python run.py --stage clean          # load + fix + report what was fixed
    python run.py --stage classify       # theme labels (MOCK without a key)
    python run.py --stage eval-sample    # build eval_sample.csv for blind labelling
    python run.py --stage report         # metrics.json + digest + leaderboard
    python run.py --stage all
"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from vireo import classify, clean, config, load, metrics, report


def stage_clean(verbose=True):
    raw = load.load_all()
    df, rep = clean.run(raw["tickets"], raw["agents"])
    config.OUT.mkdir(parents=True, exist_ok=True)
    (config.OUT / "clean_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    df.to_parquet(config.OUT / "tickets_clean.parquet", index=False)
    if verbose:
        print(json.dumps(rep, indent=2))
        print(f"\n-> {len(df):,} clean tickets written to out/tickets_clean.parquet")
    return df, raw


def _clean_or_load():
    p = config.OUT / "tickets_clean.parquet"
    raw = load.load_all()
    if p.exists():
        return pd.read_parquet(p), raw
    return stage_clean(verbose=False)


def stage_classify(mode="auto", limit=None, eval_only=False):
    df, _ = _clean_or_load()
    if eval_only:
        p = config.OUT / "eval_sample.csv"
        if not p.exists():
            raise SystemExit(
                "no out/eval_sample.csv - run `python run.py --stage eval-sample` first")
        ids = pd.read_csv(p, dtype=str).ticket_id
        before = len(df)
        df = df[df.ticket_id.isin(ids)]
        print(f"--eval-only: restricting classification to the {len(df)} gold-set "
              f"tickets (out of {before} total) - this is the cheap validation run")
    labels = classify.run(df, mode=mode, limit=limit)
    src = labels.label_source.value_counts().to_dict()
    print(f"labelled {len(labels):,} tickets")
    print("label_source:", src)
    if labels.attrs.get("mock"):
        print("\n!! MOCK MODE: keyword fallback, not a model. "
              "These labels must not feed the memo.")
    print("\ntheme distribution:")
    print(labels.theme.value_counts().to_string())
    return labels


def stage_eval_sample(n=96, min_per_theme=6, seed=20260921):
    df, _ = _clean_or_load()
    labels = classify.run(df, mode="auto")
    j = df.merge(labels[["ticket_id", "theme"]], on="ticket_id", how="left")
    parts, rng = [], seed
    for theme in config.LABELS:
        pool = j[j.theme == theme]
        if len(pool):
            parts.append(pool.sample(min(len(pool), min_per_theme),
                                     random_state=rng))
    got = pd.concat(parts)
    remaining = n - len(got)
    if remaining > 0:
        rest = j[~j.ticket_id.isin(got.ticket_id)].sample(remaining, random_state=rng)
        got = pd.concat([got, rest])
    got = got.sample(frac=1, random_state=rng)          # shuffle so order leaks nothing
    out = pd.DataFrame({
        "ticket_id": got.ticket_id.values,
        "customer_message": [classify.strip_pii(x) for x in got.customer_message],
        "human_label": "",
    })
    p = config.OUT / "eval_sample.csv"
    out.to_csv(p, index=False, encoding="utf-8")
    print(f"-> {len(out)} tickets written to {p}")
    print("   columns:", list(out.columns), "(no model prediction, no bot category)")
    print("\nlabel options to paste into human_label:")
    for lab in config.LABELS:
        print("   -", lab)
    return out


def stage_report(mock_hint=None):
    df, raw = _clean_or_load()
    lp = config.CACHE / f"labels_{config.PROMPT_VERSION}.parquet"
    labels = pd.read_parquet(lp) if lp.exists() else None
    mock = bool(labels is not None and (labels.label_source == "MOCK").any())
    if mock_hint is not None:
        mock = mock_hint
    m, watch = metrics.build(df, raw["agents"], raw["orders"], raw["products"],
                             labels)
    m["label_provenance"] = ("MOCK - keyword fallback" if mock
                             else (labels.label_source.mode().iloc[0]
                                   if labels is not None else "none"))
    metrics.freeze(m)
    written = report.write_all(watchlist=watch, mock=mock)
    print("wrote:")
    for p in [config.OUT / "metrics.json"] + written:
        print("  ", p.relative_to(config.ROOT))
    g = m["business_goal"]
    print(f"\nbusiness goal: {g['flagged_orders']} of {g['ticketed_orders']} "
          f"ticketed orders over-compensated = {g['current_pct']}%, "
          f"excess Rs {g['excess_per_quarter_inr']:,}/quarter")
    return m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["clean", "classify", "eval-sample", "report", "all"])
    ap.add_argument("--mode", default="auto", choices=["auto", "mock", "live"],
                    help="classify: force mock or require a real key")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--eval-only", action="store_true",
                    help="classify (with --stage classify) only the tickets already "
                         "in out/eval_sample.csv - the cheap way to get a real "
                         "accuracy number without paying for the full corpus")
    a = ap.parse_args(argv)
    if a.stage == "clean":
        stage_clean()
    elif a.stage == "classify":
        stage_classify(a.mode, a.limit, a.eval_only)
    elif a.stage == "eval-sample":
        stage_eval_sample()
    elif a.stage == "report":
        stage_report()
    else:
        stage_clean()
        stage_classify(a.mode, a.limit)
        stage_eval_sample()
        stage_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
