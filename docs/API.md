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
| AI meta | GET /api/ai/status, POST /api/ai/session/final-report |
| Review queue | GET /api/ai/review-queue, POST /api/ai/review-queue/{id}/decide |
| Answer-spec | POST /api/ai/answer-spec/preview |
| Notebook | POST /api/notebook/grade, GET /api/notebook/captures |
| Grading | POST /api/grading/aggregate, GET /api/grading/rubric |
| Equations | POST /api/equations/validate |
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

### GET /api/homeworks/{hw_id}/migration-status

Reports whether the stored `content_json` would change shape under the current runtime normalizer. Read-only — does NOT mutate the row. Used by the builder UI to decide whether to surface the **Migrate content** button.

```json
{
  "ok": true,
  "id": "HW-20260427-001",
  "needs_migration": true,
  "added_keys": ["gb_tile_match", "meta.cefr_level"],
  "changed_keys": ["flashcards"],
  "normalized_key_count": 18
}
```

- `needs_migration` — `true` when normalization would add or change at least one top-level / dotted key, `false` if the stored blob already matches the normalizer's output.
- `added_keys` — keys the normalizer would add to the stored blob.
- `changed_keys` — keys whose stored value differs from the normalized value.
- `normalized_key_count` — count of top-level keys after normalization (sanity figure for the UI badge).

**200** status payload above. **404** `NOT_FOUND`.

---

### POST /api/homeworks/{hw_id}/migrate-content

Persists the normalized `content_json` to the stored row. Idempotent — calling on an already-migrated row returns `migrated: false` without writing. Boss question advisory levels and IDs are normalized in the same pass.

```json
{
  "ok": true,
  "id": "HW-20260427-001",
  "migrated": true,
  "needs_migration": false,
  "added_keys": ["gb_tile_match", "meta.cefr_level"],
  "changed_keys": ["flashcards"],
  "homework": { <HomeworkRecord> }
}
```

When the row already matches the normalizer (no-op):

```json
{ "ok": true, "id": "...", "migrated": false, "needs_migration": false, "added_keys": [], "changed_keys": [], "homework": { <HomeworkRecord> } }
```

**200** payload above. **404** `NOT_FOUND`. **409** `TRASHED` — restore before migrating.

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

### AI context debug

`AI_DEBUG_CONTEXT` is an optional server environment flag. Truthy values are `1`, `true`, `yes`, `on`, and `debug`.

When unset or false, AI endpoint response shapes are unchanged. When enabled, these endpoints may include a top-level `context_debug` object:

- `POST /api/ai/check-answer`
- `POST /api/ai/boss-turn`
- `POST /api/ai/tutor/chat`
- `POST /api/ai/tutor/boss-plan`
- `GET /api/ai/tutor/history`

`context_debug` is metadata-only. It may include route/service names, phase/subphase, id presence flags, safe counts/lengths, selected provider/model, prompt size, checker path/source/result action, fallback or `ai_unavailable` status, boss HP before/after, and similar diagnostics. It must not include raw `screen_context`, raw `student_answer`, expected answers, answer keys, prompts, or chat-history text. The same sanitized metadata is logged on `nets.ai.context`; raw student text and answer-bearing content are never logged by this debug helper.

### POST /api/ai/runtime/submit-answer

Evaluates a student's answer using a phase-aware grading pipeline and persists the attempt. It resolves context server-side based on `session_id`, `homework_id`, `phase`, and `question_id`.

**Request Body:**
```json
{
  "session_id": "string",
  "homework_id": "string",
  "phase": "string",
  "question_id": "string",
  "answer_type": "string",
  "student_answer": "any",
  "student_work_text": "string",
  "attempt_number": 1
}
```

**Response Body:**
```json
{
  "ok": true,
  "grading_method": "deterministic | ai_judge",
  "is_correct": true,
  "score": 1.0,
  "confidence": 0.95,
  "feedback": "string",
  "misconception_tags": ["string"],
  "next_hint": "string",
  "requires_review": false,
  "attempt_number": 1
}
```

**400** `MISSING_QUESTION_ID` when `question_id` is absent. **404** `HW_NOT_FOUND` or `QUESTION_NOT_RESOLVED`. **422** `ANSWER_TARGET_NOT_GRADABLE` when the resolved backend item lacks trusted question text or answer material. AI judging routes through `ai_gateway` task `ANSWER_CHECK`; deterministic grading can still answer without an AI call.

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

With `AI_DEBUG_CONTEXT=true`, the same response may include top-level `context_debug` with metadata such as `checker_path`, `source`, `answer_spec_type`, `confidence`, `result_action`, and `ai_unavailable`.

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

