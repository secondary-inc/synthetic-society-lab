"""OpenRouter-only inference with durable conservative pre-dispatch reservations.

No automatic retry, route fallback, tools, plugins or model substitution. A timed-out
request may still be billed: uncertain reservations remain charged and halt the ledger.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from datetime import datetime, timezone
import json
import math
import sqlite3
import uuid
import urllib.request
from pathlib import Path
from .common import utc_now,canonical_hash,redact


class ExecutionBlocked(RuntimeError):
    pass


def micros(value):
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError("invalid monetary value")
    return int((number * 1_000_000).to_integral_value(rounding=ROUND_CEILING))


@dataclass(frozen=True)
class Policy:
    enabled: bool = False
    total_usd: str = "0"
    e01_usd: str = "0"
    e02_usd: str = "0"
    approval_id: str = ""


class BudgetLedger:
    def __init__(self, path, policy=Policy()):
        self.path, self.policy = Path(path), policy
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS charges (id TEXT PRIMARY KEY, module TEXT, reserved INTEGER, charged INTEGER, status TEXT, created TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS control (key TEXT PRIMARY KEY, value TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS metadata (id TEXT PRIMARY KEY, data TEXT)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def reserve(self, module, amount):
        p = self.policy
        if not p.enabled or not p.approval_id or module not in ("E01", "E02"):
            raise ExecutionBlocked("paid execution disabled or explicit approval missing")
        requested = micros(amount)
        if requested <= 0:
            raise ExecutionBlocked("unknown or zero request reservation")
        cap = micros(p.e01_usd if module == "E01" else p.e02_usd)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT value FROM control WHERE key='halt'").fetchone():
                raise ExecutionBlocked("ledger halted; reconcile uncertain or excessive charge")
            total = db.execute("SELECT COALESCE(SUM(charged),0) FROM charges").fetchone()[0]
            subtotal = db.execute("SELECT COALESCE(SUM(charged),0) FROM charges WHERE module=?", (module,)).fetchone()[0]
            if total + requested > micros(p.total_usd) or subtotal + requested > cap:
                raise ExecutionBlocked("approved spend ceiling exceeded")
            receipt = uuid.uuid4().hex
            db.execute("INSERT INTO charges VALUES (?,?,?,?,?,?)", (receipt, module, requested, requested, "RESERVED", utc_now()))
        return receipt

    def settle(self, receipt, actual=None, uncertain=False):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT reserved,status FROM charges WHERE id=?", (receipt,)).fetchone()
            if not row or row[1] != "RESERVED":
                raise ExecutionBlocked("invalid or settled reservation")
            charge = max(row[0], micros(actual)) if uncertain and actual is not None else row[0] if uncertain else micros(actual)
            excess = charge > row[0]
            status = "OVERRUN" if excess else "UNCERTAIN" if uncertain else "SETTLED"
            db.execute("UPDATE charges SET charged=?,status=? WHERE id=?", (max(charge, row[0]) if uncertain else charge, status, receipt))
            if uncertain or excess:
                db.execute("INSERT OR REPLACE INTO control VALUES ('halt',?)", (status,))
        if excess:
            raise ExecutionBlocked("reported charge exceeded reservation; ledger halted")

    def snapshot(self):
        with self.connect() as db:
            return [{"id": r[0], "module": r[1], "reserved_microusd": r[2],
                     "charged_microusd": r[3], "status": r[4], "at_utc": r[5],
                     'metadata':json.loads(db.execute('SELECT data FROM metadata WHERE id=?',(r[0],)).fetchone()[0])
                     if db.execute('SELECT data FROM metadata WHERE id=?',(r[0],)).fetchone() else {}}
                    for r in db.execute("SELECT * FROM charges ORDER BY created,id")]

    def record(self,receipt,fields):
        with self.connect() as db:
            row=db.execute('SELECT data FROM metadata WHERE id=?',(receipt,)).fetchone()
            current=json.loads(row[0]) if row else {}
            current.update(redact(fields))
            db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',(receipt,json.dumps(current,allow_nan=False)))


@dataclass(frozen=True)
class Price:
    model: str
    provider: str
    input_usd_per_token: str
    output_usd_per_token: str
    verified_at_utc: str
    source: str

    def validate(self):
        if not self.model or any(s in self.model.lower() for s in ("latest", ":free", "openrouter/")) or not self.provider:
            raise ExecutionBlocked("fixed model/provider required")
        if not self.source.startswith("https://openrouter.ai/"):
            raise ExecutionBlocked("official provider price evidence required")
        when = datetime.fromisoformat(self.verified_at_utc)
        if when.tzinfo is None or not 0 <= (datetime.now(timezone.utc) - when).total_seconds() <= 86400:
            raise ExecutionBlocked("pricing missing, future-dated or stale")
        if micros(self.input_usd_per_token) <= 0 or micros(self.output_usd_per_token) <= 0:
            raise ExecutionBlocked("positive verified prices required")


def network_transport(payload, api_key):
    # Prevent redirect-based credential disclosure; errors are surfaced by type only.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"})
    with urllib.request.build_opener(NoRedirect).open(req, timeout=60) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ExecutionBlocked("response exceeds size ceiling")
    return json.loads(raw)


class OpenRouter:
    def __init__(self, ledger, price, api_key="", transport=network_transport):
        self.ledger, self.price, self.api_key, self.transport = ledger, price, api_key, transport

    def complete(self, messages, *, module, max_tokens=512, seed=0):
        self.price.validate()
        if not self.api_key:
            raise ExecutionBlocked("local OpenRouter credential missing")
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or not 1 <= max_tokens <= 4096:
            raise ExecutionBlocked("invalid output ceiling")
        if not messages or any(set(m) != {"role", "content"} or m["role"] not in ("system", "user", "assistant") or not isinstance(m["content"], str) for m in messages):
            raise ExecutionBlocked("text-only messages required")
        encoded = json.dumps(messages, ensure_ascii=False).encode()
        if len(encoded) > 100_000:
            raise ExecutionBlocked("input exceeds byte ceiling")
        # Deliberately conservative byte upper bound plus message framing allowance.
        input_bound = len(encoded) + 1024 * len(messages)
        estimate = Decimal(input_bound) * Decimal(self.price.input_usd_per_token) + Decimal(max_tokens) * Decimal(self.price.output_usd_per_token)
        receipt = self.ledger.reserve(module, estimate)
        self.ledger.record(receipt,{'model':self.price.model,'requested_provider':self.price.provider,
                                   'request_hash':canonical_hash(messages),'input_token_bound':input_bound,
                                   'max_tokens':max_tokens,'seed':seed,'temperature':0,
                                   'pricing_verified_at_utc':self.price.verified_at_utc,
                                   'input_usd_per_token':self.price.input_usd_per_token,
                                   'output_usd_per_token':self.price.output_usd_per_token,
                                   'approval_id':self.ledger.policy.approval_id,'retries':0})
        payload = {"model": self.price.model, "messages": messages, "seed": seed,
                   "temperature": 0, "max_tokens": max_tokens, "stream": False,
                   "response_format": {"type": "json_object"},
                   "provider": {"only": [self.price.provider], "allow_fallbacks": False,
                                "require_parameters": True, "max_price": {
                                    "prompt": float(Decimal(self.price.input_usd_per_token) * 1_000_000),
                                    "completion": float(Decimal(self.price.output_usd_per_token) * 1_000_000)}}}
        reported_cost = None
        try:
            response = self.transport(payload, self.api_key)
            # Preserve valid billing even if routing, refusal or JSON checks fail.
            if isinstance(response, dict) and isinstance(response.get('usage'), dict) and 'cost' in response['usage']:
                micros(response['usage']['cost'])
                reported_cost = response['usage']['cost']
            self.ledger.record(receipt,{'actual_provider':response.get('provider'),
                                       'actual_model':response.get('model'),'completion_id':response.get('id'),
                                       'usage':{k:response.get('usage',{}).get(k) for k in ('cost','prompt_tokens','completion_tokens')}})
            if response.get("model") != self.price.model or response.get("provider") != self.price.provider:
                raise ExecutionBlocked("model or actual serving provider mismatch")
            usage = response["usage"]
            if not all(isinstance(usage.get(k), int) and not isinstance(usage[k], bool) and usage[k] >= 0 for k in ("prompt_tokens", "completion_tokens")):
                raise ExecutionBlocked("missing token accounting")
            if usage["prompt_tokens"] > input_bound or usage["completion_tokens"] > max_tokens:
                raise ExecutionBlocked("token ceiling exceeded")
            cost = usage["cost"]
            micros(cost)  # rejects negative, NaN or unknown charges
            content = response["choices"][0]["message"].get("content")
            if not isinstance(content, str):
                raise ExecutionBlocked("refusal or missing response content")
            output = json.loads(content)
            if not isinstance(output, dict):
                raise ExecutionBlocked("structured object required")
        except Exception as error:
            self.ledger.record(receipt,{'error_type':type(error).__name__})
            self.ledger.settle(receipt, actual=reported_cost, uncertain=True)
            raise ExecutionBlocked("request failed or accounting uncertain; no retry; ledger halted (" + type(error).__name__ + ")") from None
        self.ledger.settle(receipt, actual=cost)
        return {"output": output, "receipt": receipt, "model": response["model"],
                "provider": response["provider"], "usage": {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "cost")},
                "completion_id": response.get("id")}
