"""Single source of truth for policy constants and the taxonomy.

Every number in this file traces to support-policy.pdf v3.2. Section
references are given so any figure in the digest can be audited.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
CACHE = OUT / "cache"
PROMPTS = ROOT / "prompts"

# --- policy 4: fully loaded cost per contact (FY26 planning figures) ---
CONTACT_COST = {"chat": 210, "email": 260, "voice": 520, "social": 240}
BLENDED_CONTACT_COST = 290
TRANSFER_COST = 305
AGENT_HOUR_COST = 165
SHIFT_HOURS = 8

# --- policy 3: first-response targets (minutes) and breach credit ---
SLA_TARGET_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}
SLA_BREACH_CREDIT = 350

# --- policy 5: remedies ---
REPLACEMENT_LOGISTICS = 340          # + product unit_cost_inr
GOODWILL_CAP = 500                   # per ticket, Team Lead approval
PRODUCT_REFUND_CODES = {"RETURN-QC-OK", "DOA-REPL", "WTY-BUYBACK"}
PAYMENT_CORRECTION_CODES = {"DUP-PAYMENT", "PRICE-ADJ", "CANCEL"}

# --- policy 10: first-contact resolution window ---
REPEAT_WINDOW_DAYS = 30

# --- policy 9: migration ---
HELPDESK_GOLIVE = "2025-09-14"
LEGACY_UTC_OFFSET_HOURS = 5.5        # legacy resolved_at is UTC, display is IST

# --- policy 6: tiers ---
TIER2_VOLUME_EXEMPT = True

# --- business goal target (see decisions.md D13) ---
GOAL_CURRENT_PCT = None              # computed, never hardcoded
GOAL_TARGET_PCT = 1.0

PROMPT_VERSION = "classify_v1"

# --- taxonomy: 13 labels (12 themes + Unclear/other). See decisions.md D14 ---
TAXONOMY = {
    "Delivery delayed or not received":
        "Order has not arrived, is late, tracking is stuck, or courier marked "
        "delivered but nothing received.",
    "Arrived damaged or dead on arrival":
        "Item arrived physically damaged, cracked, dented, or non-functional "
        "straight out of the box.",
    "Charging & battery fault":
        "Device or case will not charge, shows 0%, drains abnormally fast, or "
        "will not power on.",
    "Audio quality fault":
        "Sound problem in a working device: one side silent, buzzing, "
        "distortion, low or unclear microphone.",
    "Connectivity & pairing fault":
        "Bluetooth will not pair, drops, cuts out, or the device no longer "
        "appears in the phone's device list.",
    "App & firmware fault":
        "Companion app crashes, shows a blank screen, or a firmware update "
        "fails or hangs.",
    "Payment & invoice":
        "Money taken with no order created, duplicate charge, coupon or "
        "discount not applied, or tax invoice / receipt request.",
    "Account access / login":
        "Cannot sign in, OTP not arriving, or account locked.",
    "Return pickup & refund status":
        "Return pickup not collected or rescheduled, or a refund already "
        "agreed has not reached the customer.",
    "Warranty claim / RMA status":
        "Chasing an existing warranty claim or RMA number, or asking for "
        "warranty repair.",
    "Order change, cancellation & address":
        "Cancel before dispatch, wrong variant ordered, or delivery address "
        "needs changing.",
    "Pre-sales / compatibility (no fault)":
        "Question about whether a product works with something, or what it "
        "does, with no fault reported. Excluded from fault-cost work.",
    "Unclear / other":
        "Genuinely cannot be placed in a theme above from the message alone.",
}
LABELS = list(TAXONOMY)
NO_FAULT_LABELS = {"Pre-sales / compatibility (no fault)"}
