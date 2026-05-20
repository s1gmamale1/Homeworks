# Plan — Taskboard (internal Trello-style task board)

## Context

Internal task-tracking board on the platform. No auth, no real user identity — just **named people** (typed-in names, internal use). Tasks are created on a default **"Issues"** tab and **drag-and-dropped onto a person's tab** to assign. Per-person tabs are auto-created when a name is added.

This is **greenfield** — there is no existing user model, no drag-drop UI anywhere in the codebase, no kanban primitives. We add a fifth top-level page (`/taskboard.html`) alongside `/landing`, `/index`, `/library`, `/builder`, plus two new SQLite tables and one new route file. Reuses the project's Apple-glass CSS primitives and the existing tabs pattern (`.library-tabs` / `.library-tab`).

Intended outcome: a single page where the owner can spin up a few names ("Karim", "Aiden", "Toriqli", …), throw issues onto a backlog, and drag them to whoever's responsible. State persists in SQLite, refreshes survive, no offline mode.

---

## Existing patterns to reuse (do NOT reinvent)

| Need | Reuse from | Path |
|---|---|---|
| Page registration + cache-bust placeholder | `_HTML_PAGES` dict | `server/app.py:121-146` |
| Cache-bust regression test | parametrize list | `tests/test_static_cache_bust.py:93` |
| CRUD route shape (GET/POST/PATCH/DELETE + Pydantic) | homework router | `server/routes/homework.py:43-262` |
| Pydantic conventions (`_Permissive`, `extra="allow"`, `BaseModel`) | content schemas | `server/schemas/content.py:34-37` |
| SQLite table definition (raw SQL in `_SCHEMA`, `CREATE TABLE IF NOT EXISTS`, idempotent migrations) | DB init | `server/db/migrations.py:4-150` |
| Async sqlite connection w/ WAL + FK pragmas | connection helper | `server/db/connection.py:12` |
| Frontend fetch wrapper (`request()`, error handling) | api bridge | `frontend/js/api.js:64-96` |
| Page state + localStorage idiom | library controller | `frontend/js/library.js:91-131` |
| Tabs UI markup + `.library-tabs` / `.library-tab.is-active` + `aria-selected` | dashboard tabs | `frontend/index.html:203-212` + `dashboard.js:668` |
| Apple-glass primitives (`.glass-card`, `.btn`, `.btn-primary`, `.btn-ghost`, `.tab-count`, `.eyebrow`, `.editor-card`, `.status-pill`) | shared CSS | `frontend/css/app.css` (325, 350, 361, 608, 634, 647, 688, 2916, 2944) |
| i18n table (`window.STRINGS = { en, uz, ru }`, `t("page.key")`) | strings | `frontend/js/i18n/strings.js:16-80` |
| Pre-emptive API.md endpoint section per `/api/...` route | docs index | `docs/API.md` |

**No auth** per `docs/AUTH_MODEL.md` option A — routes are public, same as `/api/homeworks`.

**No drag-drop dependency** — use HTML5 native `dragstart` / `dragover` / `drop` / `dataTransfer`. Reduces bundle weight; matches the no-framework constraint.

---

## Data model

Two new tables. Both sit inside the existing `_SCHEMA` raw-SQL string in `server/db/migrations.py` so they're created idempotently on startup.

```sql
CREATE TABLE IF NOT EXISTS taskboard_users (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  position    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  archived_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tb_users_position ON taskboard_users(position);

CREATE TABLE IF NOT EXISTS taskboard_tasks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  assignee_id INTEGER REFERENCES taskboard_users(id) ON DELETE SET NULL,
  position    INTEGER NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'open',
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  archived_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tb_tasks_assignee ON taskboard_tasks(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tb_tasks_position ON taskboard_tasks(position);
```

**Semantics**
- `assignee_id IS NULL` ⇒ task lives in the **Issues** tab (default landing for new tasks).
- `ON DELETE SET NULL` on `assignee_id` ⇒ archiving / deleting a person bounces their tasks back to Issues automatically (no orphans, no destructive cascade).
- `position` is **dense** within an `(assignee_id)` bucket. Repacked on every move. Simpler than sparse positions; cost is fine at this scale (a board has ≤ ~100 tasks, repacks are cheap).
- `archived_at` enables soft-delete; v1 only hides archived rows, no archive viewer UI.
- `status` column reserved for future ('open' is the only value v1 uses) — added now to avoid a follow-up migration.

