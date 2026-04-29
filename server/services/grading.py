"""NETS session grading — the single source of truth for the rubric.

This module owns everything GRADING.md says about how a session is scored:
  • which phases use which method (closed accuracy vs 2-axis AMR vs ungraded)
  • the score formula `((axis_1 + axis_2) / 2) * 25`
  • band thresholds (Mastered / Proficient / Apprentice / Novice)
  • the `>= 60%` conditional-button rule on the Results scorecard
  • per-phase aggregation rules (mean of items, pass/fail for tile-match, etc.)

The runtime template no longer computes any of this — it just collects the
session log (one entry per submitted answer) and POSTs it to
`/api/grading/aggregate`, then renders the response. Adding a new game in
the future is a one-dict edit here, not a change to the template.

Pure functions, no DB, no I/O. `routes/grading.py` is the HTTP surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


# ── Rubric configuration ────────────────────────────────────────────────────

# Per GRADING.md (At-a-glance table):
#   Section 1 Memory Sprint     — closed accuracy
#   Section 2 Story Mode        — pass/fail per checkpoint (closed)
#   Section 3 Game Breaks       — closed accuracy per game, mean across games
#                                 (Adaptive Quiz / Sentence Fill / Tile Match
#                                  / Mystery Box / Puzzle Lock all closed)
#   Section 4 Real-Life         — 2-axis rubric × 3-pass median
#   Section 5 Consolidation     — ungraded (engagement only)
#   Section 6 Final Boss        — 2-axis rubric per item; HP overlay separate
#   Section 7 Reflection        — ungraded (participation)
#
# The three methods:
#   "closed"   — counts toward donut + per-phase row; no axis means
#   "amr"      — counts toward donut + per-phase row + axis means
#   "ungraded" — neither in donut nor per-phase nor axes
PHASE_METHOD: dict[str, str] = {
    # Pre-session — ungraded by design
    "theme-preview":  "ungraded",
    "flash-cards":    "ungraded",
    # Phase 1
    "memory-sprint":  "closed",
    # Phase 2
    "story-mode":     "closed",
    # Phase 3 — Game Breaks (each closed; phase row is mean across games)
    "adaptive-quiz":  "closed",
    "sentence-fill":  "closed",
    "tile-match":     "closed",
    "mystery-box":    "closed",
    "puzzle-lock":    "closed",
    # Phase 4 — open responses, 2-axis AMR rubric
    "real-life":      "amr",
    # Phase 5 — ungraded (memory tree + 1-min self-check)
    "consolidation":  "ungraded",
    # Phase 6 — open boss attacks, 2-axis AMR rubric
    "final-boss":     "amr",
    # Phase 7 — ungraded (participation)
    "reflection":     "ungraded",
}

# Display-order + label table for the per-phase rows on the scorecard.
# Phases that aren't in this list still count toward AMR axis means if
# they're "amr" — but they don't render their own row. Keep this aligned
# with the at-a-glance order so the scorecard reads top-to-bottom.
PHASE_DISPLAY_ORDER: list[dict[str, Any]] = [
    {"key": "memory-sprint", "label": "Memory Sprint",  "phase_level": False},
    {"key": "story-mode",    "label": "Story Mode",     "phase_level": False},
    {"key": "adaptive-quiz", "label": "Adaptive Quiz",  "phase_level": False},
    {"key": "sentence-fill", "label": "Sentence Fill",  "phase_level": False},
    {"key": "tile-match",    "label": "Tile Match",     "phase_level": True},
    {"key": "real-life",     "label": "Real-Life",      "phase_level": False},
    {"key": "final-boss",    "label": "Final Boss",     "phase_level": False},
]

# Band thresholds applied to the 1-4 axis-mean scale (per GRADING.md
# rubric levels). For closed-only sessions where there are no axes, the
# overall percentage is mapped to the same 1-4 scale before banding.
BAND_THRESHOLDS = [
    (3.5, "mastered",   "Mastered"),
    (2.5, "proficient", "Proficient"),
    (1.5, "apprentice", "Apprentice"),
    (0.0, "novice",     "Novice"),
]

# Conditional-button rule for the bottom of the scorecard. >= 60% finishes
# the homework; below 60% offers a redo.
FINISH_THRESHOLD_PCT = 60


# ── Helpers ────────────────────────────────────────────────────────────────

def _band_for_axis_avg(axis_avg: float) -> tuple[str, str]:
    """Return (key, name) for a given axis average on the 1-4 scale."""
    for cutoff, key, name in BAND_THRESHOLDS:
        if axis_avg >= cutoff:
            return key, name
    return "novice", "Novice"


def _perf_class_for_pct(pct: float) -> str:
    """Same color rule used everywhere: ≥75% green, 50-74% yellow, else red."""
    if pct >= 75:
        return "perf-good"
    if pct >= 50:
        return "perf-mid"
    return "perf-bad"


def _perf_class_for_axis(mean: float | None) -> str:
    """Per-axis tag color: ≥3.0 green, 2.0–2.99 yellow, <2.0 red, none → neutral."""
    if mean is None:
        return "perf-neutral"
    if mean >= 3.0:
        return "perf-good"
    if mean >= 2.0:
        return "perf-mid"
    return "perf-bad"


def _axis_tag_for(mean: float | None) -> str:
    if mean is None:
        return "AI baholangan ochiq javob yo'q"
    if mean >= 3.0:
        return "Yaxshi daraja"
    if mean >= 2.0:
        return "O'rta daraja"
    return "Past daraja"


def _coaching_tip(band_key: str, has_axes: bool, overall_pct: int) -> str:
    """The one-paragraph nudge under the AMR card. Branded green/yellow/red
    via the same band → perf class mapping the renderer uses."""
    if has_axes:
        return {
            "mastered":   "Ajoyib! Siz ushbu mavzuni mukammal o'zlashtirdingiz. "
                          "Mastery promotion windowga 1 ball qo'shildi (3 dan).",
            "proficient": "Yaxshi. Siz mustaqil ishlay olasiz. Yana 1-2 sessiya — "
                          "Mastered darajasiga yetasiz.",
            "apprentice": "Konseptni nomlash yoki bosqichlarni ko'rsatishda "
                          "bo'shliqlar bor — keyingi mashqlarda jarayonni "
                          "yozma ko'rsating.",
            "novice":     "Mavzuni qaytadan ko'rib chiqing. Hint Ladder va "
                          "Flash Card'larni qayta o'qing, so'ng yana urinib ko'ring.",
        }.get(band_key, "")
    return (
        f"Yopiq-format javoblar tahlilingiz: {overall_pct}%. "
        "Ochiq topshiriqlarda AMR baholash to'liq amal qiladi."
    )


# ── Aggregator ─────────────────────────────────────────────────────────────

@dataclass
class _Item:
    phase: str
    correct: bool
    score: float
    axis_1: float | None = None
    axis_2: float | None = None
    closed: bool = False


def _coerce(item: dict[str, Any]) -> _Item:
    """Normalize a log entry dict from the runtime into an _Item."""
    phase = str(item.get("phase", "")).strip()
    correct = bool(item.get("correct"))
    try:
        score = float(item.get("score", 1.0 if correct else 0.0))
    except (TypeError, ValueError):
        score = 1.0 if correct else 0.0
    a1 = item.get("axis_1")
    a2 = item.get("axis_2")
    a1 = float(a1) if isinstance(a1, (int, float)) else None
    a2 = float(a2) if isinstance(a2, (int, float)) else None
    closed = bool(item.get("closed"))
    return _Item(phase=phase, correct=correct, score=score, axis_1=a1, axis_2=a2, closed=closed)


def aggregate(items: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Take a list of session-log dicts and return the scorecard payload.

    Output shape (consumed by the runtime template's `showResultsScreen`):
      {
        "overall_pct":         int 0-100,
        "overall_score":       float (axis-derived if AMR items exist),
        "overall_axis_1":      float|None,
        "overall_axis_2":      float|None,
        "band":                {"key": str, "name": str},
        "perf_class":          "perf-good" | "perf-mid" | "perf-bad",
        "has_axes":            bool,
        "phases": [
          {"key", "label", "is_phase_level", "correct", "total", "pct",
           "perf_class", "score_text",
           "axis_1_mean": float|None, "axis_2_mean": float|None}
        ],
        "axes": {
          "axis_1": {"mean": float|None, "perf_class": str, "tag": str},
          "axis_2": {"mean": float|None, "perf_class": str, "tag": str}
        },
        "totals":              {"correct": int, "items": int},
        "coaching_tip":        str,
        "action": {"kind": "finish"|"redo", "label": str, "perf_class": str}
      }
    """
    parsed = [_coerce(i) for i in items if isinstance(i, dict)]
    by_phase: dict[str, list[_Item]] = {}
    for it in parsed:
        if not it.phase:
            continue
        if PHASE_METHOD.get(it.phase) == "ungraded":
            continue
        by_phase.setdefault(it.phase, []).append(it)

    # ── Per-phase rows ───────────────────────────────────────────────
    phase_rows: list[dict[str, Any]] = []
    for spec in PHASE_DISPLAY_ORDER:
        key = spec["key"]
        items_in_phase = by_phase.get(key, [])
        method = PHASE_METHOD.get(key, "closed")
        is_phase_level = bool(spec["phase_level"])

        total = len(items_in_phase)
        correct_count = sum(1 for x in items_in_phase if x.correct)

        if total == 0:
            pct: float = 0.0
            score_text = "—"
            perf = "perf-neutral"
        elif is_phase_level:
            # Tile Match — pass/fail row
            passed = bool(items_in_phase[0].correct) if items_in_phase else False
            pct = 100.0 if passed else 0.0
            score_text = "Bajarildi" if passed else "—"
            perf = "perf-good" if passed else "perf-bad"
        else:
            pct = (100.0 * correct_count) / total
            score_text = f"{correct_count}/{total}"
            perf = _perf_class_for_pct(pct)

        # Per-phase axis means — only counted from items that explicitly carry
        # numeric axis values (so closed-form items can't poison the means).
        axed = [x for x in items_in_phase if x.axis_1 is not None and x.axis_2 is not None]
        a1_mean = (sum(x.axis_1 for x in axed) / len(axed)) if axed else None
        a2_mean = (sum(x.axis_2 for x in axed) / len(axed)) if axed else None

        phase_rows.append({
            "key":            key,
            "label":          spec["label"],
            "method":         method,
            "is_phase_level": is_phase_level,
            "correct":        correct_count,
            "total":          total,
            "pct":            round(pct, 1),
            "perf_class":     perf,
            "score_text":     score_text,
            "axis_1_mean":    a1_mean,
            "axis_2_mean":    a2_mean,
        })

    # ── Overall AMR axes — pool every axed item across all AMR phases ─
    all_axed: list[_Item] = []
    for phase_key, lst in by_phase.items():
        if PHASE_METHOD.get(phase_key) != "amr":
            continue
        for x in lst:
            if x.axis_1 is not None and x.axis_2 is not None:
                all_axed.append(x)

    if all_axed:
        overall_a1 = sum(x.axis_1 for x in all_axed) / len(all_axed)
        overall_a2 = sum(x.axis_2 for x in all_axed) / len(all_axed)
        # GRADING.md formula
        overall_score = ((overall_a1 + overall_a2) / 2.0) * 25.0
        band_key, band_name = _band_for_axis_avg((overall_a1 + overall_a2) / 2.0)
        has_axes = True
    else:
        overall_a1 = None
        overall_a2 = None
        overall_score = None
        band_key = "novice"
        band_name = "Novice"
        has_axes = False

    # ── Totals (donut counter) ──────────────────────────────────────
    total_correct = 0
    total_items = 0
    for row in phase_rows:
        if row["is_phase_level"]:
            total_items += row["total"]
            if row["correct"] > 0:
                total_correct += row["total"]
        else:
            total_correct += row["correct"]
            total_items   += row["total"]

    overall_pct_raw = (100.0 * total_correct / total_items) if total_items > 0 else 0.0
    item_score = overall_score if has_axes else overall_pct_raw
    overall_pct = int(round(item_score))

    # Closed-only sessions still need a band — derive from the percentage.
    if not has_axes:
        pseudo_axis = overall_pct_raw / 25.0
        band_key, band_name = _band_for_axis_avg(pseudo_axis)

    perf_class = _perf_class_for_pct(overall_pct)

    # ── Action button ──────────────────────────────────────────────
    if overall_pct >= FINISH_THRESHOLD_PCT:
        action = {"kind": "finish", "label": "Tugatish", "perf_class": "is-finish"}
    else:
        action = {"kind": "redo",   "label": "Qayta bajarish", "perf_class": "is-redo"}

    return {
        "overall_pct":    overall_pct,
        "overall_score":  None if overall_score is None else round(overall_score, 1),
        "overall_axis_1": None if overall_a1 is None else round(overall_a1, 2),
        "overall_axis_2": None if overall_a2 is None else round(overall_a2, 2),
        "band":           {"key": band_key, "name": band_name},
        "perf_class":     perf_class,
        "has_axes":       has_axes,
        "phases":         phase_rows,
        "axes": {
            "axis_1": {
                "mean":       overall_a1,
                "perf_class": _perf_class_for_axis(overall_a1),
                "tag":        _axis_tag_for(overall_a1),
            },
            "axis_2": {
                "mean":       overall_a2,
                "perf_class": _perf_class_for_axis(overall_a2),
                "tag":        _axis_tag_for(overall_a2),
            },
        },
        "totals":       {"correct": total_correct, "items": total_items},
        "coaching_tip": _coaching_tip(band_key, has_axes, int(round(overall_pct_raw))),
        "action":       action,
    }
