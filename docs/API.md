# NETS Homework Builder — API Reference

Base URL (production): `http://sigmaai.local:8000`  ·  Local dev: `http://localhost:8000`

All responses JSON unless marked **HTML**. Errors: `{ "detail": { "error": "...", "code": "..." } }` with 4xx/5xx status.

## Quick index

| Group | Endpoints |
|-------|-----------|
| Homework CRUD | POST/GET/PUT/DELETE /api/homeworks, /…/{id}/restore, /…/{id}/permanent, /…/{id}/duplicate, PATCH /…/{id}/content |
| Versions | GET/GET/POST /api/homeworks/{id}/versions, /…/{id}/versions/{vid}, /…/{id}/versions/{vid}/restore |
| Render | GET /h/{id} (HTML), GET /api/homeworks/{id}/preview (HTML) |
| Library | GET /api/library, GET /api/library/facets |
| Quotes | GET /api/quotes |
| AI tutor | POST /api/ai/check-answer, /api/ai/boss-turn, /api/ai/reflection, /api/ai/tutor |
| AI live tutor (Wave F1) | POST /api/ai/tutor/chat, /api/ai/tutor/boss-plan, GET /api/ai/tutor/history |
| AI meta | GET /api/ai/status |
| Review queue | GET /api/ai/review-queue, POST /api/ai/review-queue/{id}/decide |
| Answer-spec | POST /api/ai/answer-spec/preview |
| Notebook | POST /api/notebook/grade, GET /api/notebook/captures |
| Grading | POST /api/grading/aggregate, GET /api/grading/rubric |
| Meta | GET /api/health, GET /api/subjects, GET /api/fixtures, GET /api/fixtures/{name} |
| Trash | GET /api/trash |
| Admin | POST /api/admin/checkpoint |

---

## Homework CRUD

### POST /api/homeworks

```json
{ "title": "string", "subject": "math-algebra", "grade": 8, "mode": "easy" }
```
- `subject`: must appear in `/api/subjects`; `grade` must be valid for that subject
- `mode`: `"easy"` | `"hard"` — subjects in `ALWAYS_HARD` force `"hard"` regardless
- `family` and `content_json` are **not accepted** — derived/scaffolded server-side

**200** full Homework Record (see shape below). **400** `INVALID_SUBJECT` / `INVALID_GRADE` / `INVALID_MODE`.

---

### GET /api/homeworks

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `q` | str | — | Full-text on `title`, `subject`, `family` |
| `subject` | str | — | Exact match |
| `grade` | int | — | Exact match |
| `mode` | str | — | Exact match |
| `limit` | int | 50 | Clamped to 200 silently |
| `offset` | int | 0 | |
| `legacy` | bool | false | Returns bare array — deprecated |
| `include_deleted` | bool | false | Include soft-deleted rows |

**200** `{ "items": [...], "total": N, "limit": L, "offset": O }`. With `legacy=true`: bare array.