---

## Backend

### New files

**`server/db/taskboard_repo.py`** (~180 LOC) — the only place that writes raw SQL for these tables. Pattern matches the homework repo idiom.

Functions:
- `list_users() -> list[dict]` — non-archived, ordered by `position ASC`, joins `COUNT(taskboard_tasks.id)` for `task_count` per user.
- `create_user(name) -> dict` — appends at end (max(position)+1).
- `update_user(user_id, *, name=None, position=None) -> dict` — rename or reorder; on reorder, repack neighbors.
- `archive_user(user_id) -> None` — sets `archived_at = now`. The FK `ON DELETE SET NULL` doesn't fire for soft-delete, so we explicitly `UPDATE taskboard_tasks SET assignee_id = NULL WHERE assignee_id = ?` in the same transaction.
- `list_tasks(assignee_id: int | NULL_SENTINEL | None) -> list[dict]` — non-archived; if `assignee_id` is the sentinel, return all; else filter; ordered by `position ASC`.
- `create_task(title, description) -> dict` — always lands at end of Issues bucket.
- `update_task(task_id, **patch) -> dict` — handles the four mutations: title/description, assignee change (move to end of new bucket), position change within same bucket (repack). If both assignee and position change, route to "move to specific slot in new bucket". `updated_at` bumped.
- `archive_task(task_id) -> None` — soft delete.

Position-repack helper (private):

```python
async def _repack_bucket(db, assignee_id):
    rows = await db.execute_fetchall(
        "SELECT id FROM taskboard_tasks "
        "WHERE assignee_id IS ? AND archived_at IS NULL "
        "ORDER BY position ASC, id ASC",
        (assignee_id,),
    )
    for new_pos, row in enumerate(rows):
        await db.execute(
            "UPDATE taskboard_tasks SET position = ? WHERE id = ?",
            (new_pos, row["id"]),
        )
```

**`server/routes/taskboard.py`** (~220 LOC) — same shape as `routes/homework.py`.

Pydantic models (inline, `_Permissive` base):

```python
class TaskboardUserCreate(_Permissive):
    name: str = Field(min_length=1, max_length=64)

class TaskboardUserUpdate(_Permissive):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    position: Optional[int] = Field(default=None, ge=0)

class TaskboardUserOut(_Permissive):
    id: int; name: str; position: int; task_count: int; created_at: str

class TaskboardTaskCreate(_Permissive):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)

class TaskboardTaskUpdate(_Permissive):
    title:       Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    assignee_id: Optional[int] = None   # null is meaningful — see PATCH semantics
    position:    Optional[int] = Field(default=None, ge=0)

class TaskboardTaskOut(_Permissive):
    id: int; title: str; description: str
    assignee_id: Optional[int]; position: int; status: str
    created_at: str; updated_at: str
```

**PATCH semantics gotcha — `assignee_id = null` must be distinguishable from "field absent"**. The route handler reads `req.model_dump(exclude_unset=True)` and only touches `assignee_id` when the key was explicitly provided. Frontend sends `{assignee_id: null}` to mean "move to Issues" and omits the field to mean "don't touch".

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET    | `/api/taskboard/users` | list users + their task counts |
| POST   | `/api/taskboard/users` | create `{name}` → returns user |
| PATCH  | `/api/taskboard/users/{user_id}` | rename and/or reorder |
| DELETE | `/api/taskboard/users/{user_id}` | archive; their tasks fall back to Issues |
| GET    | `/api/taskboard/tasks` | list all (or `?assignee_id=null` / `?assignee_id=<int>`) |
| POST   | `/api/taskboard/tasks` | create `{title, description?}` → lands on Issues |
| PATCH  | `/api/taskboard/tasks/{task_id}` | rename / reassign / reorder |
| DELETE | `/api/taskboard/tasks/{task_id}` | archive |

