"""Digest and leaderboard.

Everything here reads out/metrics.json. If a number is not in that file it does
not appear in the output. The LLM (when a key is present) is handed the frozen
JSON and asked for prose only; the deterministic writer below is the default
and is what runs in mock mode.
"""
from __future__ import annotations

import json

import pandas as pd

from . import config

MOCK_BANNER = (
    "> **MOCK LABELS - NOT FOR PUBLICATION.** Theme counts in this document were\n"
    "> produced by the offline keyword fallback, not a language model. They are\n"
    "> illustrative only and must not be quoted to the client or used in the memo.\n"
    "> Ticket volumes, SLA, repeat-contact, transfer and business-goal figures on\n"
    "> this page are computed deterministically and are unaffected.\n"
)


def _inr(n) -> str:
    if n is None:
        return "n/a"
    return f"Rs {int(round(float(n))):,}"


def _ex(ids) -> str:
    ids = [str(i) for i in (ids or [])][:3]
    return f" (e.g. {', '.join(ids)})" if ids else ""


# ----------------------------------------------------------------- digest
def digest_markdown(m: dict, mock: bool) -> str:
    w, v, g = m["window"], m["volume"], m["business_goal"]
    wk = m["weekly"]
    L: list[str] = []
    L.append("# Vireo Audio - weekly support digest")
    L.append(f"*Window {w['first_ticket'][:10]} to {w['last_ticket'][:10]} "
             f"({w['days']} days). Generated {m['generated_at_utc']}.*\n")
    if mock:
        L.append(MOCK_BANNER)

    L.append("## What changed this week")
    movers = wk.get("latest_week_movers") or []
    if movers:
        L.append(f"Week ending **{wk.get('latest_week')}**"
                 + (" — theme counts are MOCK" if mock else "") + ":\n")
        for mv in movers[:5]:
            d = mv["change_vs_prior_week"]
            arrow = "up" if d > 0 else ("down" if d < 0 else "flat")
            L.append(f"- **{mv['theme']}** — {int(mv['tickets'])} tickets, "
                     f"{arrow} {abs(int(d))} on the previous week"
                     f"{_ex(mv.get('examples'))}")
    else:
        L.append("- No theme labels available; run `--stage classify` first.")
    byw = [r for r in wk["by_week"] if r.get("complete_week", True)]
    if len(byw) >= 2:
        a, b = byw[-2], byw[-1]
        L.append(f"- Total volume **{b['tickets']}** tickets, against "
                 f"{a['tickets']} the week before "
                 f"({b['wow_change_pct']:+.1f}%).")
    if wk.get("partial_final_week"):
        L.append("- *The export ends mid-week, so the final part-week is "
                 "excluded from every comparison above.*")
    L.append("")

    L.append("## What it is costing")
    s = m["sla"]
    L.append(f"- **Missed first replies:** {s['breaches']} tickets "
             f"({s['rate_pct']}% of all tickets) missed the response target and "
             f"auto-issued a {_inr(s['credit_per_breach_inr'])} credit — "
             f"**{_inr(s['credits_per_quarter_inr'])} a quarter**"
             f"{_ex(s['examples'])}. Worst channel: "
             + max(s["by_channel"], key=lambda r: r["rate_pct"])["channel"]
             + f" at {max(s['by_channel'], key=lambda r: r['rate_pct'])['rate_pct']}%.")
    rc = m["repeat_contacts"]
    hd = rc["definitions"][rc["headline_definition"]]
    L.append(f"- **Customers coming back:** {hd['repeats']} resolved tickets "
             f"({hd['rate_pct']}%) were followed by the same customer contacting "
             f"again about the same category within {rc['window_days']} days — "
             f"**{_inr(hd['cost_per_quarter_inr'])} a quarter** in repeat "
             f"contacts{_ex(rc['examples'])}.")
    tr = m["transfers"]
    L.append(f"- **Tickets handed between teams:** {tr['transfers']} transfers at "
             f"{_inr(tr['cost_per_transfer_inr'])} each — "
             f"**{_inr(tr['cost_per_quarter_inr'])} a quarter**.")
    sv = g["saving_per_quarter_inr"]
    L.append(f"- **Orders compensated for more than they cost:** "
             f"{g['flagged_orders']} orders ({g['current_pct']}% of orders that "
             f"generated a ticket) received refunds plus replacements worth more "
             f"than the customer paid — **{_inr(g['excess_per_quarter_inr'])} a "
             f"quarter** of excess{_ex(g['examples'])}.")
    L.append("")

    L.append("## What I would do next")
    L.append(f"1. **Put the {g['flagged_orders']} over-compensated orders in front "
             f"of Finance weekly.** Policy section 5 already says a refund and a "
             f"replacement must never both be given for one order, and that "
             f"breaches go to Finance the same day. "
             f"{g['components']['dual_remedy_orders']} orders got both and "
             f"{g['components']['orders_refunded_more_than_once']} were refunded "
             f"more than once; almost all span several tickets weeks apart, which "
             f"is why nobody has caught them. Cutting this from {g['current_pct']}% to "
             f"{g['target_pct']}% of ticketed orders is worth about "
             f"{_inr(sv['low'])}-{_inr(sv['high'])} a quarter.")
    worst = max(s["by_channel"], key=lambda r: r["breaches"])
    L.append(f"2. **Fix first response on {worst['channel']}.** It accounts for "
             f"{worst['breaches']} of {s['breaches']} breaches "
             f"({worst['rate_pct']}% of its own volume against a "
             f"{worst['target_min']}-minute target).")
    top_rc = rc["by_category"][0]
    L.append(f"3. **Look at {top_rc['category']} repeat contacts.** "
             f"{top_rc['repeats']} of {top_rc['tickets']} resolved tickets in that "
             f"category came back within {rc['window_days']} days "
             f"({top_rc['rate_pct']}%), the highest of any category.")
    L.append("")
    L.append("---")
    L.append("*Every figure above is computed in code from the ticket export and "
             "the costs in support-policy.pdf v3.2. No figure on this page was "
             "produced by a language model.*")
    return "\n".join(L)