### POST /api/ai/check-answer  *(phase = `"ttt"`)*

Resolves a single TTT cell-claim attempt. Server holds the answer key (side-disjoint injector pattern); client never sees `correct` until after resolve.

**Request**
```json
{
  "phase": "ttt",
  "homework_id": "string",
  "item_id": "ttt-1",
  "picked": "56"
}
```

- `item_id` references one of the homework's `gb_ttt[].id` values as populated by `injector._serialize_ttt` at render time.
- `picked` is the option string the student tapped. Falls back to `student_answer` if `picked` is omitted (legacy compatibility).

**200**
```json
{
  "is_correct": bool,
  "mercy": bool,
  "xp_delta": int,
  "correct_value": "string"
}
```

- **`is_correct`**: `true` when `picked` exactly matches the server-held correct value.
- **`mercy`**: server-rolled lucky bounce (0.2% chance, i.e. `mercy_chance=0.002`). When `true`, the student receives `xp_mercy` XP even on a wrong pick. `gb_ttt_config.mercy_chance` overrides the default.
- **`xp_delta`**: XP awarded for this pick. Default rules: +50 correct (`xp_correct`), +10 mercy bounce (`xp_mercy`), 0 wrong. `gb_ttt_config` overrides any of these per homework.
- **`correct_value`**: the answer the server holds for this item. Returned only after resolution (client-side cell already consumed by this point; max 9 probes per game).

**Errors**

| Status | code | When |
|---|---|---|
| 400 | `TTT_MISSING_HW` | `homework_id` missing on a `phase=ttt` request |
| 400 | `TTT_MISSING_ITEM_ID` | `item_id` missing or empty |
| 404 | `HW_NOT_FOUND` | homework_id does not resolve |
| 404 | `ttt_item_not_found` | `item_id` not in this homework's answer key (homework not yet rendered, or unknown id) |

**Answer-leak protection**: the rendered runtime constant `GB_TTT` is stripped server-side of `correct` and `distractors`; client only receives `{id, q, options[]}` where `options` is the shuffled choice list. The correct answer lives exclusively in `_TTT_ANSWER_KEY[hw_id][item_id]` (populated by `injector._serialize_ttt`) and is validated only at this endpoint.

---

### POST /api/ai/check-answer  *(phase = `"ttt-session"`)*

Tallies session XP at end of 3 games. Per-correct XP already paid out via `phase=ttt`; this route adds outcome XP (+200/draw, +300/win) plus the strong-session bonus (+100 if ≥2 draws). Returns mastery tier label and Duolingo-remediation flag (true if 0 wins + 0 draws).

**Request**
```json
{
  "phase": "ttt-session",
  "homework_id": "string",
  "results": [
    { "outcome": "win" },
    { "outcome": "draw" },
    { "outcome": "loss" }
  ]
}
```

- `results` is a list of `{"outcome": "win"|"draw"|"loss"}` dicts, one per completed game. Length 1 to `session_games` (default 3); longer lists are silently truncated to `session_games`.
- Per-correct-pick XP (+50 each) was already paid out during `phase=ttt` calls; this route accounts for outcome-level XP and the strong-session bonus only.

**200**
```json
{
  "session_xp": int,
  "strong_session_bonus": int,
  "mastery_tier": "string",
  "duolingo_remediation": bool,
  "wins": int,
  "draws": int,
  "losses": int
}
```

- **`session_xp`**: total outcome XP for the session (`wins × xp_win + draws × xp_draw + strong_session_bonus`). Does not include per-pick XP from `phase=ttt` calls.
- **`strong_session_bonus`**: flat bonus added when `draws >= 2`. Default +100 (`xp_strong_session`). 0 otherwise.
- **`mastery_tier`**: label derived from `(wins + draws) / total_games`:

| % wins + draws | tier |
|---|---|
| 0–<20% | Learning the Board |
| 20–<40% | Holding Ground |
| 40–<60% | Formidable Opponent |
| ≥60% | Unbreakable |

- **`duolingo_remediation`**: `true` when `wins == 0 AND draws == 0` — signals the runtime to surface remediation content.

**Errors**

| Status | code | When |
|---|---|---|
| 400 | `TTT_MISSING_HW` | `homework_id` missing on a `phase=ttt-session` request |
| 400 | `TTT_MISSING_RESULTS` | `results` field absent or not a list |
| 404 | `HW_NOT_FOUND` | homework_id does not resolve |

---

### POST /api/ai/check-answer  *(phase = `"memory-palace"`)*

