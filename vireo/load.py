"""Read the five CSVs and validate shape / enums.

Validation is deliberately loud: if an unexpected categorical value appears in
a future export we want the run to fail, not to silently drop rows.
"""
from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from . import config

TICKET_COLS = [
    "ticket_id", "created_at", "first_response_at", "resolved_at", "status",
    "channel", "customer_id", "order_id", "product_sku", "category", "priority",
    "assigned_team", "agent_id", "transfers", "csat_score", "refund_amount_inr",
    "refund_reason_code", "replacement_issued", "customer_message",
    "agent_notes", "source_system",
]

ENUMS = {
    "status": {"resolved", "closed", "open", "pending"},
    "channel": {"chat", "email", "voice", "social"},
    "priority": {"Low", "Normal", "High"},
    "source_system": {"helpdesk", "legacy_fd"},
    "replacement_issued": {"Y", "N"},
}


class TicketRow(BaseModel):
    """Row-level contract. Used by tests and by the enum sweep below."""
    ticket_id: str
    status: str
    channel: str
    source_system: str
    replacement_issued: str
    transfers: int = Field(ge=0)

    @field_validator("status", "channel", "source_system", "replacement_issued")
    @classmethod
    def known_enum(cls, v, info):
        allowed = ENUMS[info.field_name]
        if v not in allowed:
            raise ValueError(f"{info.field_name}={v!r} not in {sorted(allowed)}")
        return v


def _check_enums(df: pd.DataFrame) -> None:
    for col, allowed in ENUMS.items():
        seen = set(df[col].dropna().unique())
        unknown = seen - allowed
        if unknown:
            raise ValueError(f"tickets.{col} has unexpected values: {sorted(unknown)}")


def load_tickets(path=None) -> pd.DataFrame:
    df = pd.read_csv(path or config.DATA / "tickets.csv", dtype=str)
    missing = set(TICKET_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"tickets.csv missing columns: {sorted(missing)}")
    _check_enums(df)
    return df


def load_agents(path=None) -> pd.DataFrame:
    a = pd.read_csv(path or config.DATA / "agents.csv", dtype=str)
    # Roster is one row per assignment (README). Collapse to the newest
    # assignment per agent so downstream joins can never fan out, even if a
    # future export does contain multiple rows per agent.
    a = a.sort_values(["agent_id", "from_date"]).drop_duplicates(
        "agent_id", keep="last")
    return a


def load_orders(path=None) -> pd.DataFrame:
    return pd.read_csv(path or config.DATA / "orders.csv")


def load_customers(path=None) -> pd.DataFrame:
    return pd.read_csv(path or config.DATA / "customers.csv", dtype=str)


def load_products(path=None) -> pd.DataFrame:
    return pd.read_csv(path or config.DATA / "products.csv")


def load_all() -> dict:
    return {
        "tickets": load_tickets(),
        "agents": load_agents(),
        "orders": load_orders(),
        "customers": load_customers(),
        "products": load_products(),
    }