Mounted with `app.include_router(taskboard_router, prefix="/api")` in `server/app.py:109`-area.

### Modified files (backend)

| File | Change | LOC |
|---|---|---|
| `server/db/migrations.py` | append the two `CREATE TABLE` blocks + 3 `CREATE INDEX` to `_SCHEMA` | +30 |
| `server/db/__init__.py` | re-export taskboard_repo functions | +6 |
| `server/app.py` | router include + `_HTML_PAGES["/taskboard.html"] = "taskboard.html"` | +4 |
| `docs/API.md` | new "## Taskboard" section, ~8 endpoint blocks | +180 |

### Tests (backend)

**`tests/test_taskboard_users.py`** (~120 LOC)
- `test_list_empty_returns_array`
- `test_create_user_appends_to_end_position`
- `test_create_two_users_preserves_order`
- `test_rename_user_via_patch`
- `test_reorder_user_repacks_positions`
- `test_archive_user_unassigns_their_tasks_to_issues`
- `test_archived_user_hidden_from_list`

**`tests/test_taskboard_tasks.py`** (~180 LOC)
- `test_create_task_lands_on_issues_with_null_assignee`
- `test_create_task_appends_to_end_of_issues`
- `test_list_tasks_filter_by_assignee_null`
- `test_list_tasks_filter_by_assignee_id`
- `test_patch_task_assign_moves_to_user_end`
- `test_patch_task_assign_to_null_moves_to_issues`
- `test_patch_task_reorder_within_bucket_repacks`
- `test_patch_task_cross_bucket_move_with_explicit_position`
- `test_patch_task_omitted_assignee_does_not_change_assignee` (the unset-vs-null gotcha)
- `test_archive_task_hides_from_list`
- `test_archive_does_not_affect_other_tasks_positions`

Total: ~300 LOC test, follows the conftest fixture pattern from `tests/test_homeworks_create.py`.

---

## Frontend

### New files

**`frontend/taskboard.html`** (~140 LOC) — topbar nav matches index/library exactly.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Taskboard · NETS</title>
  <link rel="stylesheet" href="/css/app.css?v=__VERSION__">
  <link rel="stylesheet" href="/css/taskboard.css?v=__VERSION__">
</head>
<body>
  <header class="topbar">
    <a class="brand" href="/landing.html">NETS</a>
    <nav class="topbar-nav" aria-label="Primary">
      <a href="/index.html" class="topbar-nav-link">Dashboard</a>
      <a href="/library.html" class="topbar-nav-link">Library</a>
      <a href="/taskboard.html" class="topbar-nav-link is-active" aria-current="page">Taskboard</a>
    </nav>
  </header>

  <main class="taskboard-shell">
    <div class="taskboard-header glass-card">
      <h1 class="taskboard-title">Taskboard</h1>
      <p class="eyebrow muted-text">Internal task board · drag to assign</p>
      <div class="taskboard-actions">
        <button class="btn btn-primary" id="tb-new-task">+ New task</button>
        <button class="btn btn-ghost"   id="tb-new-user">+ New person</button>
      </div>
    </div>

    <div class="library-tabs taskboard-tabs" role="tablist" aria-label="Taskboard tabs" id="tb-tabs">
      <!-- rendered by JS: pinned "Issues" tab + one tab per user -->
    </div>

    <section class="taskboard-panel glass-card" id="tb-panel">
      <!-- the ACTIVE tab's task list — vertical card stack with HTML5 drag/drop -->
    </section>
  </main>

  <dialog id="tb-task-modal" class="tb-modal"></dialog>
  <dialog id="tb-user-modal" class="tb-modal"></dialog>

  <script src="/js/i18n/strings.js?v=__VERSION__"></script>
  <script src="/js/i18n.js?v=__VERSION__"></script>
  <script src="/js/api.js?v=__VERSION__"></script>
  <script src="/js/theme.js?v=__VERSION__"></script>
  <script src="/js/taskboard.js?v=__VERSION__" type="module"></script>
