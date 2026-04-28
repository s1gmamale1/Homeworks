# NETS Homework Builder — API Reference

Base URL (production): `http://192.168.1.26:8000`  ·  Local dev: `http://localhost:8000`

All responses JSON unless marked **HTML**. Errors: `{ "detail": { "error": "...", "code": "..." } }` with 4xx/5xx status.

## Quick index

| Group | Endpoints |
|-------|-----------|
| Homework CRUD | POST/GET/PUT/DELETE /api/homeworks, /…/{id}/restore, /…/{id}/permanent, /…/{id}/duplicate, PATCH /…/{id}/content |
| Versions | GET/GET/POST /api/homeworks/{id}/versions, /…/{id}/versions/{vid}, /…/{id}/versions/{vid}/restore |
| Render | GET /h/{id} (HTML), GET /api/homeworks/{id}/preview (HTML) |
| Library | GET /api/library, GET /api/library/facets |
| AI tutor | POST /api/ai/check-answer, /api/ai/boss-turn, /api/ai/reflection, /api/ai/tutor |
| AI live tutor (Wave F1) | POST /api/ai/tutor/chat, /api/ai/tutor/boss-plan, GET /api/ai/tutor/history |
| AI meta | GET /api/ai/status |
| Review queue | GET /api/ai/review-queue, POST /api/ai/review-queue/{id}/decide |
| Answer-spec | POST /api/ai/answer-spec/preview |
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

## AI Tutor

All AI endpoints accept and return JSON. On failure: `500` with `{ "error": "...", "code": "AI_ERROR" | "PROMPT_MISSING" }`.

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

### POST /api/ai/boss-turn

```json
{
  "boss_question": "string",
  "student_answer": "string",
  "expected_answers": [],
  "damage_value": 10,
  "hp_remaining": 100,
  "attempt_number": 1,
  "subject": "math-algebra",
  "grade": 8
}
```
`damage_value`: 0–50. `attempt_number`: ≥ 1.

**200** `{ "correct": bool, "damage_dealt": int, "boss_response": "string", "hint": "string|null", "score": float }`

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
  "backend": "kimi|vertex|gemini|none",
  "model_fast": "gemini-2.5-flash",
  "model_pro": "gemini-2.5-pro",
  "active_provider": "kimi",
  "preference_list": ["kimi", "vertex", "gemini"],
  "available_providers": ["kimi"]
}
```
- `active_provider` — name of the provider currently selected (first available in `preference_list`).
- `preference_list` — ordered list read from `AI_BACKEND_PREFERENCE` env (default `kimi,vertex,gemini`).
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