Tallies a Memory Palace session at the end of the recall test. Server **recomputes `is_correct` server-side** by walking the submitted `placements` map (the "answer key" here is student-generated, not author-supplied — see plan §1.3 for rationale; tampering defense rather than side-disjoint pattern). Returns outcome label, accuracy, average recall speed, and a cosmetic `session_xp_display` (XP economy is aesthetic-only in v1; not persisted).

**Request**
```json
{
  "phase": "memory-palace",
  "homework_id": "string",
  "palace_key": "string",
  "placements": [
    { "location_idx": 0, "concept_id": "concept-abc" }
  ],
  "recall_results": [
    { "location_idx": 0, "picked_concept_id": "concept-abc", "is_correct": true, "elapsed_ms": 1200 }
  ],
  "mp_hints_used": 0
}
```

- `palace_key`: identifies which palace route the student walked (must be a key in `gb_memory_palace.palaces`).
- `placements`: the Step-2 location-to-concept bindings the student authored. Server uses these as the answer key to recompute `is_correct`.
- `recall_results`: the Step-4 picks. `is_correct` values from the client are **ignored** — server recomputes from `placements`. `elapsed_ms` is trusted.
- `mp_hints_used`: optional, default `0`. Reserved for future XP shaping; cosmetic only in v1.

**200**
```json
{
  "outcome": "perfect"|"yaxshi"|"hali_emas_partial"|"hali_emas_fail",
  "outcome_title": "string",
  "outcome_text": "string",
  "accuracy_pct": 100,
  "correct_count": 5,
  "total_count": 5,
  "recall_speed_avg_s": 1.2,
  "level_label": "string",
  "session_xp_display": 450,
  "retry_offered": false,
  "missed_location_indices": []
}
```

- **`outcome`**: one of four result buckets (see threshold table below).
- **`outcome_title` / `outcome_text`**: Uzbek-localised display strings.
- **`accuracy_pct`**: `round(correct_count / total_count * 100)`.
- **`recall_speed_avg_s`**: average `elapsed_ms / 1000` across all recall picks (1 decimal place).
- **`level_label`**: cosmetic mastery label based on outcome.
- **`session_xp_display`**: `correct_count × 50` + outcome bonus (`+200` perfect, `+100` yaxshi, `+0` otherwise). **Not persisted.**
- **`retry_offered`**: `true` unless outcome is `"perfect"`.
- **`missed_location_indices`**: sorted list of `location_idx` values where recall was wrong.

**Outcome thresholds**

| correct / total | outcome | level_label |
|---|---|---|
| 5/5 (all correct) | `perfect` | Proficient |
| 4/5 (one miss) | `yaxshi` | Apprentice ↗ |
| 3/5 (≥ 60 %) | `hali_emas_partial` | Apprentice |
| ≤ 2/5 | `hali_emas_fail` | Pending |

**Errors**

| Status | code | When |
|---|---|---|
| 400 | `MP_MISSING_HW` | `homework_id` missing on a `phase=memory-palace` request |
| 400 | `MP_MISSING_PALACE_KEY` | `palace_key` missing or empty |
| 400 | `MP_MISSING_PLACEMENTS` | `placements` absent or empty list |
| 400 | `MP_MISSING_RECALL` | `recall_results` absent or empty list |
| 404 | `homework_not_found` | `homework_id` does not resolve |

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

With `AI_DEBUG_CONTEXT=true`, the same response may include top-level `context_debug` with metadata such as fixed/dynamic mode, session presence, history count when available, question source, HP before/after, difficulty when available, provider/model, and `ai_unavailable`.

---

## Dynamic Boss (Plan 5) — net-new endpoints

The five `/api/ai/boss/*` endpoints below implement Plan 5 (`docs/AI Architecture plan/.../05_DYNAMIC_BOSS_AI_PLAN.md`). They generate boss questions adaptively from the student's session metrics rather than reading from `content_json.boss_questions[]`. The legacy `/api/ai/boss-turn` (above) and the static `boss_questions` content path remain untouched as fallbacks for older homework HTML.

Backend owns HP, trials, and difficulty. The model never receives `answer_spec.expected` / `accepted_answers` / prior question answer keys. The damage formula and difficulty policy live server-side; any model-supplied `damage_multiplier` is clamped to `[0.0, 1.5]`.

### POST /api/ai/boss/start

```json
{
  "session_id": "string",
  "homework_id": "string",
  "max_hp": 100,
  "trials_left": 7,
  "initial_difficulty": "medium"
}
```
`initial_difficulty` is one of `easy | medium | hard`. Idempotent: if an active boss session already exists for `(session_id, homework_id)`, returns it.

**200**
```json
{
  "boss_session_id": "bs_<hex>",
  "hp": 100,
  "max_hp": 100,
  "trials_left": 7,
  "current_difficulty": "medium",
  "weak_topics": ["string"],
  "strong_topics": ["string"],
  "missing_context_flags": ["string"]
}
```

