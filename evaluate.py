#!/usr/bin/env python3
"""Score the classifier against a human-labelled gold set.

    python evaluate.py --gold out/eval_sample_filled.csv

The gold file is the one YOU filled in. This script never labels anything; it
only compares your human_label column with the cached model predictions. That
separation is the point: the model is not allowed to mark its own homework.
"""
from __future__ import annotations

import argparse
import json
import math

import pandas as pd

from vireo import config


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval - correct near 0 and 1, unlike the normal approx."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def load_predictions(path=None) -> pd.DataFrame:
    path = path or config.CACHE / f"labels_{config.PROMPT_VERSION}.parquet"
    if not path.exists():
        raise SystemExit(f"no predictions at {path}; run `python run.py --stage classify` first")
    return pd.read_parquet(path)


def evaluate(gold: pd.DataFrame, pred: pd.DataFrame) -> dict:
    g = gold.copy()
    g["human_label"] = g.human_label.astype(str).str.strip()
    blank = g[g.human_label.isin(["", "nan", "None"])]
    g = g[~g.index.isin(blank.index)]

    unknown = sorted(set(g.human_label) - set(config.LABELS))
    if unknown:
        raise SystemExit(
            "human_label contains values outside the taxonomy:\n  "
            + "\n  ".join(unknown)
            + "\n\nAllowed labels:\n  " + "\n  ".join(config.LABELS))

    j = g.merge(pred, on="ticket_id", how="left", suffixes=("", "_pred"))
    missing_pred = j[j.theme.isna()]
    j = j[j.theme.notna()].copy()

    schema_valid = int((~j.label_source.astype(str).str.endswith(":FAILED")).sum())
    invalid = len(j) - schema_valid

    j["correct"] = j.human_label == j.theme
    n, k = len(j), int(j.correct.sum())
    lo, hi = wilson(k, n)

    per = []
    for lab in config.LABELS:
        tp = int(((j.theme == lab) & (j.human_label == lab)).sum())
        fp = int(((j.theme == lab) & (j.human_label != lab)).sum())
        fn = int(((j.theme != lab) & (j.human_label == lab)).sum())
        support = tp + fn
        if support == 0 and tp + fp == 0:
            continue
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / support if support else None
        f1 = (2 * prec * rec / (prec + rec)) if prec and rec else None
        per.append({"theme": lab, "support": support, "predicted": tp + fp,
                    "precision": round(prec, 3) if prec is not None else None,
                    "recall": round(rec, 3) if rec is not None else None,
                    "f1": round(f1, 3) if f1 is not None else None})

    conf = (j[~j.correct].groupby(["human_label", "theme"]).size()
            .reset_index(name="n").sort_values("n", ascending=False).head(5))

    return {
        "prompt_version": config.PROMPT_VERSION,
        "label_source": sorted(set(j.label_source.astype(str))),
        "labelled_by_human": n,
        "left_blank": len(blank),
        "no_prediction_found": len(missing_pred),
        "accuracy": round(k / n, 3) if n else None,
        "accuracy_ci95": [round(lo, 3), round(hi, 3)],
        "correct": k,
        "schema_valid_rate": round(schema_valid / n, 3) if n else None,
        "invalid_output_rate": round(invalid / n, 3) if n else None,
        "per_theme": per,
        "top_confusions": [
            {"human_said": r.human_label, "model_said": r.theme, "n": int(r.n)}
            for r in conf.itertuples()],
        "failures": [
            {"ticket_id": r.ticket_id, "human": r.human_label, "model": r.theme,
             "confidence": float(r.confidence) if pd.notna(r.confidence) else None,
             "evidence": str(r.evidence_phrase)[:80]}
            for r in j[~j.correct].itertuples()],
    }


def render(res: dict) -> str:
    L = [f"# Classifier evaluation - {res['prompt_version']}", ""]
    if any("MOCK" in s for s in res["label_source"]):
        L.append("> **MOCK PREDICTIONS.** Scored against the keyword fallback, "
                 "not a model. This number describes the fallback only.\n")
    lo, hi = res["accuracy_ci95"]
    L.append(f"**Accuracy {res['accuracy']:.1%}** "
             f"(95% CI {lo:.1%}-{hi:.1%}) on {res['labelled_by_human']} "
             f"human-labelled tickets.")
    L.append(f"Schema-valid {res['schema_valid_rate']:.1%}, "
             f"invalid output {res['invalid_output_rate']:.1%}. "
             f"Blank in gold file: {res['left_blank']}. "
             f"No prediction found: {res['no_prediction_found']}.")
    L += ["", "## Per theme", "",
          "| Theme | Support | Predicted | Precision | Recall | F1 |",
          "|---|---|---|---|---|---|"]
    for r in res["per_theme"]:
        f = lambda v: "-" if v is None else f"{v:.2f}"
        L.append(f"| {r['theme']} | {r['support']} | {r['predicted']} | "
                 f"{f(r['precision'])} | {f(r['recall'])} | {f(r['f1'])} |")
    L += ["", "## Top 5 confusions", ""]
    if res["top_confusions"]:
        L.append("| You labelled | Model said | n |")
        L.append("|---|---|---|")
        for c in res["top_confusions"]:
            L.append(f"| {c['human_said']} | {c['model_said']} | {c['n']} |")
    else:
        L.append("None.")
    L += ["", f"## Failures ({len(res['failures'])})", "",
          "| Ticket | You | Model | Conf | Model's evidence |", "|---|---|---|---|---|"]
    for f_ in res["failures"]:
        L.append(f"| {f_['ticket_id']} | {f_['human']} | {f_['model']} | "
                 f"{f_['confidence']} | {f_['evidence']} |")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, help="your filled eval_sample.csv")
    ap.add_argument("--pred", default=None, help="override predictions parquet")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    gold = pd.read_csv(a.gold, dtype=str).fillna("")
    if "human_label" not in gold.columns:
        raise SystemExit("gold file needs a human_label column")
    pred = load_predictions(a.pred)
    res = evaluate(gold, pred)

    out = a.out or (config.OUT / "eval_report.md")
    md = render(res)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    (config.OUT / "eval_report.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(md)
    print(f"\n-> written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
