"""The three corrections the raw export needs, each with a self-check.

B1  653 ticket_ids appear twice (one helpdesk row + one legacy_fd row from the
    Sep-2025 re-import). They are byte-identical except resolved_at and
    csat_score. Keep the helpdesk row.
B2  resolved_at on legacy_fd rows is UTC, not IST. Verified: on every dup pair
    the helpdesk value is exactly +5:30, and the fix takes impossible
    timestamps (resolved before created) from 1,874 to 0.
B3  csat_score 0 in legacy rows means "no response"; helpdesk uses blank.
    Policy s8 forbids treating a non-response as zero.

Nothing is ever dropped silently. Every fix reports what it touched.
"""
from __future__ import annotations

import pandas as pd

from . import config

TS_COLS = ["created_at", "first_response_at", "resolved_at"]


def dedupe_reimports(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """B1 - keep the helpdesk copy of re-imported legacy tickets."""
    before = len(df)
    dup_ids = df.ticket_id[df.ticket_id.duplicated()].unique()
    df = df.copy()
    df["_pref"] = (df.source_system == "helpdesk").astype(int)
    df = (df.sort_values(["ticket_id", "_pref"], ascending=[True, False])
            .drop_duplicates("ticket_id", keep="first")
            .drop(columns="_pref"))
    return df, {"rows_before": before, "rows_after": len(df),
                "duplicate_ticket_ids": int(len(dup_ids))}


def fix_legacy_timezone(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """B2 - shift legacy resolved_at from UTC to IST."""
    df = df.copy()
    for c in TS_COLS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    impossible_before = int((df.resolved_at < df.created_at).sum())
    mask = df.source_system == "legacy_fd"
    df.loc[mask, "resolved_at"] = df.loc[mask, "resolved_at"] + pd.Timedelta(
        hours=config.LEGACY_UTC_OFFSET_HOURS)
    impossible_after = int((df.resolved_at < df.created_at).sum())
    if impossible_after:
        raise AssertionError(
            f"timezone fix left {impossible_after} tickets resolved before creation")
    return df, {"rows_shifted": int(mask.sum()),
                "impossible_before": impossible_before,
                "impossible_after": impossible_after}


def fix_csat(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """B3 - legacy csat 0 means no response."""
    df = df.copy()
    raw = pd.to_numeric(df.csat_score, errors="coerce")
    df["csat"] = raw.replace(0, pd.NA).astype("Float64")
    zeros = int((raw == 0).sum())
    return df, {"zeros_nulled": zeros,
                "mean_if_zeros_kept": round(float(raw.mean()), 3),
                "mean_corrected": round(float(df.csat.mean()), 3),
                "response_rate_pct": round(float(df.csat.notna().mean() * 100), 1)}


def derive(df: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    """Columns every metric depends on. Pure arithmetic, no judgement."""
    df = df.copy()
    df["transfers_n"] = pd.to_numeric(df.transfers)
    df["refund_inr"] = pd.to_numeric(df.refund_amount_inr, errors="coerce")
    df["replacement"] = df.replacement_issued.eq("Y")
    df["frt_min"] = (df.first_response_at - df.created_at).dt.total_seconds() / 60
    df["sla_target_min"] = df.channel.map(config.SLA_TARGET_MIN)
    df["sla_breach"] = df.frt_min > df.sla_target_min
    df["handle_min"] = (df.resolved_at - df.first_response_at).dt.total_seconds() / 60
    df["attendance"] = df.status.isin(["resolved", "closed"])   # policy s10
    df["auto_closed"] = df.status.eq("closed")                  # policy s8
    df["contact_cost"] = df.channel.map(config.CONTACT_COST)
    df["week"] = df.created_at.dt.to_period("W-SUN").astype(str)
    df["resolved_week"] = df.resolved_at.dt.to_period("W-SUN").astype(str)
    a = agents.set_index("agent_id")
    df["agent_name"] = df.agent_id.map(a["name"])
    df["agent_team"] = df.agent_id.map(a["team"])
    df["agent_tier"] = df.agent_id.map(a["tier"])
    df["agent_site"] = df.agent_id.map(a["site"])
    return df


def run(tickets: pd.DataFrame, agents: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {}
    df, report["dedupe"] = dedupe_reimports(tickets)
    df, report["timezone"] = fix_legacy_timezone(df)
    df, report["csat"] = fix_csat(df)
    df = derive(df, agents)

    # integrity assertions - these are the invariants the rest of the tool trusts
    assert df.ticket_id.is_unique, "ticket_id not unique after dedupe"
    assert not (df.resolved_at < df.created_at).any()
    assert not (df.resolved_at < df.first_response_at).any()
    assert not ((df.csat == 0).fillna(False)).any(), "csat 0 survived the fix"
    open_with_csat = int(df.loc[~df.attendance, "csat"].notna().sum())
    report["anomalies"] = {
        "open_or_pending_with_csat": open_with_csat,
        "note": "policy s8 surveys on resolution; these are excluded from CSAT",
    }
    return df, report