### POST /api/ai/boss/generate-question

```json
{
  "boss_session_id": "string",
  "recent_boss_phrases": ["string"]
}
```

**200**
```json
{
  "question_id": "gbq_<hex>",
  "question_text": "string",
  "target_skill": "string",
  "difficulty": "easy|medium|hard",
  "why_this_question": "string",
  "boss_session_id": "string"
}
```
`expected_answer` and `rubric` are stored server-side and never returned to the frontend. **502** with `code=BOSS_GEN_REJECTED` if the generator output fails validation (missing answer/rubric, paraphrase of an asked question, invalid difficulty, too long).

### POST /api/ai/boss/submit-answer

```json
{
  "boss_session_id": "string",
  "question_id": "string",
  "student_answer": "string"
}
```

**200**
```json
{
  "is_correct": true,
  "score": 0.92,
  "confidence": 0.88,
  "feedback": "string",
  "damage": 15,
  "hp": 85,
  "trials_left": 6,
  "current_difficulty": "medium",
  "boss_status": "active|won|failed",
  "should_retry_same_skill": false,
  "misconception_tags": ["string"]
}
```

### POST /api/ai/boss/state

```json
{ "boss_session_id": "string" }
```

**200** — full hydrated boss-session row (HP / trials / difficulty / asked queue / current question summary). Used by the runtime to recover after a refresh.

### POST /api/ai/boss/give-up

```json
{ "boss_session_id": "string" }
```

Marks the boss session as `abandoned`; subsequent `generate-question` / `submit-answer` calls return **409**.

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
  "message": "string",
  "screen_context": "string",
  "student_work_text": "string",
  "subphase": "string",
  "ui_state": {},
  "recent_assistant_phrases": ["string"]
}
```
- `phase` is optional (defaults to `"preview"`).
- `question_id` is optional — required only when the chat is scoped to a specific question (practice/boss).
- `screen_context`, `student_work_text`, `subphase`, `ui_state`, and `recent_assistant_phrases` are optional context enrichment fields.
- For `phase != "preview"`, the server strips `expected`, `ans`, `accepted_answers`, and `correct` from the question payload before it enters the LLM context.
- Per-(session_id, hw_id) cap of **60 total turns**. The 61st request returns **429** `TUTOR_SESSION_CAP`.

**200** `{ "response": "string", "message_id": int }`. **429** when the cap is reached. **500** `TUTOR_BACKEND_ERROR` on a transient AI-backend failure.

With `AI_DEBUG_CONTEXT=true`, the same response may include top-level `context_debug` with metadata such as session/homework presence, phase/subphase, question id presence, `question_found`, question text length, raw/clean/forwarded screen-context lengths, student-work length, chat-history count, provider/model, prompt size, and fallback status.

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

With `AI_DEBUG_CONTEXT=true`, the same response may include top-level `context_debug` with metadata such as boss-question count, question source, provider/model, prompt size, fallback status, and `ai_unavailable`.

---

### GET /api/ai/tutor/history  *(Wave F1)*

| Param | Type | Required |
|-------|------|----------|
| `session_id` | str | yes |
| `hw_id` | str | yes |

Returns chronological turns (oldest first), capped at 50.

**200** `{ "turns": [{ "id", "session_id", "hw_id", "phase", "question_id", "role", "content", "created_at" }] }`

With `AI_DEBUG_CONTEXT=true`, the same response may include top-level `context_debug` with metadata such as session/homework presence and `history_count`; it does not include turn content.

---

### GET /api/ai/status

Reports which AI backend is active plus the resolved effective model for every gateway task (Plan 6).

**200**:
```json
{
  "provider_order": ["kimi"],
  "active_provider": "kimi",
  "tasks": {
    "tutor_chat":             {"provider": "kimi", "model": "kimi-k2.6",        "tier": "max"},
    "answer_check":           {"provider": "kimi", "model": "moonshot-v1-128k", "tier": "pro"},
    "boss_question_generate": {"provider": "kimi", "model": "moonshot-v1-128k", "tier": "pro"},
    "boss_answer_check":      {"provider": "kimi", "model": "moonshot-v1-128k", "tier": "pro"},
    "boss_persona_response":  {"provider": "kimi", "model": "moonshot-v1-32k",  "tier": "fast"},
    "final_report":           {"provider": "kimi", "model": "moonshot-v1-128k", "tier": "pro"},
    "safety_guardrail":       {"provider": "kimi", "model": "moonshot-v1-32k",  "tier": "fast"},
    "simulation_judge":       {"provider": "kimi", "model": "moonshot-v1-128k", "tier": "pro"}
  },
  "backend": "kimi",
  "model_fast": "moonshot-v1-32k",
  "model_pro": "moonshot-v1-128k",
  "available_providers": ["kimi"],
  "preference_list": ["kimi"]
}
```

- `provider_order` — provider preference list parsed from `AI_BACKEND_PREFERENCE`. Resolution walks this list in order until a provider is healthy.
- `active_provider` — first provider in `provider_order` whose credentials are present (`"kimi"` by default, `"none"` if no credentials are configured).
- `tasks` — per-`AITask` resolved `provider` / `model` / `tier`. The 8 task keys mirror `server/services/ai_gateway.py::AITask`. `tier` is `"max"`, `"pro"`, or `"fast"` from `TASK_MODEL_POLICY`; `"max"` selects `KIMI_MODEL_VISION` (Kimi K2.6 by default), while `"pro"` and `"fast"` select `KIMI_MODEL_PRO` and `KIMI_MODEL_FAST` env overrides.
- `available_providers` — all registered providers whose credentials are present.
- `backend`, `model_fast`, `model_pro`, `preference_list` — legacy fields kept for backward compat with pre-Plan-6 consumers. New consumers should read `tasks` and `provider_order`.

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

**200** `{ "status": "ok", "ai_backend": "kimi|none", "ai_ready": bool, "gemini": bool }`. `gemini` is a legacy alias for `ai_ready`.

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

## Taskboard

### GET /api/taskboard/users

**200** array of User records (see [Taskboard Record shapes](#taskboard-record-shapes)). Non-archived only, ordered by `position` ascending.

---

### POST /api/taskboard/users

```json
{ "name": "string", "color": "#22c55e" }
```

| Field   | Type           | Required | Notes |
|---------|----------------|----------|-------|
| `name`  | string         | yes      | 1–64 chars |
| `color` | string \| null | no       | 6-digit hex (`^#[0-9a-fA-F]{6}$`); `null` / omitted = no accent |