def digest_csv(m: dict) -> pd.DataFrame:
    rows = []
    for r in m["weekly"]["by_week"]:
        rows.append({"section": "volume", "key": r["week"],
                     "value": r["tickets"], "change_pct": r["wow_change_pct"]})
    for r in m["weekly"].get("by_week_theme", []):
        rows.append({"section": "theme_week", "key": f"{r['week']}|{r['theme']}",
                     "value": r["tickets"], "change_pct": None})
    for r in m["sla"]["by_channel"]:
        rows.append({"section": "sla", "key": r["channel"],
                     "value": r["breaches"], "change_pct": r["rate_pct"]})
    for r in m["repeat_contacts"]["by_category"]:
        rows.append({"section": "repeat", "key": r["category"],
                     "value": r["repeats"], "change_pct": r["rate_pct"]})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ leaderboard
def leaderboard_markdown(m: dict) -> str:
    lb = m["leaderboard"]
    L = ["# Agent leaderboard", ""]
    L.append("Two views of the same 18 months. Read them together: the left-hand "
             "ranking is the one that was asked for, the right-hand one is the "
             "one I would act on.\n")

    L.append("## 1. As requested - tickets closed per week")
    L.append("")
    L.append("| # | Agent | Team | Tier | Closed/week | Closed | Auto-closed | CSAT | SLA breach |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in lb["as_requested"]:
        L.append(f"| {r['rank']} | {r['name']} | {r['team']} | {r['tier']} | "
                 f"{r['closed_per_week']} | {r['closed']} | "
                 f"{r['auto_closed']} ({r['auto_closed_pct']}%) | {r['csat']} | "
                 f"{r['sla_breach_pct']}% |")
    L.append("")
    ev = lb["evidence"]
    tm = lb["team_means"]; ti = lb["tier_means"]
    L.append("### Why this ranking should not be used to judge people")
    L.append("")
    L.append(f"- **It ranks queues, not agents.** Mean tickets closed per week by "
             f"team: " + ", ".join(f"{k} {v}" for k, v in
                                   sorted(tm.items(), key=lambda x: -x[1])) + ".")
    L.append(f"- **Channel sets the ceiling.** Median handle time in minutes: "
             + ", ".join(f"{k} {int(v)}" for k, v in
                         sorted(ev["median_handle_min_by_channel"].items(),
                                key=lambda x: x[1])) + ". An email agent cannot "
             "out-close a chat agent.")
    L.append(f"- **It buries Tier 2 by design.** Tier 1 mean "
             f"{ti.get('1')}/week against Tier 2 mean {ti.get('2')}/week. "
             f"Tier 2 resolves {ev['tier2_share_of_warranty_tickets_pct']}% of all "
             "warranty tickets, and policy section 6 says explicitly that Tier 2 "
             "is measured on resolution days and is not to be compared with "
             "Tier 1 on volume.")
    L.append(f"- **Auto-closed tickets count as attendance** (policy section 8), "
             "so they are shown in their own column rather than folded into the "
             "total.")
    L.append(f"- Resolver's roster team matches the team the ticket was routed to "
             f"on {ev['resolver_team_matches_assigned_team_pct']}% of tickets.")
    L.append("")

    L.append("## 2. Corrected - ranked within team, Tier 1")
    L.append("")
    L.append("Composite = closed per week + CSAT + (inverted) SLA breach rate, each "
             "standardised **within the agent's own team** so queue mix cancels out.")
    L.append("")
    L.append("| Team | # in team | Agent | Closed/week | CSAT | SLA breach | Composite |")
    L.append("|---|---|---|---|---|---|---|")
    for r in lb["corrected_tier1"]:
        L.append(f"| {r['team']} | {r['team_rank']} | {r['name']} | "
                 f"{r['closed_per_week']} | {r['csat']} | {r['sla_breach_pct']}% | "
                 f"{r['composite']} |")
    L.append("")

    L.append("## 3. Tier 2 - shown separately (policy section 6)")
    L.append("")
    L.append("| Agent | Team | Median days to resolve | Closed/week | CSAT |")
    L.append("|---|---|---|---|---|")
    for r in lb["tier2_separate"]:
        L.append(f"| {r['name']} | {r['team']} | {r['median_resolution_days']} | "
                 f"{r['closed_per_week']} | {r['csat']} |")
    L.append("")
    L.append("*Tier 2 cases are multi-touch by design. Ranking them on weekly "
             "volume would be against policy and would misrepresent the team.*")
    return "\n".join(L)


# ------------------------------------------------------------------ write
def write_all(metrics_path=None, watchlist: pd.DataFrame | None = None,
              mock: bool = True) -> list:
    metrics_path = metrics_path or config.OUT / "metrics.json"
    m = json.loads(metrics_path.read_text(encoding="utf-8"))
    config.OUT.mkdir(parents=True, exist_ok=True)
    written = []

    p = config.OUT / "digest.md"
    p.write_text(digest_markdown(m, mock), encoding="utf-8")
    written.append(p)

    p = config.OUT / "digest.csv"
    digest_csv(m).to_csv(p, index=False, encoding="utf-8")
    written.append(p)

    p = config.OUT / "leaderboard.md"
    p.write_text(leaderboard_markdown(m), encoding="utf-8")
    written.append(p)

    if watchlist is not None:
        p = config.OUT / "breach_watchlist.csv"
        watchlist.to_csv(p, index=False, encoding="utf-8")
        written.append(p)
    return written
