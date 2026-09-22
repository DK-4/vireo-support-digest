"""Eight tests, one per thing that would silently corrupt a number.

Each uses a small hand-built frame so the expected answer is obvious by eye,
except the two that assert against the real export.
"""
import json

import pandas as pd
import pytest
from pydantic import ValidationError

from vireo import classify, clean, config, load, metrics


# ------------------------------------------------------------ fixtures
def _ticket(tid, src="helpdesk", resolved="2025-03-01 12:00", csat="5",
            created="2025-03-01 09:00", fr="2025-03-01 09:05", ch="chat",
            status="resolved", agent="A3001", cust="C100000", order="VR1",
            sku="VA-EB-PL1", cat="Audio Quality", team="Chat Frontline",
            transfers="0", refund="", code="", repl="N", msg="no sound"):
    return dict(ticket_id=tid, created_at=created, first_response_at=fr,
                resolved_at=resolved, status=status, channel=ch,
                customer_id=cust, order_id=order, product_sku=sku, category=cat,
                priority="Normal", assigned_team=team, agent_id=agent,
                transfers=transfers, csat_score=csat, refund_amount_inr=refund,
                refund_reason_code=code, replacement_issued=repl,
                customer_message=msg, agent_notes="note", source_system=src)


@pytest.fixture
def agents():
    return pd.DataFrame([
        dict(agent_id="A3001", name="A One", site="Indore", team="Chat Frontline",
             shift="Day", tier="1", from_date="2024-01-01", to_date=""),
        dict(agent_id="A3002", name="B Two", site="Indore",
             team="Escalations & Warranty", shift="Day", tier="2",
             from_date="2024-01-01", to_date=""),
    ])


# 1 --------------------------------------------------------------- dedupe
def test_dedupe_keeps_helpdesk_row_and_drops_the_legacy_twin():
    df = pd.DataFrame([
        _ticket("TK-1", src="helpdesk", resolved="2025-03-01 12:00", csat=""),
        _ticket("TK-1", src="legacy_fd", resolved="2025-03-01 06:30", csat="0"),
        _ticket("TK-2", src="legacy_fd"),
    ])
    out, rep = clean.dedupe_reimports(df)
    assert len(out) == 2
    assert rep["duplicate_ticket_ids"] == 1
    kept = out[out.ticket_id == "TK-1"].iloc[0]
    assert kept.source_system == "helpdesk"
    assert kept.resolved_at == "2025-03-01 12:00"


# 2 ------------------------------------------------------------ timezone
def test_legacy_resolved_at_is_shifted_by_five_and_a_half_hours():
    df = pd.DataFrame([
        _ticket("TK-1", src="legacy_fd", created="2025-03-01 09:00",
                resolved="2025-03-01 06:30"),                  # impossible as-is
        _ticket("TK-2", src="helpdesk", resolved="2025-03-01 12:00"),
    ])
    out, rep = clean.fix_legacy_timezone(df)
    assert rep["impossible_before"] == 1
    assert rep["impossible_after"] == 0
    assert str(out.loc[out.ticket_id == "TK-1", "resolved_at"].iloc[0]) == "2025-03-01 12:00:00"
    # helpdesk rows must be untouched
    assert str(out.loc[out.ticket_id == "TK-2", "resolved_at"].iloc[0]) == "2025-03-01 12:00:00"


def test_timezone_fix_raises_rather_than_shipping_impossible_timestamps():
    df = pd.DataFrame([_ticket("TK-1", src="helpdesk", created="2025-03-01 09:00",
                               resolved="2025-03-01 06:30")])
    with pytest.raises(AssertionError):
        clean.fix_legacy_timezone(df)


# 3 ---------------------------------------------------------------- csat
def test_csat_zero_becomes_null_and_moves_the_mean():
    df = pd.DataFrame([_ticket("TK-1", csat="0"), _ticket("TK-2", csat="4"),
                       _ticket("TK-3", csat="")])
    out, rep = clean.fix_csat(df)
    assert rep["zeros_nulled"] == 1
    assert out.csat.isna().sum() == 2
    assert rep["mean_corrected"] == 4.0
    assert rep["mean_if_zeros_kept"] == 2.0


# 4 ---------------------------------------------------- weekly aggregation
def test_weekly_buckets_and_week_over_week_change(agents):
    rows = ([_ticket(f"TK-A{i}", created="2025-03-03 09:00",
                     fr="2025-03-03 09:05", resolved="2025-03-03 10:00")
             for i in range(4)]
            + [_ticket(f"TK-B{i}", created="2025-03-10 09:00",
                       fr="2025-03-10 09:05", resolved="2025-03-10 10:00")
               for i in range(6)])
    rows += [_ticket(f"TK-C{i}", created="2025-03-17 09:00",
                     fr="2025-03-17 09:05", resolved="2025-03-17 10:00")
             for i in range(9)]
    df, _ = clean.run(pd.DataFrame(rows), agents)
    wk = metrics.weekly(df, None)
    w = wk["by_week"]
    assert [r["tickets"] for r in w] == [4, 6, 9]
    assert w[1]["wow_change_pct"] == 50.0
    # the export stops on 17 Mar, mid-week, so that week is partial and must
    # not be published as a week-over-week change
    assert w[0]["complete_week"] and w[1]["complete_week"]
    assert w[2]["complete_week"] is False
    assert w[2]["wow_change_pct"] is None
    assert wk["partial_final_week"] is True


