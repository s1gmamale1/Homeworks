"""LLM cost estimate from ai_call_logs.

USAGE:
    .venv\\Scripts\\python.exe scripts\\llm_cost_report.py

Disclaimer:
    Costs are ESTIMATES. ai_call_logs records `input_chars` / `output_chars`,
    not actual API-billed tokens. We approximate tokens as `chars / 4` which
    is reasonable for English (~3-4 chars/token) and slightly underestimates
    for Uzbek/Russian where tokenization is denser. Verify against your
    provider's billing dashboard before using these numbers for invoicing.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


DB = Path(__file__).resolve().parent.parent / "nets.db"

# Per-million-token pricing (USD). Sources: OpenAI public pricing page +
# Moonshot/Kimi published rates (verify your account tier — these are the
# standard pay-as-you-go rates as of 2026).
PRICING_PER_M_TOKENS = {
    # OpenAI
    "gpt-4o-mini":               {"in": 0.15,  "out": 0.60},
    "gpt-4o":                    {"in": 2.50,  "out": 10.00},
    "gpt-4o-mini-2024-07-18":    {"in": 0.15,  "out": 0.60},
    # Kimi / Moonshot
    "moonshot-v1-32k":           {"in": 0.20,  "out": 0.20},
    "moonshot-v1-128k":          {"in": 1.00,  "out": 1.00},
    "moonshot-v1-128k-vision-preview": {"in": 1.00, "out": 1.00},
    "kimi-k2.6":                 {"in": 1.50,  "out": 1.50},
    "kimi-k2-turbo-preview":     {"in": 1.20,  "out": 1.20},
}

#  chars-per-token ratio empirically calibrated 2026-05-14 against the OpenAI
#  dashboard: 253,405 chars produced 81,643 tokens → ratio 3.1. Our prompts
#  carry a lot of Uzbek/Russian text + JSON schemas, both of which tokenize
#  denser than plain English (~4 chars/token). Adjust upward (toward 4) if
#  most calls are English-only; downward (toward 2.5) for heavy Cyrillic.
CHARS_PER_TOKEN = 3.1


def _est_tokens(chars: int) -> float:
    return chars / CHARS_PER_TOKEN


def _cost_usd(model: str, in_chars: int, out_chars: int) -> tuple[float, bool]:
    """Return (cost_usd, pricing_known). pricing_known=False when the model
    isn't in PRICING_PER_M_TOKENS — caller surfaces a $0.00 entry with a flag
    so the operator knows to update the table."""
    rates = PRICING_PER_M_TOKENS.get(model)
    if not rates:
        return 0.0, False
    in_tokens_m = _est_tokens(in_chars) / 1_000_000
    out_tokens_m = _est_tokens(out_chars) / 1_000_000
    return in_tokens_m * rates["in"] + out_tokens_m * rates["out"], True


def _fmt_money(usd: float) -> str:
    if usd < 0.01:
        return f"${usd:.5f}"
    return f"${usd:.4f}"


def report(since_iso: str | None = None, label: str = "all-time") -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    q = """
        SELECT provider, model,
               COUNT(*)                      AS calls,
               SUM(input_chars)              AS in_chars,
               SUM(output_chars)             AS out_chars,
               SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) AS ok,
               SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) AS fail
        FROM ai_call_logs
    """
    params: tuple = ()
    if since_iso:
        q += " WHERE created_at >= ?"
        params = (since_iso,)
    q += " GROUP BY provider, model ORDER BY SUM(input_chars) DESC"

    rows = c.execute(q, params).fetchall()
    if not rows:
        print(f"\n=== {label} ===  (no calls)")
        return

    print(f"\n=== {label} ===")
    fmt = "{:<8} {:<35} {:>6} {:>6} {:>5} {:>10} {:>10} {:>11}"
    print(fmt.format(
        "PROVIDER", "MODEL", "CALLS", "OK", "FAIL",
        "IN_CHARS", "OUT_CHARS", "EST $ COST",
    ))
    print("-" * 100)

    total = 0.0
    unknown_models: list[str] = []
    grand_calls = 0
    grand_in_chars = 0
    grand_out_chars = 0
    for r in rows:
        provider = r["provider"] or "(none)"
        model = r["model"] or "(none)"
        calls = r["calls"] or 0
        ok = r["ok"] or 0
        fail = r["fail"] or 0
        in_chars = r["in_chars"] or 0
        out_chars = r["out_chars"] or 0
        cost, known = _cost_usd(model, in_chars, out_chars)
        if not known:
            unknown_models.append(model)
        total += cost
        grand_calls += calls
        grand_in_chars += in_chars
        grand_out_chars += out_chars
        print(fmt.format(
            provider, model, calls, ok, fail,
            f"{in_chars:,}", f"{out_chars:,}",
            _fmt_money(cost) + ("*" if not known else ""),
        ))

    print("-" * 100)
    print(fmt.format(
        "TOTAL", "", grand_calls, "", "",
        f"{grand_in_chars:,}", f"{grand_out_chars:,}", _fmt_money(total),
    ))
    print(
        f"\nEstimated total: {_fmt_money(total)} "
        f"({_est_tokens(grand_in_chars):,.0f} input tokens, "
        f"{_est_tokens(grand_out_chars):,.0f} output tokens, "
        f"@ ~{CHARS_PER_TOKEN:.1f} chars/token)"
    )
    if unknown_models:
        print(
            f"\n*  Models without pricing entries (counted as $0): "
            f"{', '.join(sorted(set(unknown_models)))}"
        )

    conn.close()


if __name__ == "__main__":
    # All-time view first.
    report(since_iso=None, label="ALL-TIME (every row in ai_call_logs)")

    # Today (UTC start of day).
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
    report(since_iso=today_utc, label=f"TODAY since {today_utc} UTC")

    # Last 24h (rolling window).
    last_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    report(since_iso=last_24h, label=f"LAST 24h (since {last_24h[:16]})")