</body>
</html>
```

**`frontend/js/taskboard.js`** (~420 LOC) — single-page controller, follows the `library.js` shape.

Module-level state:

```js
const state = {
  users:        [],   // [{id, name, position, task_count}]
  tasks:        [],   // [{id, title, description, assignee_id, position, ...}]
  activeTabId:  null, // null = Issues tab; number = user_id
  draggedTaskId: null,
  dropTarget:   null, // { kind: "tab"|"card", id: number|"issues" }
};
```

Sub-modules (all in one file):

- **API helpers** — wrap `request()` from `frontend/js/api.js`:
  - `apiListUsers()`, `apiCreateUser(name)`, `apiPatchUser(id, patch)`, `apiArchiveUser(id)`
  - `apiListTasks()`, `apiCreateTask(title, description)`, `apiPatchTask(id, patch)`, `apiArchiveTask(id)`
- **Render**:
  - `renderTabs()` — pinned "Issues" pill (with task count), then `state.users` in `position` order. Each tab is a `.library-tab` with `data-tab-id="issues"` or `data-tab-id="<user_id>"`. Active one has `is-active` + `aria-selected="true"`.
  - `renderPanel()` — filters `state.tasks` by `state.activeTabId`, sorts by `position`, builds card list.
  - `renderCard(task)` — `.taskboard-card[draggable="true"][data-task-id]` with title + description preview + small action menu (edit / archive).
- **Drag-drop wiring** (HTML5 native, no library):
  - On each card: `dragstart` (set `state.draggedTaskId`, `effectAllowed='move'`), `dragend` (clear).
  - On each card (drop target for **within-tab reorder**): `dragover` (preventDefault + compute insert-before/after via midpoint of `getBoundingClientRect()`), `drop` → `moveTask(draggedId, {position: targetPos})`.
  - On each tab pill (drop target for **cross-tab reassign**): `dragover` (highlight), `drop` → `moveTask(draggedId, {assignee_id: tabId, position: 999_999})` — backend repack normalizes to end.
- **Mutations**:
  - `moveTask(id, patch)` — **optimistic**: mutate `state.tasks` in memory first, re-render, fire PATCH; on error, revert by re-fetching server state.
  - `createTask({title, description})` → POST → re-fetch → switch to Issues tab → flash newly-created card.
  - `createUser({name})` → POST → re-fetch users → switch to that new user's tab.
  - `editTask(id)`, `archiveTask(id)`, `archiveUser(id)` (with confirm dialog).
- **Boot**: `init()` runs `Promise.all([apiListUsers(), apiListTasks()])`, sets `state.activeTabId = null`, renders.

**`frontend/css/taskboard.css`** (~280 LOC) — page-specific only. Reuses `.glass-card`, `.btn*`, `.library-tabs`, `.library-tab`, `.tab-count`, `.eyebrow` from `app.css`. Adds:

- `.taskboard-shell` — page max-width grid
- `.taskboard-header` — header card layout
- `.taskboard-tabs` — extends `.library-tabs` with horizontal scroll on overflow
- `.taskboard-panel` — vertical card stack, min-height
- `.taskboard-card` — card shell; `cursor: grab` baseline → `cursor: grabbing` while dragging
- `.taskboard-card.is-dragging` — opacity 0.4
- `.library-tab.is-drop-target`, `.taskboard-card.is-drop-above`, `.taskboard-card.is-drop-below` — drop indicators
- `.taskboard-empty` — empty-state message ("No tasks here yet — drag one over.")

### Modified files (frontend)

| File | Change | LOC |
|---|---|---|
| `frontend/index.html` | append Taskboard link to `.topbar-nav` | +1 |
| `frontend/library.html` | same nav-link addition | +1 |
| `frontend/builder.html` | same nav-link addition | +1 |
| `frontend/landing.html` | optional: skip in v1 (landing has its own nav style) | 0 |
| `frontend/js/i18n/strings.js` | add ~25 keys × 3 langs under `taskboard.*` namespace | +75 |

### Tests (frontend)

Add `"/taskboard.html"` to `tests/test_static_cache_bust.py:93` parametrize list. No JS-eval browser tests in v1.

---

## File deltas summary

### NEW
| File | LOC |
|---|---|
| `server/db/taskboard_repo.py` | ~180 |
| `server/routes/taskboard.py` | ~220 |
| `frontend/taskboard.html` | ~140 |
| `frontend/js/taskboard.js` | ~420 |
| `frontend/css/taskboard.css` | ~280 |
| `tests/test_taskboard_users.py` | ~120 |
| `tests/test_taskboard_tasks.py` | ~180 |

### Modified
| File | LOC delta |
|---|---|
| `server/db/migrations.py` | +30 |
| `server/db/__init__.py` | +6 |
| `server/app.py` | +4 |
| `frontend/index.html` | +1 |
| `frontend/library.html` | +1 |
| `frontend/builder.html` | +1 |
| `frontend/js/i18n/strings.js` | +75 |
| `tests/test_static_cache_bust.py` | +1 |
| `docs/API.md` | +180 |

**Total: ~1540 LOC new + ~300 LOC modified. ~7 new files, ~9 modified.**

---

## Verification

### Backend smoke (after T1)

```bash
python -m pytest tests/test_taskboard_users.py tests/test_taskboard_tasks.py -v
python -m pytest tests/ -q