# 5 ---------------------------------------------------- agent aggregation
def test_agent_rollup_never_fans_out_on_a_multi_assignment_roster(agents, tmp_path):
    """An agent with two roster rows must not double-count their tickets."""
    roster = pd.concat([agents, pd.DataFrame([
        dict(agent_id="A3001", name="A One", site="Bengaluru",
             team="Email Frontline", shift="Night", tier="1",
             from_date="2025-06-01", to_date="")])])
    p = tmp_path / "_agents.csv"
    roster.to_csv(p, index=False)
    collapsed = load.load_agents(str(p))
    assert collapsed.agent_id.is_unique
    assert collapsed.loc[collapsed.agent_id == "A3001", "team"].iloc[0] == "Email Frontline"

    rows = [_ticket(f"TK-{i}", agent="A3001") for i in range(5)]
    df, _ = clean.run(pd.DataFrame(rows), collapsed)
    lb = metrics.leaderboard(df, collapsed)
    assert sum(r["closed"] for r in lb["as_requested"]) == 5


# 6 ------------------------------------------------------ schema validation
def test_label_schema_accepts_valid_and_rejects_everything_else():
    ok = classify.Label(theme="Audio quality fault", confidence=0.9,
                        evidence_phrase="no sound from right earbud")
    assert ok.theme in config.LABELS

    with pytest.raises(ValidationError):          # label outside the taxonomy
        classify.Label(theme="Broken Headphones", confidence=0.9,
                       evidence_phrase="x")
    with pytest.raises(ValidationError):          # confidence out of range
        classify.Label(theme="Audio quality fault", confidence=1.7,
                       evidence_phrase="x")
    with pytest.raises(ValidationError):          # evidence is a quote, not an essay
        classify.Label(theme="Audio quality fault", confidence=0.5,
                       evidence_phrase="y" * 200)


# 7 ------------------------------------------- invalid LLM output handling
def test_bad_model_output_is_retried_then_recorded_as_failed(tmp_path, monkeypatch):
    calls = {"n": 0}

    def broken_post(self, system, user):
        calls["n"] += 1
        return "I think this is about audio, probably.", {"input_tokens": 10,
                                                          "output_tokens": 5}

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setattr(classify.LLMClient, "_post", broken_post)
    monkeypatch.setattr(classify.time, "sleep", lambda s: None)

    c = classify.LLMClient(log_path=tmp_path / "calls.jsonl")
    lab, info = c.label("sys", "usr", "TK-1", retries=3)
    assert lab is None                       # never coerced into a fake label
    assert calls["n"] == 3                   # retried the full budget
    logged = [json.loads(l) for l in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert len(logged) == 3 and not any(r["ok"] for r in logged)


def test_pii_is_stripped_before_anything_leaves_the_machine():
    msg = ("order VR892043 broke, call me on 9876543210 or "
           "a.khanna@example.com, claim RMA40980, ref TK-240001")
    out = classify.strip_pii(msg)
    for leak in ["VR892043", "9876543210", "a.khanna@example.com", "RMA40980",
                 "TK-240001"]:
        assert leak not in out
    assert "broke" in out                    # the signal survives


# 8 -------------------------------------------------- goal calculation
def test_over_compensation_needs_two_remedies_and_prices_the_excess(agents):
    orders = pd.DataFrame([
        dict(order_id="VR1", customer_id="C100000", sku="VA-EB-PL1",
             order_value_inr=2000),
        dict(order_id="VR2", customer_id="C100001", sku="VA-EB-PL1",
             order_value_inr=2000),
        dict(order_id="VR3", customer_id="C100002", sku="VA-EB-PL1",
             order_value_inr=1000),
    ])
    products = pd.DataFrame([dict(sku="VA-EB-PL1", unit_cost_inr=1120,
                                  product_name="Pulse")])
    rows = [
        # VR1: refunded twice at full value -> excess 2000, two remedies
        _ticket("TK-1", order="VR1", refund="2000", code="RETURN-QC-OK"),
        _ticket("TK-2", order="VR1", refund="2000", code="RETURN-QC-OK",
                cust="C100000"),
        # VR2: refund + replacement -> excess 2000 + 1460 - 2000
        _ticket("TK-3", order="VR2", refund="2000", code="DOA-REPL",
                repl="Y", cust="C100001"),
        # VR3: replacement only, costs more than the order sold for -> NOT a breach
        _ticket("TK-4", order="VR3", refund="", repl="Y", cust="C100002"),
    ]
    df, _ = clean.run(pd.DataFrame(rows), agents)
    g = metrics.overcompensation(df, orders, products, quarters=1.0)
    flagged = set(g.pop("_watchlist").order_id)
    assert flagged == {"VR1", "VR2"}, "single-remedy order must not be flagged"
    assert g["flagged_orders"] == 2
    # VR1 excess 2000; VR2 excess = 2000 + (1120+340) - 2000 = 1460
    assert g["excess_total_inr"] == 3460
    assert g["components"]["dual_remedy_orders"] == 1
    assert g["components"]["orders_refunded_more_than_once"] == 1


# --------------------------------------------- integration against real data
def test_real_export_survives_the_full_clean_with_its_invariants_intact():
    raw = load.load_all()
    df, rep = clean.run(raw["tickets"], raw["agents"])
    assert rep["dedupe"]["rows_before"] == 12528
    assert rep["dedupe"]["rows_after"] == 11875
    assert rep["timezone"]["impossible_before"] == 1874
    assert rep["timezone"]["impossible_after"] == 0
    assert rep["csat"]["response_rate_pct"] == pytest.approx(44.4, abs=0.5)
    assert df.ticket_id.is_unique