**200** created User. **422** validation error (invalid hex pattern).

---

### PATCH /api/taskboard/users/{user_id}

```json
{ "name": "string", "position": 0, "color": "#a855f7" }
```

All fields optional (`exclude_unset`). `color` accepts the same `^#[0-9a-fA-F]{6}$` pattern as POST. **200** updated User. **404** `NOT_FOUND`. **422** invalid color.

---

### DELETE /api/taskboard/users/{user_id}

Archive (soft-delete). Any assigned tasks are bounced back to Issues (`assignee_id = NULL`).

**200** `{ "ok": true }`. **404** `NOT_FOUND`.

---

### GET /api/taskboard/tasks

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `assignee_id` | int / "null" | — | Omit for all; `"null"` for Issues backlog; integer for a user's column |

**200** array of Task records (see [Taskboard Record shapes](#taskboard-record-shapes)), ordered by `position` ascending. `archived_at IS NULL` is always implicit.

---

### POST /api/taskboard/tasks

```json
{
  "title": "string",
  "description": "string",
  "task_type": "development",
  "assignee_id": 1,
  "subtask_total": 5,
  "subtask_done": 2,
  "attachment_count": 3,
  "cover_url": "https://example.com/cover.png"
}
```

| Field              | Type           | Required | Notes |
|--------------------|----------------|----------|-------|
| `title`            | string         | yes      | 1–200 chars |
| `description`      | string         | no       | default `""`, max 2000 chars |
| `task_type`        | string         | no       | one of `"general"` (default), `"development"`, `"design"`, `"research"`, `"ops"`. Unknown → **422** |
| `assignee_id`      | int \| null    | no       | omit / `null` lands on Issues backlog; integer assigns to a user (no `404` if user is archived — task ends up orphaned, callers must verify) |
| `subtask_total`    | int            | no       | 0–999, default 0 |
| `subtask_done`     | int            | no       | 0–999, default 0 |
| `attachment_count` | int            | no       | 0–999, default 0 |
| `cover_url`        | string \| null | no       | max 500 chars; renderer only displays http(s) URLs |

`status` is server-set on create (`"open"`); use PATCH to mark `"done"`. `position` is auto-assigned to the end of the target bucket.

**200** created Task. **422** validation error.

---

### PATCH /api/taskboard/tasks/{task_id}

```json
{
  "title": "string",
  "description": "string",
  "assignee_id": 1,
  "position": 0,
  "status": "done",
  "task_type": "design",
  "subtask_total": 5,
  "subtask_done": 5,
  "attachment_count": 3,
  "cover_url": null
}
```

All fields optional (`exclude_unset`). Validation rules + bounds are identical to POST (`status` is `Literal["open","done"]`; bad values → **422**). Behaviour notes:

- Omitting `assignee_id` leaves the existing assignee untouched. Sending `null` explicitly moves the task to Issues.
- Sending `position` alone reorders within the current bucket and repacks neighbours. Sending `assignee_id` + `position` cross-moves to the new bucket at that slot. Sending `assignee_id` alone appends to the end of the new bucket.
- `cover_url: null` clears an existing cover.

**200** updated Task. **404** `NOT_FOUND`. **422** validation error.

---

### DELETE /api/taskboard/tasks/{task_id}

Archive (soft-delete). Sibling positions in the same bucket are repacked to keep the column compact.

**200** `{ "ok": true }`. **404** `NOT_FOUND`.

---

### Taskboard Record shapes

User:
```json
{
  "id": 1,
  "name": "Karim",
  "position": 0,
  "color": "#22c55e",
  "task_count": 3,
  "created_at": "2026-05-06T10:00:00.000Z"
}
```

`color` is `null` for users created/migrated before per-user accents existed.

Task:
```json
{
  "id": 1,
  "title": "Fix typo",
  "description": "",
  "assignee_id": null,
  "position": 0,
  "status": "open",
  "task_type": "general",
  "subtask_total": 0,
  "subtask_done": 0,
  "attachment_count": 0,
  "cover_url": null,
  "created_at": "2026-05-06T10:00:00.000Z",
  "updated_at": "2026-05-06T10:00:00.000Z"
}
```

`status` is one of `"open" | "done"`. `task_type` is one of `"general" | "development" | "design" | "research" | "ops"`. Counts are bounded `0 ≤ n ≤ 999`. `cover_url` may be `null`; renderer (frontend) only displays http(s) URLs even though the server stores any string ≤ 500 chars.

---

## Plan 8 — Evaluation, Logging, and Rollout (admin-only)

All endpoints below are gated by either `AI_DEBUG_CONTEXT` truthy (dev) or a matching `X-Debug-Token` header equal to `AI_DEBUG_ADMIN_TOKEN` (prod). Pytest-running processes are auto-allowed. Missing or wrong creds return **403** with `{"detail": {"code": "DEBUG_FORBIDDEN"}}`.

The debug context endpoint deliberately returns **only metadata** (lengths, presence flags, counts) — never raw question text, chat history, or screen context. This is the difference between a useful diagnostic surface and a silent leak.

### GET /api/ai/debug/session/{session_id}/context

Query: `hw_id=<homework id>` (required).

**200** — `DebugContextResponse`. Length-only fields, no raw text.

```json
{
  "session_id": "s1",
  "hw_id": "hw_42",
  "phase": "practice",
  "subphase": "memory-sprint",
  "current_question_id": "q12",
  "homework_found": true,
  "session_found": true,
  "homework_title": "Algebra basics",
  "subject": "math-algebra",
  "grade": 8,
  "homework_summary_chars": 412,
  "current_phase_content_chars": 1820,
  "current_question_text_chars": 84,
  "visible_screen_text_chars": 230,
  "student_work_text_chars": 0,
  "recent_chat_history_count": 5,
  "recent_attempts_count": 3,
  "metrics_present": true,
  "missing_context_flags": [],
  "context_packet_version": "tutor.v2",
  "notes": []
}
```

### GET /api/ai/debug/session/{session_id}/events

Query: `hw_id` (required), `limit` (1-500, default 100), `event_type` (optional filter).

**200** `{ "session_id": "...", "hw_id": "...", "count": N, "events": [...] }`

### GET /api/ai/debug/session/{session_id}/ai-calls

Query: `task_type` (optional), `limit` (1-500, default 100).

**200** `{ "session_id": "...", "count": N, "ai_calls": [...] }` — rows from `ai_call_logs`.

### GET /api/ai/debug/session/{session_id}/metrics

Query: `hw_id` (required).

**200** `{ "session_id": "...", "hw_id": "...", "metrics": {...}, "attempts_count": N }`.

### GET /api/ai/debug/boss/{boss_session_id}

**200** Boss session row + every generated question (with rubric/expected_answer; admin-only by design).
**404** if `boss_session_id` does not exist.

### POST /api/ai/session/final-report

Generates and stores the final AI session report from trusted backend metrics, phase attempts, and Boss state. The service routes through `ai_gateway` task `FINAL_REPORT` and does not include raw student answers in the report prompt.

**Request Body:**
```json
{
  "session_id": "sess-uuid",
  "hw_id": "HW-20260507-001"
}
```

`homework_id` may be sent instead of `hw_id`.

**200**
```json
{
  "ok": true,
  "session_id": "sess-uuid",
  "hw_id": "HW-20260507-001",
  "prompt_version": "final-report:v1",
  "report": {
    "summary": "Concise session summary.",
    "weak_topics": ["fractions"],
    "strong_topics": ["equations"],
    "recommendation": "Review equivalent fractions before the next boss round.",
    "mastery_score": 0.72
  },
  "metrics": { "mastery_score": 0.72 },
  "attempts_count": 8
}
```

**400** `MISSING_HOMEWORK_ID` or `SESSION_HOMEWORK_MISMATCH`. **404** `HW_NOT_FOUND` or `SESSION_NOT_FOUND`.

### GET /api/ai/eval/cases/{eval_name}

**200** Loaded fixture case index (id + task_type + expected-rule keys) for `tests/ai_eval_cases/<eval_name>.jsonl`.
**404** when fixture file is missing.
**422** when fixture JSONL is corrupt.

### GET /api/ai/eval/runs

Query: `eval_name` (optional), `task_type` (optional), `limit` (1-200, default 20).

**200** `{ "count": N, "runs": [...] }` from the `ai_eval_runs` table.

### POST /api/ai/eval/run

```json
{
  "eval_name": "live_tutor_context_questions",
  "stub_response": "according to ...",
  "persist": true
}
```

Runs every fixture case through the supplied `stub_response` (single string judged against every case). Used for harness smoke-checks; CI / production-grade evals should call `ai_evaluator.run_eval` directly with a real candidate fn.

**200** `{ "report": {...}, "gate_threshold": 0.95, "gate_passed": true|false|null, "case_count": N }`.

### GET /api/ai/sim/list

**200** `{ "simulations": [{ "name": "...", "purpose": "...", "task_type": "...", "turn_count": N, "gate_threshold": 0.95 }, ...] }`.

### POST /api/ai/sim/run

```json
{
  "name": "student_confused_vocab",
  "initial_state": null,
  "persist": true
}
```

Runs the named simulation through the in-process default candidate stub. Real-backend simulations call `ai_simulator.run_simulation(...)` directly with a custom `candidate_fn`.

**200** `{ "report": {...}, "gate_threshold": 0.95, "gate_passed": true|false|null }`.

### GET /api/ai/metrics/regression-dashboard

Query: `window_hours` (1-720, default 24).

**200** Plan 8 §8 dashboard payload — provider failure rates, schema validation failures, fallback rates, question-resolution failures, boss repetition, per-task latency, latest eval run scoreboards, and per-metric `alerts` flags using `ALERT_THRESHOLDS`.

```json
{
  "window_hours": 24,
  "ai_calls": {"total": 1234, "failures": 3, "fallbacks": 1, "schema_failures": 0, "avg_latency_ms": 820, "avg_input_chars": 4200, "avg_output_chars": 350},
  "per_task": [{"task_type": "tutor_chat", "total": 800, "failures": 2, "avg_latency_ms": 900}, ...],
  "attempts": {"total": 412, "correct_count": 280, "avg_confidence": 0.87, "low_conf_ai": 3},
  "review_queue_pending": 7,
  "rates": {
    "provider_failure_rate": 0.0024,
    "schema_validation_failure_rate": 0.0,
    "generic_fallback_rate": 0.0008,
    "question_resolution_failure_rate": 0.012,
    "boss_repetition_rate": 0.0
  },
  "alerts": {"provider_failure_rate": false, ...},
  "any_alert": false,
  "eval_runs": [...]
}
```

---

## Equations

Companion endpoint to the MathLive equation editor (frontend builder UI).
Lets clients verify a LaTeX expression is well-formed before it hits storage
or a downstream renderer (KaTeX, MathML, AI tutor prompts). Pure-Python
validator in `server/services/latex_validator.py` — no third-party renderer
dependency, deterministic, fast (<1ms per expression for typical inputs).

**When to call this**

- Before saving a new equation to `block.text` (defense-in-depth — the editor
  validates client-side via MathLive, but a hostile client could bypass that)
- Before piping a student-authored or author-authored equation into an AI
  tutor prompt — the validator surfaces unfilled `\placeholder{}` markers
  so the AI doesn't try to interpret the literal text
- Before importing math from an external source (Word `.docx`, scraped HTML)

### POST /api/equations/validate

Request body:

```json
{
  "latex": "\\frac{1}{2}",
  "mode": "inline",
  "max_length": 2000
}
```

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `latex` | string | ✅ | — | The LaTeX expression. May or may not include outer `$…$` / `$$…$$` delimiters — if it does, a single matching pair is auto-stripped before validation. |
| `mode` | `"inline"` \| `"display"` | ❌ | `"inline"` | Currently informational; reserved for future per-mode rules. |
| `max_length` | int > 0 | ❌ | `2000` | Override the default cap. The hard server-side ceiling is **50 000** chars (request bodies above that 413). |

Extra unknown fields are accepted (`extra="allow"` — Invariant 1) so older
servers can talk to newer clients without breaking.

**Response (always 200, except 413 / 422 — see below):**

```json
{
  "valid": true,
  "latex": "\\frac{1}{2}",
  "mode": "inline",
  "length": 12,
  "macros": ["frac"],
  "placeholders": 0,
  "depth": 1,
  "warnings": [],
  "error": null,
  "message": null,
  "position": null
}
```

| Field | Type | Always present? | Meaning |
|---|---|---|---|
| `valid` | bool | ✅ | The only field clients MUST inspect. `true` = LaTeX passed every check. |
| `latex` | string | ✅ | Input with outer `$`-delimiters stripped. |
| `mode` | string | ✅ | Echoed back. |
| `length` | int | ✅ | Char count after stripping delimiters. |
| `macros` | string[] | ✅ | Sorted, deduplicated list of `\name` macros used. |
| `placeholders` | int | ✅ | Number of `\placeholder{}` markers (MathLive cells the author hasn't filled). |
| `depth` | int | ✅ | Maximum brace nesting depth — useful as a "complex equation" signal. |
| `warnings` | string[] | ✅ | Non-fatal advisories (e.g., "latex has 2 unfilled `\placeholder{}` markers"). |
| `error` | string \| null | ✅ | Error code when `valid=false`; `null` otherwise. |
| `message` | string \| null | ✅ | Human-readable description of the error. |
| `position` | int \| null | ✅ | 0-based byte offset of the offending char in the cleaned LaTeX. |

**Error codes** (in `error` field, response stays 200):

| `error` | Triggers when |
|---|---|
| `empty` | LaTeX is empty or whitespace-only after stripping delimiters |
| `too_long` | LaTeX exceeds `max_length` |
| `script_tag` | Input contains `<script>` / `</script>` (case-insensitive) |
| `latex_include` | `\input{…}` or `\include{…}` (file-inclusion macros) |
| `latex_shell_escape` | `\write18{…}` (shell-escape macro) |
| `href_macro` | `\href{…}{…}` (would inject clickable links into rendered output) |
| `unbalanced_braces` | `{` / `}` / `[` / `]` / `(` / `)` mismatch — `position` points at the offender |
| `unbalanced_environments` | `\begin{X}` without matching `\end{X}` (or wrong nesting) |
| `type_error` | Service-level fallback if non-string value slips through (Pydantic 422 normally catches it first) |

**HTTP status codes**

| Code | When |
|---|---|
| 200 | Always — including for `valid=false`. Clients inspect `body.valid`, not the status. |
| 413 | Payload exceeds the 50 000-char hard ceiling — pathological input, treated as client misuse. |
| 422 | Request body fails Pydantic schema validation (missing `latex`, wrong type, etc.). |

**Examples**

Valid simple expression:

```bash
$ curl -sX POST http://localhost:8000/api/equations/validate \
    -H 'Content-Type: application/json' \
    -d '{"latex": "\\sqrt{x^2 + y^2}"}' | jq
{
  "valid": true,
  "latex": "\\sqrt{x^2 + y^2}",
  "mode": "inline",
  "length": 16,
  "macros": ["sqrt"],
  "placeholders": 0,
  "depth": 1,
  "warnings": [],
  "error": null,
  "message": null,
  "position": null
}
```

Unbalanced braces:

```bash
$ curl -sX POST http://localhost:8000/api/equations/validate \
    -H 'Content-Type: application/json' \
    -d '{"latex": "\\frac{1"}' | jq '.valid, .error, .message, .position'
false
"unbalanced_braces"
"unclosed '{'"
6
```

Unfilled MathLive placeholders (warning, not error):

```bash
$ curl -sX POST http://localhost:8000/api/equations/validate \
    -H 'Content-Type: application/json' \
    -d '{"latex": "\\frac{\\placeholder{}}{\\placeholder{}}"}' | jq '.valid, .placeholders, .warnings'
true
2
[
  "latex has 2 unfilled \\placeholder{} marker(s) — MathLive cells the author hasn't typed into yet"
]
```

Security guard:

```bash
$ curl -sX POST http://localhost:8000/api/equations/validate \
    -H 'Content-Type: application/json' \
    -d '{"latex": "<script>alert(1)</script>"}' | jq '.valid, .error'
false
"script_tag"
```

**Tests**: see `tests/test_equations_validate_endpoint.py` (46 cases).