python -m uvicorn server.app:app --host 127.0.0.1 --port 8765 --log-level warning &
curl -X POST http://127.0.0.1:8765/api/taskboard/users  -H 'Content-Type: application/json' -d '{"name":"Karim"}'
curl -X POST http://127.0.0.1:8765/api/taskboard/tasks  -H 'Content-Type: application/json' -d '{"title":"Wire up landing copy"}'
curl       http://127.0.0.1:8765/api/taskboard/users
curl       http://127.0.0.1:8765/api/taskboard/tasks
curl -X PATCH http://127.0.0.1:8765/api/taskboard/tasks/1 -H 'Content-Type: application/json' -d '{"assignee_id":1}'
curl       'http://127.0.0.1:8765/api/taskboard/tasks?assignee_id=1'
```

Expected: task #1 starts with `assignee_id=null`, ends with `assignee_id=1, position=0`.

### Frontend smoke (after T2)

Manual walkthrough at `http://127.0.0.1:8765/taskboard.html`:

1. Empty board renders with **only "Issues"** tab pinned.
2. Click "+ New person", type "Karim", submit → second tab appears and becomes active.
3. Click "+ New person", type "Aiden", submit → third tab appears.
4. Switch back to "Issues" tab.
5. Click "+ New task", title="Fix landing typo" → card appears in Issues.
6. **Drag** that card onto the "Karim" tab pill → card disappears from Issues, "Karim" tab count goes 0 → 1.
7. Switch to "Karim" tab → card visible; create 2 more, drag to reorder → reorder persists across F5 refresh.
8. Drag a Karim card onto "Issues" pill → returns to Issues backlog.
9. Archive a task (action menu → Archive) → disappears; reload, still gone.
10. Archive Karim (with tasks assigned) → confirm dialog → Karim's tab disappears, his tasks fall back to Issues with `(N)` count restored.
11. F5 reload → all state preserved.

### Regression
- `python -m pytest tests/test_static_cache_bust.py -v` includes `/taskboard.html` and asserts `?v=<sha>` substituted.
- Open `/index.html` and `/library.html` — Taskboard nav-link present, active state lights only on `/taskboard.html`.

### Visual loop close

Screenshots:
- empty board (no users, no tasks)
- 3 users + cards distributed
- mid-drag (`.is-dragging` opacity, `.is-drop-target` accent)

