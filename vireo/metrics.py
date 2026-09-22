"""Every number the digest, leaderboard and memo can quote.

Nothing here calls a model. The output of `build()` is frozen to
out/metrics.json and is the ONLY numeric input report.py is allowed to use.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config


def _q(df: pd.DataFrame) -> float:
    """Quarters covered by the ticket window, for per-quarter rates."""
    span = (df.created_at.max() - df.created_at.min()).days
    return span / 91.25


def _ex(s, n=3) -> list:
    return list(pd.Series(s).astype(str).head(n))


# ---------------------------------------------------------------- SLA
def sla(df: pd.DataFrame, quarters: float) -> dict:
    by = df.groupby("channel").agg(
        tickets=("sla_breach", "size"), breaches=("sla_breach", "sum"),
        median_frt_min=("frt_min", "median"))
    by["rate_pct"] = (by.breaches / by.tickets * 100).round(1)
    by["target_min"] = [config.SLA_TARGET_MIN[c] for c in by.index]
    total = int(df.sla_breach.sum())
    return {
        "breaches": total,
        "rate_pct": round(float(df.sla_breach.mean() * 100), 1),
        "credit_per_breach_inr": config.SLA_BREACH_CREDIT,
        "credits_total_inr": total * config.SLA_BREACH_CREDIT,
        "credits_per_quarter_inr": round(total * config.SLA_BREACH_CREDIT / quarters),
        "by_channel": by.reset_index().to_dict("records"),
        "examples": _ex(df.loc[df.sla_breach, "ticket_id"]),
        "policy": "s3 - Rs 350 credit per missed first-response target",
    }


# ------------------------------------------------------- repeat contacts
def repeat_contacts(df: pd.DataFrame, quarters: float) -> dict:
    """Policy s10: same customer contacts again about the same issue <=30d
    after resolution. 'Same issue' is undefined in the policy, so all three
    readings are reported and the conservative one is headline (D7)."""
    res = df[df.resolved_at.notna()].copy()
    contacts = (df[["customer_id", "created_at", "category", "product_sku",
                    "ticket_id"]]
                .sort_values("created_at"))
    by_cust = {c: g for c, g in contacts.groupby("customer_id")}
    win = pd.Timedelta(days=config.REPEAT_WINDOW_DAYS)

    flags = {"any": [], "same_category": [], "same_product": []}
    for r in res.itertuples():
        g = by_cust[r.customer_id]
        m = ((g.created_at > r.resolved_at) & (g.created_at <= r.resolved_at + win)
             & (g.ticket_id != r.ticket_id))
        nxt = g[m]
        flags["any"].append(len(nxt) > 0)
        flags["same_category"].append(bool((nxt.category == r.category).any()))
        flags["same_product"].append(bool((nxt.product_sku == r.product_sku).any()))
    for k, v in flags.items():
        res["rp_" + k] = v

    out = {"resolved_tickets": len(res), "window_days": config.REPEAT_WINDOW_DAYS,
           "headline_definition": "same_category", "definitions": {}}
    for k in flags:
        n = int(res["rp_" + k].sum())
        out["definitions"][k] = {
            "repeats": n,
            "rate_pct": round(n / len(res) * 100, 1),
            "cost_per_quarter_inr": round(n * config.BLENDED_CONTACT_COST / quarters),
        }
    out["by_category"] = (res.groupby("category")
                          .agg(tickets=("rp_same_category", "size"),
                               repeats=("rp_same_category", "sum"))
                          .assign(rate_pct=lambda d: (d.repeats / d.tickets * 100).round(1))
                          .sort_values("rate_pct", ascending=False)
                          .reset_index().to_dict("records"))
    out["examples"] = _ex(res.loc[res.rp_same_category, "ticket_id"])
    out["_frame"] = res[["ticket_id", "rp_same_category"]]
    return out


# ------------------------------------------------------------ transfers
def transfers(df: pd.DataFrame, quarters: float) -> dict:
    n = int(df.transfers_n.sum())
    by = (df.groupby("category")
          .agg(tickets=("transfers_n", "size"),
               transfers=("transfers_n", "sum"))
          .assign(rate_pct=lambda d: (d.transfers / d.tickets * 100).round(1))
          .sort_values("rate_pct", ascending=False).reset_index())
    return {
        "transfers": n,
        "tickets_with_transfer": int((df.transfers_n > 0).sum()),
        "cost_per_transfer_inr": config.TRANSFER_COST,
        "cost_total_inr": n * config.TRANSFER_COST,
        "cost_per_quarter_inr": round(n * config.TRANSFER_COST / quarters),
        "by_category": by.to_dict("records"),
        "policy": "s4 - Rs 305 per internal transfer",
    }


# -------------------------------------------------- business goal + watchlist
def overcompensation(df: pd.DataFrame, orders: pd.DataFrame,
                     products: pd.DataFrame, quarters: float) -> dict:
    """Business goal (D13).

    An order is OVER-COMPENSATED when the money and goods returned to the
    customer exceed what they paid for that order:
        total_compensation = sum(refunds on the order)
                           + (unit_cost + Rs 340) if any replacement issued
        excess = max(0, total_compensation - order_value_inr)

    This is arithmetic, not judgement: a customer cannot be owed more than
    they paid. It is a strict superset of the policy s5 breach ("in no case
    is a customer to receive both a refund and a replacement for the same
    order") and it also catches the same order being refunded twice.
    """
    oo = df[df.order_id.notna()]
    g = oo.groupby("order_id").agg(
        refund_sum=("refund_inr", "sum"),
        refund_count=("refund_inr", "count"),
        any_replacement=("replacement", "any"),
        tickets=("ticket_id", "size"),
        ticket_ids=("ticket_id", lambda s: "|".join(s)),
        codes=("refund_reason_code", lambda s: "|".join(sorted(set(s.dropna())))),
        first_contact=("created_at", "min"),
        last_contact=("created_at", "max"),
    )
    g = (g.join(orders.set_index("order_id")[["order_value_inr", "sku", "customer_id"]])
           .join(products.set_index("sku")[["unit_cost_inr", "product_name"]], on="sku"))
    g["replacement_cost"] = (g.unit_cost_inr + config.REPLACEMENT_LOGISTICS) * g.any_replacement
    g["total_compensation"] = g.refund_sum + g.replacement_cost
    g["excess_inr"] = (g.total_compensation - g.order_value_inr).clip(lower=0)

    # A single remedy is never a breach, even if it costs more than the order
    # was sold for (discounted sale, unit_cost + Rs 340 can exceed sale price).
    # Only orders given MORE THAN ONE remedy can be over-compensated.
    g["remedies"] = g.refund_count + g.any_replacement.astype(int)
    ticketed = int(df.order_id.nunique())
    flagged = (g[(g.excess_inr > 0) & (g.remedies > 1)]
               .sort_values("excess_inr", ascending=False))
    dual = g[(g.refund_sum > 0) & (g.any_replacement)]
    multi_refund = g[g.refund_count > 1]

    # goodwill cap breach, policy s5: Rs 500 per ticket
    gw = df[df.refund_reason_code == "GW-OTHER"]
    gw_excess = float((gw.refund_inr - config.GOODWILL_CAP).clip(lower=0).sum())

    cur = len(flagged) / ticketed * 100
    tgt = config.GOAL_TARGET_PCT
    excess_q = float(flagged.excess_inr.sum()) / quarters
    reduction = (cur - tgt) / cur if cur else 0
    # Range: low = only the arithmetically unarguable refund-side excess;
    # high = that plus replacement-side excess plus goodwill cap enforcement.
    multi_ref = g[g.refund_count > 1]
    refund_only_excess = float(
        (multi_ref.refund_sum - multi_ref.order_value_inr).clip(lower=0).sum()) / quarters
    saving_low = round(refund_only_excess * reduction)
    saving_mid = round(excess_q * reduction)
    saving_high = round((excess_q + gw_excess / quarters) * reduction)

    watch_cols = ["tickets", "ticket_ids", "codes", "refund_sum", "any_replacement",
                  "order_value_inr", "excess_inr", "first_contact", "last_contact",
                  "product_name"]
    return {
        "ticketed_orders": ticketed,
        "flagged_orders": len(flagged),
        "current_pct": round(cur, 2),
        "target_pct": tgt,
        "orders_per_quarter": round(len(flagged) / quarters, 1),
        "excess_total_inr": round(float(flagged.excess_inr.sum())),
        "excess_per_quarter_inr": round(excess_q),
        "saving_per_quarter_inr": {"low": saving_low, "mid": saving_mid,
                                   "high": saving_high},
        "components": {
            "dual_remedy_orders": len(dual),
            "orders_refunded_more_than_once": len(multi_refund),
            "orders_refunded_more_than_once_in_excess": int(len(multi_ref[multi_ref.refund_sum > multi_ref.order_value_inr])),
            "refund_excess_per_quarter_inr": round(refund_only_excess),
            "replacement_driven_excess_per_quarter_inr": round(
                excess_q - refund_only_excess),
            "goodwill_over_cap_per_quarter_inr": round(gw_excess / quarters),
            "goodwill_tickets_over_cap": int((gw.refund_inr > config.GOODWILL_CAP).sum()),
        },
        "examples": _ex(flagged.index),
        "policy": "s5 - no refund AND replacement for the same order; "
                  "goodwill capped at Rs 500 per ticket",
        "_watchlist": flagged[watch_cols].reset_index(),
    }


# ---------------------------------------------------------- leaderboard
def leaderboard(df: pd.DataFrame, agents: pd.DataFrame) -> dict:
    """Two views, side by side.

    'as_requested' is exactly what Priya asked for: tickets closed per week.
    'corrected' ranks within team and tier, because the raw metric is mostly a
    measure of which queue an agent sits in (see decisions.md D9).
    """
    att = df[df.attendance & df.resolved_at.notna()]
    wk = att.groupby(["agent_id", "resolved_week"]).size().reset_index(name="n")
    per = wk.groupby("agent_id").agg(active_weeks=("resolved_week", "nunique"),
                                     closed=("n", "sum"))
    per["closed_per_week"] = (per.closed / per.active_weeks).round(2)
    per["auto_closed"] = att.groupby("agent_id").auto_closed.sum()
    per["auto_closed_pct"] = (per.auto_closed / per.closed * 100).round(1)
    per["csat"] = att.groupby("agent_id").csat.mean().round(2)
    per["csat_responses"] = att.groupby("agent_id").csat.count()
    per["sla_breach_pct"] = (df.groupby("agent_id").sla_breach.mean() * 100).round(1)
    a = agents.set_index("agent_id")
    per = per.join(a[["name", "team", "tier", "site", "shift"]])

    as_req = per.sort_values("closed_per_week", ascending=False).copy()
    as_req["rank"] = range(1, len(as_req) + 1)

    def _z(s, invert=False):
        """Standardise within a team. A one-agent team has no spread, so its
        z-score is 0 rather than NaN - otherwise a single-agent team crashes
        or silently drops out of the ranking."""
        sd = s.astype("float64").std()
        if pd.isna(sd) or sd == 0:
            return pd.Series(0.0, index=s.index)
        z = (s.astype("float64") - s.astype("float64").mean()) / sd
        return -z if invert else z

    t1 = per[per.tier == "1"].copy()
    for c in ["closed_per_week", "csat"]:
        t1[c + "_z"] = t1.groupby("team")[c].transform(_z)
    t1["sla_z"] = t1.groupby("team").sla_breach_pct.transform(_z, invert=True)
    t1["composite"] = (t1.closed_per_week_z.fillna(0) + t1.csat_z.fillna(0)
                       + t1.sla_z.fillna(0)).round(2)
    t1["team_rank"] = t1.groupby("team").composite.rank(ascending=False).astype(int)
    corrected = t1.sort_values(["team", "team_rank"])

    t2 = per[per.tier == "2"].copy()
    # policy s6: Tier 2 is measured on resolution days, not weekly volume
    t2d = df[(df.agent_tier == "2") & df.resolved_at.notna()]
    t2["median_resolution_days"] = (
        (t2d.resolved_at - t2d.created_at).dt.total_seconds() / 86400
    ).groupby(t2d.agent_id).median().round(2)

    cols = ["name", "team", "tier", "closed_per_week", "closed", "active_weeks",
            "auto_closed", "auto_closed_pct", "csat", "csat_responses",
            "sla_breach_pct"]
    return {
        "as_requested": as_req.reset_index()[["rank", "agent_id"] + cols].to_dict("records"),
        "corrected_tier1": corrected.reset_index()[
            ["agent_id", "team_rank"] + cols + ["composite"]].to_dict("records"),
        "tier2_separate": t2.reset_index()[
            ["agent_id", "name", "team", "closed_per_week", "closed",
             "median_resolution_days", "csat"]].to_dict("records"),
        "team_means": per.groupby("team").closed_per_week.mean().round(2).to_dict(),
        "tier_means": per.groupby("tier").closed_per_week.mean().round(2).to_dict(),
        "evidence": {
            "note": "raw ranking is confounded by team and channel; see decisions.md D9",
            "median_handle_min_by_channel": df.groupby("channel").handle_min.median().round(0).to_dict(),
            "tier2_share_of_warranty_tickets_pct": round(float(
                (df[df.category == "Warranty & Repair"].agent_tier == "2").mean() * 100), 1),
            "resolver_team_matches_assigned_team_pct": round(float(
                (df.agent_team == df.assigned_team).mean() * 100), 1),
        },
    }


# --------------------------------------------------------- weekly volume
def weekly(df: pd.DataFrame, labels: pd.DataFrame | None) -> dict:
    # The export ends mid-week. A partial week must never be compared with a
    # full one - it reads as a collapse in volume that did not happen.
    last_ts = df.created_at.max()
    periods = df.created_at.dt.to_period("W-SUN")
    complete = {str(p): bool(p.end_time <= last_ts) for p in periods.unique()}

    vol = df.groupby("week").size().reset_index(name="tickets")
    vol["complete_week"] = vol.week.map(complete)
    vol["wow_change_pct"] = (vol.tickets.pct_change() * 100).round(1)
    vol["wow_change_pct"] = vol.wow_change_pct.astype(object).where(
        vol.complete_week & vol.wow_change_pct.notna(), None)
    out = {"by_week": vol.to_dict("records"),
           "partial_final_week": not vol.complete_week.iloc[-1],
           "by_week_product": (df.groupby(["week", "product_sku"]).size()
                               .reset_index(name="tickets").to_dict("records")),
           "themes_available": labels is not None}
    if labels is None:
        out["by_week_theme"] = []
        out["theme_totals"] = []
        return out
    j = df.merge(labels, on="ticket_id", how="left")
    out["label_source"] = str(j.label_source.mode().iloc[0]) if "label_source" in j else "unknown"
    tw = j.groupby(["week", "theme"]).size().reset_index(name="tickets")
    piv = tw.pivot(index="week", columns="theme", values="tickets").fillna(0)
    wow = piv.diff()
    full = [w for w in piv.index if complete.get(w, False)]
    last = full[-1] if full else (piv.index[-1] if len(piv) else None)
    out["by_week_theme"] = tw.to_dict("records")
    out["theme_totals"] = (j.theme.value_counts().rename_axis("theme")
                           .reset_index(name="tickets").to_dict("records"))
    out["latest_week"] = str(last)
    if last is not None:
        mv = wow.loc[last].sort_values(ascending=False)
        out["latest_week_movers"] = [
            {"theme": k, "change_vs_prior_week": float(v),
             "tickets": float(piv.loc[last, k]),
             "examples": _ex(j[(j.week == last) & (j.theme == k)].ticket_id)}
            for k, v in mv.items()]
    out["theme_by_product"] = (j.groupby(["theme", "product_sku"]).size()
                               .reset_index(name="tickets").to_dict("records"))
    return out


# ------------------------------------------------------------------ build
def build(df: pd.DataFrame, agents, orders, products,
          labels: pd.DataFrame | None = None) -> dict:
    quarters = _q(df)
    rc = repeat_contacts(df, quarters)
    rc.pop("_frame", None)
    goal = overcompensation(df, orders, products, quarters)
    watch = goal.pop("_watchlist")
    m = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": {"first_ticket": str(df.created_at.min()),
                   "last_ticket": str(df.created_at.max()),
                   "days": int((df.created_at.max() - df.created_at.min()).days),
                   "quarters": round(quarters, 2)},
        "volume": {"tickets": len(df),
                   "per_quarter": round(len(df) / quarters),
                   "attendance": int(df.attendance.sum()),
                   "auto_closed": int(df.auto_closed.sum()),
                   "open_or_pending": int((~df.attendance).sum()),
                   "by_channel": df.channel.value_counts().to_dict(),
                   "contact_cost_total_inr": int(df.contact_cost.sum()),
                   "contact_cost_per_quarter_inr": round(float(df.contact_cost.sum()) / quarters)},
        "csat": {"mean": round(float(df.loc[df.attendance, "csat"].mean()), 2),
                 "responses": int(df.loc[df.attendance, "csat"].count()),
                 "response_rate_pct": round(float(
                     df.loc[df.attendance, "csat"].notna().mean() * 100), 1)},
        "sla": sla(df, quarters),
        "repeat_contacts": rc,
        "transfers": transfers(df, quarters),
        "business_goal": goal,
        "leaderboard": leaderboard(df, agents),
        "weekly": weekly(df, labels),
    }
    return m, watch


def freeze(metrics: dict, path=None) -> None:
    path = path or config.OUT / "metrics.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (pd.Timestamp, pd.Period)):
            return str(o)
        if o is pd.NaT or o is pd.NA:
            return None
        return str(o)

    path.write_text(json.dumps(metrics, indent=2, default=default), encoding="utf-8")