**List-payload enrichments (PR #118):**
- Each item has a computed `progress` field (`int 0..100`) derived from `compute_progress()` over the canonical content sections (see `server/services/progress.py`). Status overrides: `ready → 100`, `error → 0`, `generating` capped at 90.
- `content_json` is **dropped** from the list payload to keep the dashboard response small. The single-item endpoint `GET /api/homeworks/{hw_id}` still returns it in full.

---

### GET /api/homeworks/{hw_id}

**200** full Homework Record (includes `content_json`). **404** `NOT_FOUND`.

---

### PUT /api/homeworks/{hw_id}

```json
{ "title": "string", "content_json": { ... } }
```
All fields optional. `content_json` schema: [CONTRACTS.md §1](../CONTRACTS.md#1-data-model--content_json). Returns unchanged record if no recognised fields.

**`content_json` is fully replaced** — every key you omit gets wiped from the stored blob. Use `PATCH /…/{id}/content` (below) when you only want to update a subset. The builder UI always sends the complete blob.

**200** updated record. **404** `NOT_FOUND`. **409** `TRASHED`.

---

### PATCH /api/homeworks/{hw_id}/content

```json
{ "content_json": { "gb_puzzle_lock": [{ "content": "1", "q": "...", "a": "..." }] } }
```

Partial update. Deep-merges the keys you send into the existing `content_json`:

- Top-level keys present in the patch overwrite the same keys in storage.
- When BOTH sides hold a dict at the same key, the merge recurses (so `{ "meta": { "section": "22" } }` only updates `section`, leaves `title`/`subject_display`/`cefr_level` alone).
- Arrays are replaced wholesale — no append.
- `null` sets the key to null (does NOT delete it).
- Keys you omit are left untouched.

**200** updated record. **404** `NOT_FOUND`. **409** `TRASHED`.

---

### DELETE /api/homeworks/{hw_id}

Soft delete (trash). **200** `{ "ok": true, "trashed": true }`. If already trashed: `{ "ok": true, "already_trashed": true }`. **404** `NOT_FOUND` if record does not exist.

---

### POST /api/homeworks/{hw_id}/restore

**200** `{ "ok": true, "restored": true }`. If not trashed: `{ "ok": true, "already_active": true }`. **404** `NOT_FOUND`.

---

### DELETE /api/homeworks/{hw_id}/permanent

Hard delete — removes row and all version history. **200** `{ "ok": true, "hard_deleted": true }`. **404** `NOT_FOUND`.

---

### POST /api/homeworks/{hw_id}/duplicate

Clones `title` (appended `" (copy)"`), `subject`, `grade`, `mode`, `content_json` into a new `draft`. Version history not cloned.

**200** new Homework Record. **404** `NOT_FOUND`. **409** `TRASHED`.

---

### Homework Record shape

```json
{
  "id": "HW-20260427-001",
  "title": "string",
  "subject": "math-algebra",
  "grade": 8,
  "mode": "hard",
  "family": "aniq-fanlar",
  "language": "uz",
  "status": "draft",
  "content_json": { ... },
  "created_at": "2026-04-27T10:00:00+00:00",
  "updated_at": "2026-04-27T10:00:00+00:00",
  "deleted_at": null
}
```
`content_json` schema: [CONTRACTS.md §1](../CONTRACTS.md#1-data-model--content_json).
List responses omit `content_json` from each item.

---

## Version History

### GET /api/homeworks/{hw_id}/versions

**200** `{ "homework_id": "...", "versions": [ { "id": 7, "homework_id": "...", "title": "...", "saved_at": "...", "size_bytes": 4210 } ], "count": N }`. Metadata only — no `content_json`. **404** `NOT_FOUND`.

---

### GET /api/homeworks/{hw_id}/versions/{version_id}

**200** `{ "id": 7, "homework_id": "...", "title": "...", "saved_at": "...", "content_json": { ... } }`.
**404** `NOT_FOUND`. **400** `MISMATCH` — version belongs to a different homework.

---

### POST /api/homeworks/{hw_id}/versions/{version_id}/restore

Overwrites live `content_json` with the snapshot. Auto-saves a snapshot of current content first.

**200** `{ "ok": true, "restored_from_version": 7, "homework": { <HomeworkRecord> } }`.
**404** `NOT_FOUND`. **400** `MISMATCH`. **500** `RESTORE_FAILED`.

---

## Render

### GET /h/{hw_id}

Returns **HTML**. Permanent share URL for students.
`Cache-Control: public, max-age=300`.
Missing → friendly 404 HTML page. Trashed → friendly 409 HTML page. Both are HTML bodies, not JSON errors.

---

### GET /api/homeworks/{hw_id}/preview

Returns **HTML**. Same render as `/h/{hw_id}` but:
- `Cache-Control: no-store, no-cache, must-revalidate`
- Errors are JSON `HTTPException` (not HTML)

**404** `NOT_FOUND`. **409** `TRASHED`.

---

## Library

### GET /api/library

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `subject` | str | — | Exact match |
| `grade` | int | — | Exact match |
| `mode` | str | — | Exact match |
| `q` | str | — | LIKE on `title` and `content_json` blob |
| `limit` | int | 50 | 1–200 |
| `offset` | int | 0 | |

**200** `{ "items": [ { "id", "subject", "grade", "mode", "title", "chapter", "updated_at" } ], "total": N }`.
`chapter` = `content_json.meta.section`. Non-deleted only.

---

### GET /api/library/facets

**200** `{ "subjects": [...], "grades": [...], "modes": [...] }`. Distinct values from non-deleted rows.

---

## Quotes

### GET /api/quotes

Searchable quote library used by the builder's quote-picker modal. Returns matching items plus facets so the UI can populate its filter selects in one round-trip.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `q` | str | — | Substring search over text + author |
| `type` | str | — | Filter by type: `fact` or `quote` |
| `origin` | str | — | Filter by origin: `National` or `Global` |
| `category` | str | — | Filter by category |
| `author` | str | — | Filter by author |
| `limit` | int | 50 | 1–200 |
| `offset` | int | 0 | |

**200**
```json
{
  "items": [
    {
      "id": "...",
      "text": "...",
      "author": "...",
      "category": "...",
      "type": "quote|fact",
      "origin": "National|Global",
      "language": "uz|ru|en"
    }
  ],
  "total": N,
  "limit": 50,
  "offset": 0,
  "facets": {
    "types": ["quote", "fact"],
    "origins": ["National", "Global"],
    "categories": [...],
    "authors": [...]
  }
}
```

---

## Notebook

### POST /api/notebook/grade

Accept multipart photo upload with session/homework/question IDs; grade the handwritten formula and return grading result or rejection reason.

**Multipart fields:**
- `image` (file, required) — JPEG/PNG/WebP photo (1 KB – 5 MB)
- `session_id` (text, required) — client-side UUID
- `hw_id` (text, required) — homework record ID
- `question_id` (text, required) — question identifier within the homework

**200** on success or rejection (both include `rejected` flag):
```json
{
  "rejected": false,
  "photo_id": "ph-uuid",
  "transcribed_text": "x² + 2x + 1 = 0",
  "confidence": 0.92,
  "correct": true,
  "score_1_to_4": 4,
  "axis_1_concept_id": 3,
  "axis_2_process_integrity": 4,
  "feedback": "...",
  "matches_expected": true
}
```

**Rejection response** (HTTP 200, `rejected: true`):
```json
{
  "rejected": true,
  "reason": "invalid_file|vision_low_confidence|no_math_symbols|blank_or_scene|...",
  "retry_message_uz": "Rasmning sifati aniq emas...",
  "retry_message_ru": "...",
  "retry_message_en": "..."
}
```

Rejection reasons:
- `invalid_file` — unsupported MIME type or file size out of range
- `vision_low_confidence` — OCR confidence below threshold or empty transcription detected
- `no_math_symbols` — transcribed text contains no math operators/digits
- `blank_or_scene` — OpenCV pre-filter detected blank page or scene photo

---

### GET /api/notebook/captures

List all captures for a session (used by review/retry UI).

| Param | Type | Required |
|-------|------|----------|
| `session_id` | str | yes |
| `hw_id` | str | yes |

**200**
```json
{
  "captures": [
    {
      "id": "...",
      "session_id": "...",
      "hw_id": "...",
      "question_id": "...",
      "rejected": false,
      "reason": null,
      "photo_id": "...",
      "transcribed_text": "...",
      "confidence": 0.92,
      "correct": true,
      "created_at": "2026-04-30T10:00:00+00:00"
    }
  ]
}
```

---

## Grading

### POST /api/grading/aggregate

Take a session log (array of submitted answers) and return the scorecard payload. Pure compute — no DB involved. Replaces the old client-side `_amrAggregate` JS function.

```json
{
  "items": [
    {
      "phase": "memory-sprint",
      "correct": true,
      "axis_1": 3.5,
      "axis_2": 4.0
    }
  ],
  "session_id": "client-uuid",
  "homework_id": "HW-20260428-001",
  "warning_deductions": 0,
  "homework_failed": false
}
```

**200** Scorecard payload consumed by the Results screen:
```json
{
  "overall_pct": 85,
  "overall_score": 85.0,
  "overall_axis_1": 3.5,
  "overall_axis_2": 4.0,
  "band": {"key": "proficient", "name": "Proficient"},
  "perf_class": "perf-good",
  "has_axes": true,
  "phases": [
    {
      "key": "memory-sprint",
      "label": "Memory Sprint",
      "method": "closed",
      "is_phase_level": false,
      "correct": 5,
      "total": 5,
      "pct": 100.0,
      "perf_class": "perf-good",
      "score_text": "5/5",
      "axis_1_mean": null,
      "axis_2_mean": null
    }
  ],
  "axes": {
    "axis_1": {
      "mean": 3.5,
      "perf_class": "perf-good",
      "tag": "Developing"
    },
    "axis_2": {
      "mean": 4.0,
      "perf_class": "perf-good",
      "tag": "Proficient"
    }
  },
  "totals": {"correct": 45, "items": 50},
  "coaching_tip": "...",
  "action": {"kind": "finish", "label": "Tugatish", "perf_class": "is-finish"}
}
```

---

### GET /api/grading/rubric

Inspect the current grading rubric configuration. Useful for the dashboard (so teachers can see which phases produce which grade) and for tests.

**200**
```json
{
  "phase_method": {
    "memory-sprint": "closed",
    "story-mode": "closed",
    "adaptive-quiz": "closed",
    "sentence-fill": "closed",
    "tile-match": "closed",
    "real-life": "amr",
    "consolidation": "ungraded",
    "final-boss": "amr",
    "reflection": "ungraded",
    "theme-preview": "ungraded",
    "flash-cards": "ungraded"
  },
  "phase_display_order": [
    {"key": "memory-sprint", "label": "Memory Sprint", "phase_level": false},
    {"key": "story-mode", "label": "Story Mode", "phase_level": false},
    {"key": "adaptive-quiz", "label": "Adaptive Quiz", "phase_level": false},
    {"key": "sentence-fill", "label": "Sentence Fill", "phase_level": false},
    {"key": "tile-match", "label": "Tile Match", "phase_level": true},
    {"key": "real-life", "label": "Real-Life", "phase_level": false},
    {"key": "final-boss", "label": "Final Boss", "phase_level": false}
  ],
  "band_thresholds": [
    {"axis_avg_floor": 3.5, "key": "mastered", "name": "Mastered"},
    {"axis_avg_floor": 2.5, "key": "proficient", "name": "Proficient"},
    {"axis_avg_floor": 1.5, "key": "apprentice", "name": "Apprentice"},
    {"axis_avg_floor": 0.0, "key": "novice", "name": "Novice"}
  ],
  "finish_threshold_pct": 60
}
```

Legend:
- `phase_method`: `"closed"` = closed accuracy, `"amr"` = 2-axis rubric, `"ungraded"` = participation only
- `band_thresholds`: scoring bands applied to the 1–4 axis-mean scale (or overall % for closed-only sessions)
- `finish_threshold_pct`: score at or above which the Finish button is enabled (below: Redo button)

---

## AI Tutor

All AI endpoints accept and return JSON. On failure: `500` with `{ "error": "...", "code": "AI_ERROR" | "PROMPT_MISSING" | "TUTOR_BACKEND_ERROR" | "TUTOR_SESSION_CAP" }`.

### AI Error codes
- `AI_ERROR` — generic upstream LLM provider failure; client should retry
- `PROMPT_MISSING` — required prompt field is empty or missing
- `TUTOR_BACKEND_ERROR` — transient AI backend failure (LLM provider unavailable); client should retry
- `TUTOR_SESSION_CAP` — per-session message cap reached (60 turns max); no further turns can be appended

### POST /api/ai/check-answer

```json
{
  "question": "string",
  "student_answer": "string",
  "expected_answers": [],
  "question_id": "",
  "answer_spec": null,
  "allow_ai_fallback": true,
  "subject": "math-algebra",
  "grade": 8,
  "tier": "MEDIUM",
  "context": null,
  "phase": null
}
```
- `tier`: `"EASY"` | `"MEDIUM"` | `"HARD"`
- `phase`: optional grading-phase hint (added Wave D round 4)
- Only `question` and `student_answer` are required; all others have defaults

**200** `{ "correct": bool, "score": float, "feedback": "string", "matched_expected": "string|null" }`

---

### POST /api/ai/check-answer/finalize  *(PR #132 — Sentence Fill)*

Per-item perfect-fill bonus query. Aggregates the per-blank attempt log built up by prior `POST /api/ai/check-answer` calls during the same sentence-fill item, returns the `xp_bonus` and a per-blank summary.

```json
{
  "phase": "sentence-fill",
  "homework_id": "string",
  "item_id": "string"
}
```

- `phase` must be `"sentence-fill"` — other values return **400** `SF_BAD_PHASE`.
- `homework_id` / `item_id` reference the homework row and the specific sentence-fill item under `content_json`. The server reads the per-blank attempt history from in-memory state populated by earlier `/check-answer` calls.

**200**
```json
{
  "perfect_fill": bool,
  "xp_bonus": 100 | 0,
  "summary": {
    "blanks_correct": int,
    "blanks_total": int,
    "first_attempt_correct": int
  }
}
```

- `perfect_fill` is `true` only when **every** blank was solved AND **every** blank was solved on the first attempt. `xp_bonus` is `100` in that case, else `0`.
- `summary.first_attempt_correct` reflects how many blanks the student got right on attempt #1 (used by the runtime to surface a "perfect fill" badge). Missing per-blank attempt records (e.g., cold-call without prior `/check-answer` activity) are treated as missing — they don't count toward `blanks_correct`.

**Errors**

| Status | code | When |
|---|---|---|
| 400 | `SF_BAD_PHASE` | `phase` is not `"sentence-fill"` |
| 404 | `HW_NOT_FOUND` | homework_id does not resolve |
| 404 | `SF_ITEM_NOT_FOUND` | item_id does not resolve under that homework's content |

---

### POST /api/ai/check-answer  *(phase = `"tile-match"`, PR #137)*

Per-pair grading for the Tile Match mechanic. Same URL as the regular `/check-answer`; dispatch is gated on `phase="tile-match"` AND `homework_id` present (legacy AMR-shape callers without `homework_id` fall through to the regular handler).

**Request**
```json
{
  "phase": "tile-match",
  "homework_id": "string",
  "left_id": "tm_001",
  "right_id": "tm_002",
  "session_id": "string|null",
  "grade": 8
}
```

- `left_id` / `right_id` are pair ids the student selected from the side-disjoint `GB_TILE_MATCH` runtime global. Server matches a correct pair when `left_id == right_id` (the same pair-id is shared across each side's tile).
- `session_id` keys the in-memory `_TM_ATTEMPTS` tracker. Refreshing the runtime resets the session — XP/streak/timer all start over.
- `grade` is optional; falls back to the homework's authored grade. Drives the timer + recommended pair-count band (G1-2: 4 pairs / 180s, G3-4: 5 / 165s, G5-7: 6 / 150s, G8-11: 8 / 120s).

**200**
```json
{
  "correct": bool,
  "hint": "string|null",
  "explanation": "string|null",
  "xp": {
    "base": 100,
    "speed_bonus": 0 | 10 | 30 | 50,
    "streak_bonus": 0 | 50 | 75,
    "palace_bonus": 0 | 50,
    "branch_bonus": 0 | 100,
    "total": int
  },
  "timer": {
    "remaining_seconds": int,
    "delta_seconds": -5 | 0 | 3
  },
  "matched_count": int,
  "total_pairs": int,
  "complete": bool,
  "outcome": "perfect_clear|flawless|cleared|below_threshold|partial|null",
  "completion_bonus_xp": 0 | 100 | 200
}
```

- **Correct match**: `correct=true`, `xp.base=100`, `timer.delta_seconds=+3`. Speed bonus computed from POST-delta `remaining_seconds` per spec §5C: ≥50s → +50, 30–49s → +30, 1–29s → +10, ≤0 → 0.
- **Wrong match**: `correct=false`, `xp.base=0`, `timer.delta_seconds=-5`. `hint` returns the LEFT-side concept text of the right-tile's TRUE partner (the student already sees that left tile in the DOM, so this is not a new leak surface). Streak resets.
- **Streak bonus**: every 3rd consecutive correct match — `+50` (basic tier) or `+75` (premium tier) added to `xp.streak_bonus`.
- **Memory Palace bonus**: matching a pair authored with `is_palace_tile=true` (premium-only authoring) adds `+50` to `xp.palace_bonus`.
- **Branch-complete bonus**: matching the final pair of a `concept_family` adds `+100` to `xp.branch_bonus` (one-shot per family per session).
- **Already-matched defensive path**: claiming the same pair twice returns `correct=false` with all XP fields zero AND `timer.delta_seconds=0` (no penalty for double-clicks).
- **Premium `explanation`** field surfaces the authored teaching note when matching a `tier="premium"` pair correctly. Never echoes any other pair's right-side text.

**Outcome computation** (per spec §5A/5B, fires when `matched_count == total_pairs` OR `timer.remaining_seconds == 0`):

| Condition | `outcome` | `completion_bonus_xp` |
|---|---|---|
| `matched == total` AND `wrong_count == 0` | `perfect_clear` | 200 |
| `matched == total` AND `wrong_count == 1` | `flawless` | 100 |
| `matched == total` AND `wrong_count >= 2` | `cleared` | 0 |
| timer expired AND `matched/total < 0.6` | `below_threshold` | 0 (replay flagged) |
| timer expired AND `0.6 <= matched/total < 1.0` | `partial` | 0 |
| game in progress | `null` | 0 |

**Errors**

| Status | code | When |
|---|---|---|
| 400 | `TM_MISSING_HW` | `homework_id` missing on a `phase=tile-match` request |
| 400 | `TM_MISSING_IDS` | `left_id` or `right_id` missing |
| 400 | `TM_BAD_LEFT_ID` | `left_id` not in this homework's tile-match board |
| 400 | `TM_BAD_RIGHT_ID` | `right_id` not in this homework's tile-match board |
| 404 | `HW_NOT_FOUND` | homework_id does not resolve |
| 404 | `TM_NO_CONTENT` | homework has no `gb_tile_match` (or legacy `gb_memory_match`) content |

**Answer-leak protection**: the rendered runtime constant `GB_TILE_MATCH` is **side-disjoint** — every pair contributes two separate entries (`{id, side: "left", text}` and `{id, side: "right", text}`); left-tile entries never carry right text and vice versa. Cross-side matching happens exclusively at this endpoint; the client only ever sees IDs and prompts.

---

### POST /api/ai/check-answer  *(phase = `"real-life-challenge"`, PR #143)*

Per-step grading for the 5-step Real-Life Challenge mechanic. Same URL as the regular `/check-answer`; dispatch is gated on `phase="real-life-challenge"` AND `homework_id` present (legacy callers without `homework_id` fall through to the regular handler).

**Request**
```json
{
  "phase": "real-life-challenge",
  "homework_id": "string",
  "step_id": "step1",
  "session_id": "string|null",
  "selected_option_id": "a|b|c|...",
  "selected_chip_id": "string|null",
  "reasoning_text": "string|null"
}
```

- `step_id` ∈ `{"step1", "step2", "step3", "step4", "step5"}` matching the case's 5 steps in order: `decision → info_request → final_decision → concept_select → reasoning`.
- Only ONE of `selected_option_id` / `selected_chip_id` / `reasoning_text` is used per request, gated by the step's `kind`. Sending the wrong payload kind for a step returns `400 RLC_PAYLOAD_KIND_MISMATCH`.
- `session_id` keys the in-memory `_RLC_ATTEMPTS` tracker. Refreshing the runtime resets the session.

**200**
```json
{
  "step_id": "step1",
  "kind": "decision|info_request|final_decision|concept_select|reasoning",
  "correct": true,
  "consequence": "string|null",
  "correct_option_label": "string|null",
  "reasoning_score": "int|null",
  "reasoning_feedback": "string|null",
  "xp": {
    "decision_quality": 50,
    "reasoning_quality": 0,
    "concept_id": 0,
    "step_total": 50
  },
  "step_index": 0,
  "total_steps": 5,
  "complete": false,
  "outcome": "expert_decision|strong_analysis|passing|hali_emas|null",
  "completion_bonus_xp": 0,
  "total_xp": 50,
  "rubric_breakdown": null
}
```

- **Decision steps** (1, 2, 3): `correct` echoes correctness; on first wrong attempt, server returns `correct=false` with `correct_option_label=null` (encourage retry); on second wrong attempt, server returns `correct_option_label=<label of the right option>` for pedagogical reveal.
- **`consequence` text** surfaces ONLY on a wrong decision (mentor hint). Correct decisions return `consequence: null` to keep the no-leak invariant strict.
- **Concept-select** (step 4): single attempt, no retry policy.
- **Reasoning** (step 5): server enforces `min_chars` (default 80); short submissions return `400 RLC_REASONING_TOO_SHORT` before any AI call. AI grader returns `{score: 0-100, feedback: str}`; `xp.reasoning_quality = score` (1:1 map).
- **On step 5 graded** → `complete: true`. Server applies outcome multiplier per spec §5:
  - 90–100% → `outcome="expert_decision"`, `completion_bonus_xp=50`, `total_xp = sum + 50`
  - 75–89% → `outcome="strong_analysis"`, no bonus
  - 60–74% → `outcome="passing"`, `total_xp = round(sum * 0.8)` (no bonus)
  - <60% → `outcome="hali_emas"`, `total_xp = round(sum * 0.4)`
- **`rubric_breakdown`** is populated only on `complete=true`; surfaces `{decision_quality, reasoning_quality, concept_id, bonus, total}` for the closure card.

**Per-step XP allocation (sums to spec §5's 300 max):**

| Step kind | XP credited to | Cap |
|---|---|---|
| `decision` (step 1) | `decision_quality` | 50 |
| `info_request` (step 2) | `decision_quality` | 50 |
| `final_decision` (step 3) | `decision_quality` | 50 |
| `concept_select` (step 4) | `concept_id` | 50 |
| `reasoning` (step 5) | `reasoning_quality` | 100 |

**Errors**

| Status | code | When |
|---|---|---|
| 400 | `RLC_BAD_PHASE` | dispatch gate hit but case-resolution fails |
| 400 | `RLC_PAYLOAD_KIND_MISMATCH` | step kind doesn't match the field provided (e.g., `selected_chip_id` for a decision step) |
| 400 | `RLC_REASONING_TOO_SHORT` | reasoning_text shorter than the step's `min_chars` |
| 404 | `HW_NOT_FOUND` | homework_id does not resolve |
| 404 | `RLC_CASE_NOT_FOUND` | homework has no `real_life_challenge` content |
| 404 | `RLC_STEP_NOT_FOUND` | step_id is not one of the case's 5 step ids |

**Answer-leak protection:** the rendered runtime constant `RLC_CASE` is side-disjoint — `is_correct` flags on options + chips, per-option `consequence`, and per-step `acceptable_keywords` are stripped server-side before injection. Grading happens exclusively at this endpoint.

---

### POST /api/ai/check-answer  *(phase = `"final-boss"`, PR #N)*

Per-turn grading for the Final Boss mechanic. Same URL as the regular `/check-answer`; dispatch is gated on `phase="final-boss"` AND `homework_id` present (legacy callers without `homework_id` fall through to the regular handler). Internally adapts the `CheckAnswerRequest` shape into a `BossTurnRequest` and delegates grading to `tutor.boss_turn` — same AMR 2-axis output.

**Request**
```json
{
  "phase": "final-boss",
  "homework_id": "string",
  "question_id": "E1",
  "student_answer": "string",
  "session_id": "string|null",
  "boss_type": "sub|big|mythical",
  "grade_band": "g1_4|g5|g6_8|g9_11|null",
  "hp_remaining": 100,
  "attempt_number": 1,
  "attempts_used": 0,
  "subject": "math-algebra",
  "grade": 8
}
```

- `question_id` references one of the homework's `boss_questions[].id` values.
- `boss_type` defaults to `"sub"` (current production mechanic). `"big"` and `"mythical"` are forward-compat schema-recognized but their full runtime engines are deferred (see "Out of scope" in the FB plan).
- `grade_band` drives default starting HP (g1_4: 50, g5: 100, g6_8: 100, g9_11: 150 per spec §6) and hint cost (g1_4: +5, g5: +10, g6_8: +10, g9_11: +15 per spec §8). Per-question `hint_cost_per_use` overrides the band default if authored.
- `session_id` keys the in-memory `_FB_ATTEMPTS` tracker. Refreshing the runtime resets the session.

**200**
```json
{
  "correct": bool,
  "damage_dealt": int,
  "boss_response": "string|null",
  "hint": "string|null",
  "score": 0.0..1.0,
  "axis_1": int,
  "axis_2": int,
  "hp_remaining": int,
  "outcome": "expert|strong|passing|hali_emas|null",
  "stars": "1|2|3|null",
  "outcome_xp": int,
  "boss_type_used": "sub|big|mythical",
  "done": bool
}
```

- **`damage_dealt`**: applied on correct match; doubled when the boss is in a 3-streak combo state (server-tracked).
- **`hp_remaining`** is server-authoritative; clients echo their last-known value but the server's value is canonical.
- **`outcome` / `stars` / `outcome_xp`** populated ONLY when `done=true` (boss defeated OR HP depleted). Per spec §11:

| Condition | `outcome` | `stars` | `outcome_xp` (Sub / Big / Mythical) |
|---|---|---|---|
| First attempt + zero hints + `hp >= max_hp * 0.8` | `expert` | 3 | 1000 / 2000 / 5000 |
| Attempt ≤ 2 + `hp > max_hp * 0.5` | `strong` | 2 | 700 / 1500 / 0 |
| Boss defeated, any other path | `passing` | 1 | 500 / 1000 / 0 |
| Boss not defeated (HP depleted) | `hali_emas` | 0 | 0 |

- **Mythical Boss** rewards XP only on a 3-star defeat (per spec §11). Lesser star outcomes return `outcome_xp: 0`.
- **`done`** is set true on the final turn; runtime trips end-of-fight transition.

**Errors**

| Status | code | When |
|---|---|---|
| 400 | `FB_MISSING_HW` | `homework_id` missing on a `phase=final-boss` request |
| 404 | `HW_NOT_FOUND` | homework_id does not resolve |
| 404 | `FB_NO_CONTENT` | homework has no `boss_questions` |
| 404 | `FB_QUESTION_NOT_FOUND` | `question_id` is not one of the homework's boss-question ids |

**Answer-leak protection**: the rendered runtime constant `BOSS_QUESTIONS` is **stripped server-side** of `accepted[]`, `ans`, `accepted_answers`, and `answer_spec` before client injection. Grading happens exclusively at this endpoint (or its legacy sibling `/api/ai/boss-turn`). The transitional `_BOSS_LEGACY_CLIENT_MATCH` flag (default `False`) preserves the leak fix; only test/replay paths that need the old shape may toggle it.

The optional sibling field `content_json.boss_meta` carries phase-level metadata (boss_type, grade_band, attempts_max, anti_cheat policy, starting_hp_override) and is injected into the runtime as `BOSS_META` (or `null` if absent). Existing homework rows without `boss_meta` continue to render unchanged.

---

### POST /api/ai/boss-turn

Legacy canonical endpoint for the Final Boss mechanic. The `phase=final-boss` branch on `/api/ai/check-answer` (above) adapts to this same grading path; both endpoints coexist.

```json
{
  "boss_question": "string",
  "student_answer": "string",
  "expected_answers": [],
  "damage_value": 10,
  "hp_remaining": 100,
  "attempt_number": 1,
  "subject": "math-algebra",
  "grade": 8,
  "boss_type": "sub|big|mythical|null",
  "grade_band": "g1_4|g5|g6_8|g9_11|null",
  "attempts_used": 0,
  "session_id": "string|null"
}
```
`damage_value`: 0–50. `attempt_number`: ≥ 1. The four trailing fields (`boss_type`, `grade_band`, `attempts_used`, `session_id`) are optional — added in the FB redesign; legacy callers may omit them safely.

**200**
```json
{
  "correct": bool,
  "damage_dealt": int,
  "boss_response": "string",
  "hint": "string|null",
  "score": float,
  "axis_1": int,
  "axis_2": int,
  "hp_remaining": int,
  "outcome": "expert|strong|passing|hali_emas|null",
  "stars": "1|2|3|null",
  "outcome_xp": int,
  "done": bool
}
```

`outcome` / `stars` / `outcome_xp` populate only on the final turn (`done=true`). See the table under `phase=final-boss` above for the rubric.

---

### POST /api/ai/reflection

```json
{
  "student_reflection": "string",
  "homework_title": "",
  "homework_summary": "",
  "performance": {},
  "subject": "math-algebra",
  "grade": 8
}
```
`performance` keys: `correct`, `total`, `time_minutes`, `weak_phase` (all optional).

**200** `{ "feedback": "string", "next_steps": [...], "encouragement": "string" }`

---

### POST /api/ai/tutor

```json
{
  "phase": "general",
  "question": "string",
  "student_input": "",
  "subject": "math-algebra",
  "grade": 8,
  "context": null
}
```

**200** `{ "response": "string", "guidance_type": "string" }`

---

### POST /api/ai/tutor/chat  *(Wave F1)*

Live, persistent tutor chat. Each call appends one user turn and one assistant turn to `tutor_conversations` and returns the assistant's reply.

```json
{
  "session_id": "client-uuid",
  "hw_id": "HW-20260428-001",
  "phase": "preview|practice|boss",
  "question_id": "qb1",
  "message": "string"
}
```
- `question_id` is optional — required only when the chat is scoped to a specific question (practice/boss).
- For `phase != "preview"`, the server strips `expected`, `ans`, `accepted_answers`, and `correct` from the question payload before it enters the LLM context.
- Per-(session_id, hw_id) cap of **60 total turns**. The 61st request returns **429** `TUTOR_SESSION_CAP`.

**200** `{ "response": "string", "message_id": int }`. **429** when the cap is reached. **500** `TUTOR_BACKEND_ERROR` on a transient AI-backend failure.

---

### POST /api/ai/tutor/boss-plan  *(Wave F1)*

Builds a personalized boss-question plan from `boss_questions[]` in the homework's `content_json`. Reorders the pool and emits a short student-facing framing for each question (≤180 chars). Question stems and `answer_spec` are unchanged — deterministic grading still works byte-identically.

```json
{
  "session_id": "client-uuid",
  "hw_id": "HW-20260428-001"
}
```

**200**
```json
{
  "ordered": [{ "question_id": "qb1", "framing_text": "Warm-up first." }],
  "persona_traits": ["challenger" | "mentor" | "analyst"]
}
```
On any LLM failure or invalid response, the server returns a default fallback: input order, `persona_traits = ["mentor"]`, neutral framing.

---

### GET /api/ai/tutor/history  *(Wave F1)*

| Param | Type | Required |
|-------|------|----------|
| `session_id` | str | yes |
| `hw_id` | str | yes |

Returns chronological turns (oldest first), capped at 50.

**200** `{ "turns": [{ "id", "session_id", "hw_id", "phase", "question_id", "role", "content", "created_at" }] }`

---

### GET /api/ai/status

**200**:
```json
{
  "backend": "kimi|vertex|gemini_api|none",
  "model_fast": "gemini-2.5-flash",
  "model_pro": "gemini-2.5-pro",
  "active_provider": "kimi",
  "preference_list": ["kimi", "vertex", "gemini_api"],
  "available_providers": ["kimi"]
}
```
- `active_provider` — name of the provider currently selected (first available in `preference_list`).
- `preference_list` — ordered list read from `AI_BACKEND_PREFERENCE` env (default `kimi,vertex,gemini_api`).
- `available_providers` — all registered providers whose credentials are present.
- `backend` is a legacy alias for `active_provider` — kept for backward compat.
When `active_provider == "vertex"`: also includes `project`, `location`, `credentials_path`.

---

## Review Queue

### GET /api/ai/review-queue

Returns all `status = "pending"` items.

**200** array of `{ "id": int, "question_id": "string", "student_answer": "string", "answer_spec": {...}, "ai_response": {...}, "status": "pending", "created_at": "..." }`.

---

### POST /api/ai/review-queue/{id}/decide

```json
{ "correct": true, "score": 1.0, "feedback": "string" }
```

**200** `{ "status": "ok" }`. **404** — item not found or already resolved.

---

## Answer-Spec Preview

### POST /api/ai/answer-spec/preview

```json
{ "answer_spec": { "type": "numeric", "expected": 42, "tolerance": 0.5 } }
```
`type`: `"numeric"` | `"set_match"` | `"text_fuzzy"` | `"semantic"`.

**200** `{ "examples": ["42.0", "42.5", "41.5"] }`

---

## Internationalization (i18n)

Client-side translation layer (Wave I1+) exposes `window.i18n` and `window.STRINGS` in all frontend pages. Server populates `NETS_CTX.lang` from the homework's `language` DB column (default `'uz'`).

### `window.i18n` API

| Method | Signature | Notes |
|--------|-----------|-------|
| `t(key, fallback)` | `(string, ?string) → string` | Resolve key in current lang; chain: `current → en → uz → fallback → key` |
| `setLang(lang)` | `(string) → void` | Set active lang (`'uz'` \| `'ru'` \| `'en'`); writes `localStorage.nets_lang`, updates `<html lang>`, re-renders all `data-i18n*` attrs, fires `onChange` callbacks |
| `getLang()` | `() → string` | Get active lang; resolves from `localStorage.nets_lang → <html lang> → 'en'` |
| `onChange(cb)` | `(callback) → void` | Register function called on `setLang()` |

### `window.STRINGS` shape

```javascript
{
  uz: { "dashboard.btn_new_hw": "...", "builder.save": "...", ... },
  ru: { "dashboard.btn_new_hw": "...", ... },
  en: { "dashboard.btn_new_hw": "...", ... }
}
```

**Key naming convention:** `page.element_role` (e.g., `dashboard.btn_new_hw`, `builder.input_placeholder`, `library.title_text`). ~111 keys across dashboard, builder, library, common subsections (I2 in flight).

### HTML attribute wrappers

Four attributes auto-render on page load and after `setLang()`:

| Attribute | Target | Example |
|-----------|--------|---------|
| `data-i18n="key"` | `textContent` | `<button data-i18n="dashboard.btn_new_hw">…</button>` |
| `data-i18n-placeholder="key"` | input `placeholder` | `<input data-i18n-placeholder="builder.input_q">` |
| `data-i18n-aria-label="key"` | `aria-label` | `<button data-i18n-aria-label="common.close">…</button>` |
| `data-i18n-title="key"` | `title` attr | `<span data-i18n-title="common.tooltip">hover me</span>` |

### Resolution & fallback chains

**Language resolution** (when page loads, or `i18n.getLang()` called):
```
localStorage.nets_lang (if set) → <html lang> value → 'en' (final fallback)
```

**String resolution** in `t(key, fallback)`:
```
STRINGS[current_lang][key] → STRINGS['en'][key] → STRINGS['uz'][key] → fallback arg → key string
```

### Adding a new translatable string

1. **Add to all 3 languages** in `frontend/js/i18n/strings.js`:
   ```javascript
   STRINGS.uz.new_page_title = "...";
   STRINGS.ru.new_page_title = "...";
   STRINGS.en.new_page_title = "...";
   ```

2. **Use in HTML** (auto-translates on load + on `setLang()`):
   ```html
   <h1 data-i18n="new_page_title">English fallback text</h1>
   ```
   OR **in JavaScript** (manual):
   ```javascript
   el.textContent = i18n.t('new_page_title', 'English fallback');
   ```

### HTML `<html lang>` convention

- **Dashboard pages** (`/`, `/builder.html`, `/library.html`): `<html lang="en">` (static fallback; no dynamic language changes)
- **Runtime template** (`perfect_homework.html`, `/h/{id}`): `<html lang="uz">` (student-facing default; respects `localStorage.nets_lang` switch)

---

## Meta

### GET /api/health

**200** `{ "status": "ok", "ai_backend": "vertex|...", "ai_ready": bool, "gemini": bool }`. `gemini` is a legacy alias for `ai_ready`.

---

### GET /api/subjects

**200**:
```json
{
  "subjects": [ { "id": "math-algebra", "family": "aniq-fanlar", "always_hard": false, "grades": [8, 9] } ],
  "families": { "aniq-fanlar": "#hexcolor", ... },
  "statuses": { "draft": "#hexcolor", ... },
  "phase_names": { "phase_key": "Display Name", ... },
  "phase_icons": { "phase_key": "...", ... },
  "pipelines": { "aniq-fanlar:hard": ["phase1", ...], ... }
}
```

---

### GET /api/fixtures

Lists fixture templates. Excludes files prefixed `_` or `tutor-`.

**200** `{ "fixtures": [ { "name", "title", "subject", "subject_display", "grade", "mode", "cefr_level" } ] }`

---

### GET /api/fixtures/{name}

`name`: lowercase letters, digits, hyphens only. Returns raw `content_json` object.

**400** `INVALID_NAME`. **404** `NOT_FOUND`. **500** `FIXTURE_MALFORMED`.

---

## Trash

### GET /api/trash

All soft-deleted rows, newest-deleted first.

**200** `{ "items": [ <HomeworkRecord>, ... ], "count": N }`

---

## Admin

### POST /api/admin/checkpoint

Forces a SQLite WAL checkpoint. No request body.

**200** `{ "ok": true }`

---

## Example: create → update → render

```bash
# 1. Create
curl -s -X POST http://localhost:8000/api/homeworks \
  -H "Content-Type: application/json" \
  -d '{"title":"Kvadrat tenglama","subject":"math-algebra","grade":8,"mode":"hard"}' \
  | jq '{id, status}'
# → { "id": "HW-20260427-001", "status": "draft" }

# 2. Populate content
curl -s -X PUT http://localhost:8000/api/homeworks/HW-20260427-001 \
  -H "Content-Type: application/json" \
  -d '{"content_json": { ... }}'

# 3. Render (browser or curl — returns HTML)
curl http://localhost:8000/h/HW-20260427-001
```

---

## Gotchas

- **Trashed homeworks** return `409 TRASHED` (not 404) on `PUT`, `duplicate`, and `preview`. Use `POST /…/restore` first.
- **Soft-delete idempotency**: deleting an already-trashed homework returns `200`, not an error.
- **ID format**: `HW-YYYYMMDD-NNN` — sequential per day; always a string.
- **`/h/{id}` vs `/preview`**: same HTML, different cache headers and error format.
- **Library slimmed row**: adds `chapter`, drops `content_json`, `family`, `language`, `status`, `deleted_at`.
