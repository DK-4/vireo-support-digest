"""Theme classification for ticket free text.

Design rules this module exists to enforce:
  * the model assigns a label and nothing else - it never sees or emits a number
  * ticket text is DATA, never instructions (delimiters + explicit system rule)
  * PII leaves the machine stripped (phones, emails, order IDs, RMA numbers)
  * every label is validated against the 13-label taxonomy; anything else is
    an invalid output, counted and retried, never silently coerced
  * results are cached on disk by ticket_id + prompt version, so a re-run is
    free and the bill is a one-off, not per-ticket (Arjun, 8 Sep)
  * MOCK mode runs the whole pipeline with no API key. Mock labels are tagged
    label_source="MOCK" and report.py refuses to publish them unwatermarked.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field

import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator

from . import config

# --------------------------------------------------------------- schema
class Label(BaseModel):
    theme: str
    confidence: float
    evidence_phrase: str

    @field_validator("theme")
    @classmethod
    def known_theme(cls, v):
        if v not in config.LABELS:
            raise ValueError(f"theme {v!r} is not one of the {len(config.LABELS)} allowed labels")
        return v

    @field_validator("confidence")
    @classmethod
    def in_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return v

    @field_validator("evidence_phrase")
    @classmethod
    def short_quote(cls, v):
        if len(v) > 120:
            raise ValueError("evidence_phrase must be a short quote (<=120 chars)")
        return v


# ------------------------------------------------------------ PII scrub
PII = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"(?<!\w)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\w)"), "[PHONE]"),
    (re.compile(r"\bVR\d{5,}\b", re.I), "[ORDER_ID]"),
    (re.compile(r"\bRMA\d{3,}\b", re.I), "[RMA]"),
    (re.compile(r"\bTK-\d{4,}\b", re.I), "[TICKET_ID]"),
    (re.compile(r"\bC1\d{5}\b"), "[CUSTOMER_ID]"),
]


def strip_pii(text: str) -> str:
    out = str(text).replace("\\n", "\n")
    for pat, repl in PII:
        out = pat.sub(repl, out)
    return out.strip()


# ----------------------------------------------------------- mock engine
MOCK_RULES = [
    ("Arrived damaged or dead on arrival", r"crack|crush|dent|broken|damaged|smashed|before i even"),
    ("Order change, cancellation & address", r"cancel|wrong colour|wrong color|by mistake|moved house|change (the )?address|old flat|don'?t ship"),
    ("Account access / login", r"otp|log ?in|locked out|password|sign in"),
    ("Warranty claim / RMA status", r"warranty|\brma\b|claim number|service cent"),
    ("Return pickup & refund status", r"pickup|pick-?up|return was|refund (not|still)|where is the money|packed the box|reschedul"),
    ("Payment & invoice", r"deducted|no order (was )?creat|duplicate|coupon|discount was not|invoice|tax bill|statement|bank says"),
    ("App & firmware", r"app |firmware|white screen|update (failed|stuck)|cleared cache"),
    ("Charging & battery fault", r"charg|battery|0%|won'?t turn on|drain|no light"),
    ("Audio quality fault", r"sound|audio|mic\b|volume|one ear|buzzing|distort|repeat myself|mute"),
    ("Connectivity & pairing fault", r"bluetooth|pair|connection drops|keeps losing|cutting out|doesn'?t see it|not show"),
    ("Delivery delayed or not received", r"not (yet )?(receiv|deliver)|out for delivery|tracking|courier|nothing in hand|nobody"),
    ("Pre-sales / compatibility (no fault)", r"will (this|it|the)|does (my|this|it)|compatible|work with|before i buy|can i connect"),
]
MOCK_RULES = [(t.replace("App & firmware", "App & firmware fault"), re.compile(p, re.I))
              for t, p in MOCK_RULES]


def mock_label(text: str) -> Label:
    for theme, pat in MOCK_RULES:
        m = pat.search(text)
        if m:
            return Label(theme=theme, confidence=0.35,
                         evidence_phrase=m.group(0)[:120])
    return Label(theme="Unclear / other", confidence=0.2, evidence_phrase="")


# ------------------------------------------------------------ LLM client
@dataclass
class CallLog:
    path: object
    rows: list = field(default_factory=list)

    def add(self, **kw):
        self.rows.append(kw)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(kw) + "\n")


class LLMClient:
    """Works against an OpenAI-compatible endpoint or the Anthropic messages API.

    Selected entirely by env vars so no provider is baked in:
        LLM_PROVIDER = anthropic | openai   (default: anthropic)
        LLM_API_KEY  = ...
        LLM_BASE_URL = https://api.anthropic.com  (or any compatible host)
        LLM_MODEL    = model string
    """

    def __init__(self, log_path=None):
        self.provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "")
        self.base_url = os.getenv("LLM_BASE_URL", "").rstrip("/") or (
            "https://api.anthropic.com" if self.provider == "anthropic"
            else "https://api.openai.com/v1")
        self.timeout = float(os.getenv("LLM_TIMEOUT", "60"))
        self.log = CallLog(log_path or config.OUT / "llm_calls.jsonl")
        # Pace calls to stay under the provider's requests-per-minute limit
        # instead of firing as fast as the network allows and relying on
        # retries to absorb the resulting 429s. 0 = no pacing (default keeps
        # old behaviour for providers with high/no rate limits).
        self.rpm = float(os.getenv("LLM_RPM", "0") or 0)
        self._min_interval = 60.0 / self.rpm if self.rpm > 0 else 0.0
        self._last_call_started = 0.0

    def _pace(self):
        if self._min_interval <= 0:
            return
        wait = self._min_interval - (time.time() - self._last_call_started)
        if wait > 0:
            time.sleep(wait)
        self._last_call_started = time.time()

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.model)

    def _post(self, system: str, user: str) -> tuple[str, dict]:
        self._pace()
        import urllib.request
        if self.provider == "anthropic":
            url = f"{self.base_url}/v1/messages"
            headers = {"content-type": "application/json",
                       "x-api-key": self.api_key,
                       "anthropic-version": "2023-06-01"}
            body = {"model": self.model, "max_tokens": 300, "system": system,
                    "messages": [{"role": "user", "content": user}]}
        else:
            url = f"{self.base_url}/chat/completions"
            headers = {"content-type": "application/json",
                       "authorization": f"Bearer {self.api_key}"}
            body = {"model": self.model, "max_tokens": 300,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}]}
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.loads(r.read())
        if self.provider == "anthropic":
            text = data["content"][0]["text"]
            usage = {"input_tokens": data.get("usage", {}).get("input_tokens"),
                     "output_tokens": data.get("usage", {}).get("output_tokens")}
        else:
            text = data["choices"][0]["message"]["content"]
            u = data.get("usage", {})
            usage = {"input_tokens": u.get("prompt_tokens"),
                     "output_tokens": u.get("completion_tokens")}
        return text, usage

    def label(self, system: str, user: str, ticket_id: str,
              retries: int = 3) -> tuple[Label | None, dict]:
        last_err = None
        for attempt in range(1, retries + 1):
            t0 = time.time()
            try:
                text, usage = self._post(system, user)
                raw = text.strip()
                if raw.startswith("```"):
                    raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
                obj = Label(**json.loads(raw))
                self.log.add(ticket_id=ticket_id, attempt=attempt, ok=True,
                             model=self.model, provider=self.provider,
                             seconds=round(time.time() - t0, 2), **usage)
                return obj, usage
            except (ValidationError, json.JSONDecodeError) as e:
                last_err = f"invalid_output: {e}"
            except Exception as e:                      # network / timeout / 5xx
                last_err = f"transport: {type(e).__name__}: {e}"
            self.log.add(ticket_id=ticket_id, attempt=attempt, ok=False,
                         error=str(last_err)[:300], model=self.model,
                         provider=self.provider, seconds=round(time.time() - t0, 2))
            # A 429 means the per-minute quota is exhausted, not a blip - an
            # 8-second backoff can never clear a 60-second window, so wait
            # long enough to actually recover instead of burning retries.
            rate_limited = "429" in str(last_err) or "Too Many Requests" in str(last_err)
            time.sleep(65 if rate_limited else min(2 ** attempt, 8))
        return None, {"error": last_err}


# ------------------------------------------------------------ orchestration
def build_prompt(messages: list[str]) -> tuple[str, str]:
    template = (config.PROMPTS / f"{config.PROMPT_VERSION}.txt").read_text(encoding="utf-8")
    taxonomy = "\n".join(f"- {k}: {v}" for k, v in config.TAXONOMY.items())
    system = template.replace("{{TAXONOMY}}", taxonomy)
    body = "\n\n".join(
        f"<<<TICKET {i+1}>>>\n{m}\n<<<END TICKET {i+1}>>>"
        for i, m in enumerate(messages))
    return system, body


def run(df: pd.DataFrame, mode: str = "auto", batch_size: int = 1,
        limit: int | None = None) -> pd.DataFrame:
    """Returns ticket_id, theme, confidence, evidence_phrase, label_source."""
    config.CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = config.CACHE / f"labels_{config.PROMPT_VERSION}.parquet"
    cached = (pd.read_parquet(cache_file) if cache_file.exists()
              else pd.DataFrame(columns=["ticket_id", "theme", "confidence",
                                         "evidence_phrase", "label_source"]))

    client = LLMClient()
    if mode == "live" and not client.available:
        raise SystemExit(
            "--mode live needs LLM_API_KEY and LLM_MODEL set. Refusing to fall "
            "back to MOCK silently: mock labels must never be mistaken for "
            "model output. Use --mode mock if that is what you want.")
    use_mock = (mode == "mock") or (mode == "auto" and not client.available)
    source = "MOCK" if use_mock else f"{client.provider}:{client.model}"

    work = df if limit is None else df.head(limit)
    todo = work[~work.ticket_id.isin(cached.ticket_id)]
    rows, invalid = [], 0

    if use_mock:
        for r in todo.itertuples():
            lab = mock_label(strip_pii(r.customer_message))
            rows.append(dict(ticket_id=r.ticket_id, theme=lab.theme,
                             confidence=lab.confidence,
                             evidence_phrase=lab.evidence_phrase,
                             label_source="MOCK"))
    else:
        system, _ = build_prompt([])
        for r in todo.itertuples():
            clean_text = strip_pii(r.customer_message)
            user = (f"<<<TICKET>>>\n{clean_text}\n<<<END TICKET>>>\n\n"
                    "Return only the JSON object.")
            lab, _ = client.label(system, user, r.ticket_id)
            if lab is None:
                invalid += 1
                rows.append(dict(ticket_id=r.ticket_id, theme="Unclear / other",
                                 confidence=0.0, evidence_phrase="",
                                 label_source=source + ":FAILED"))
            else:
                rows.append(dict(ticket_id=r.ticket_id, theme=lab.theme,
                                 confidence=lab.confidence,
                                 evidence_phrase=lab.evidence_phrase,
                                 label_source=source))

    out = pd.concat([cached, pd.DataFrame(rows)], ignore_index=True)
    out = out.drop_duplicates("ticket_id", keep="last")
    out.to_parquet(cache_file, index=False)
    out.attrs["invalid_outputs"] = invalid
    out.attrs["mock"] = use_mock
    return out[out.ticket_id.isin(work.ticket_id)]