Compare against the same shot after F5 to confirm persistence.

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| HTML5 native drag is finicky on mobile (touch events don't fire `dragstart`) | v1 = desktop-only by design. Add `@media (pointer: coarse)` notice. Touch is a follow-up. |
| `assignee_id` PATCH ambiguity (`null` vs unset) silently corrupts state | Backend uses `req.model_dump(exclude_unset=True)`; the unset-vs-null test is the regression fence. |
| Position-repack on every move is N writes per move | At ≤100 tasks it's fine. If the board grows past ~500 tasks, switch to sparse positions. Not v1. |
| User archive cascades tasks back to Issues — accidental archive blobs everything | Soft-delete + 5-second toast with **Undo** button. If cut from v1, document in release notes. |
| Cache-bust regression test forgets the new page | Adding to the parametrize list is mandatory in T3 — flagged in the dispatch brief. |
| FK constraint blocks soft-delete cascade | Schema defines `ON DELETE SET NULL` for hard delete; soft-delete path explicitly `UPDATE … SET assignee_id=NULL` in the same tx. |
| Old prod DB doesn't have the new tables | `CREATE TABLE IF NOT EXISTS` + `init_db()` handle this idempotently. No manual migration. |
| Optimistic move + failed PATCH leaves UI out of sync | On PATCH failure, re-fetch and re-render; show toast `"Couldn't move — refreshed."`. |
| i18n keys missing in `uz` / `ru` fall through to English | i18n helper has fallback chain; add the keys for all 3 langs in T2 to keep parity. |

---

## Sequencing & dispatch

Single PR; three sub-chunks. T1 + T3 are file-disjoint and run **in parallel**; T2 runs **after T1** because the JS contract pins to confirmed endpoint shapes. Smoke is inline.

```
T1 — Backend (schema + repo + routes + tests + docs/API.md section)        Sonnet 4.6   ~900 LOC
   │  files: server/db/migrations.py, server/db/__init__.py,
   │         server/db/taskboard_repo.py, server/routes/taskboard.py,
   │         server/app.py, tests/test_taskboard_*.py, docs/API.md
   │
   ├─ in parallel ─→ T3 — Cross-cuts (nav links + cache-bust test row)     Sonnet 4.6   ~10 LOC
   │                       files: frontend/index.html, frontend/library.html,
   │                              frontend/builder.html, tests/test_static_cache_bust.py
   ▼
T2 — Frontend (taskboard.html + taskboard.js + taskboard.css + i18n)        Opus 4.7     ~920 LOC
   │  files: frontend/taskboard.html, frontend/js/taskboard.js,
   │         frontend/css/taskboard.css, frontend/js/i18n/strings.js
   │  Reasoning for Opus tier: drag-drop UX is the failure-prone surface
   │  (insert-position math, optimistic-update rollback, accessibility).
   ▼
T4 — Smoke (uvicorn + curl + browser walkthrough per Verification section)  inline       (no LOC)
   ▼
Open PR → push → admin-merge per s1gmamale1 rule on Sigma green
```

**Worktree: OFF** for all (single coordinated arc, no parallel-session risk).

**Re-fetch `origin/server` before T1 starts AND right before push.**

Dispatch flags:
> "Dispatching **[T1 backend taskboard]** to **Sonnet 4.6** — mechanical CRUD scaffold mirroring `routes/homework.py`; conf 92%; worktree OFF; fg."
>
> "Dispatching **[T3 cross-cuts]** to **Sonnet 4.6** — 4 single-line nav additions + 1-line parametrize add; conf 98%; worktree OFF; fg."

---

## Out of scope (v1) — note in PR body

- Auth / per-user login / multi-tenant taskboards
- Task labels, due dates, comments, attachments
- Within-tab subcolumns (Doing / Done)
- Archive viewer UI
- Drag on touch devices (desktop-only v1)
- Real-time multi-client sync
- Bulk operations (multi-select drag, bulk archive)
- Activity log / audit trail
- Landing-page nav-link entry

---

## §7 Open decisions — defaults already chosen, flag if any need to flip

1. **Single-status model.** `status` column reserved but v1 only uses `'open'`.
2. **Drag UX.** Cross-tab move = drop card onto tab pill. Within-tab reorder = drop card onto another card.
3. **Card detail view.** Click card body opens edit modal; explicit `⋮` menu for Archive.
4. **User archive policy.** Archiving a person bounces their tasks back to Issues.
5. **Auth.** Public routes.
6. **i18n coverage.** All 3 langs (en/uz/ru) on day one.
7. **Position storage.** Dense `(0..N-1)` repacked on every move.
8. **Multi-select drag.** No — single-card only.
9. **Tab pill task counts.** Yes — reuse `.tab-count`.
10. **Order of new tasks.** Always land at end of Issues.
