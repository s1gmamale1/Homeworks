# NETS Homework Builder — Server README

Operational manual for the National Education Transformation System (NETS) builder for Uzbekistan. Production host: `aisigma@192.168.1.26`.

---

## 1. Status Summary

| Area | Status | Notes |
|----|----|----|
| **AI Runtime** | ✅ Live | Permanent `/h/{id}` URLs with hybrid grading (Wave D). |
| **Builder UI** | ✅ Live | 10 phase editors with RichField + auto-save. |
| **API Surface** | ✅ Live | 29 endpoints documented in `docs/API.md`. |
| **Ops (Mac mini)**| ✅ Live | launchd auto-restart installed at `192.168.1.26`. |

---

## 2. Quick Start (Dev)

```bash
# Install
python -m venv .venv
./.venv/bin/pip install -r requirements.txt

# Run
./.venv/bin/python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```
*Production uses launchd; see [Operations](#4-operations) below.*

---

## 3. Documentation

| File | Purpose |
|------|---------|
| **[docs/API.md](docs/API.md)** | Full endpoint reference (CRUD, AI, Meta, Trash). |
| **[docs/AUTH_MODEL.md](docs/AUTH_MODEL.md)** | Auth approach (Option B: token-in-URL recommended). |
| **[CONTRACTS.md](CONTRACTS.md)** | Single source of truth for `content_json` schema + enums. |
| **[STATE.md](STATE.md)** | Operational truth: what's confirmed working vs. known issues. |

---

## 4. Operations

### Persistence & Auto-restart
The server runs on a Mac mini (`192.168.1.26`) with a launchd agent that respawns uvicorn on crash and starts at login.

- **Install/Update:** `bash scripts/install_launchd.sh`
- **Control:** See [scripts/install_launchd.README.md](scripts/install_launchd.README.md) for `launchctl kickstart`.
- **Logs:** `tail -f uvicorn.log`

### Backup & Recovery
- **Daily Snapshot:** `bash scripts/backup_db.sh` (online backup, safe while running).
- **Restore:** `bash scripts/restore_db.sh backups/nets-YYYYMMDD-HHMMSS.db.gz`
- **Next Step:** Set up a crontab for `backup_db.sh` for 2 AM daily snapshots.

---

## 5. Directory Layout

```
/Users/aisigma/nets-builder/
  ├── server/
  │   ├── app.py           # FastAPI entry + static mounts
  │   ├── routes/          # CRUD, Library, AI, Meta, review-queue
  │   ├── services/        # gemini.py, injector.py, answer_checker.py
  │   └── template/        # perfect_homework.html (runtime template)
  ├── frontend/
  │   ├── index.html       # Dashboard (library + trash)
  │   ├── builder.html     # Editor SPA shell
  │   └── js/editors/      # One .js per phase (boss.js, real-life.js, etc.)
  ├── docs/                # API, Auth, Answer-Spec references
  ├── scripts/             # launchd install, backup/restore, telegram tests
  ├── fixtures/            # Seed JSONs for subjects/grades
  └── nets.db              # SQLite (WAL mode)
```

---

## 6. Key Concepts

- **Hybrid Grading:** Every question uses `answer_spec` (deterministic check) with AI fallback. High-confidence AI grades are cached; low-confidence ones hit the **Review Queue** (`/api/ai/review-queue`).
- **No Standalone Export:** The `/export` endpoint is deleted. Use `/h/{id}` for the permanent, live-graded share URL.
- **The Injector:** `server/services/injector.py` regex-replaces 10 constants in the template on the fly.
- **Vanilla Frontend:** No React/Tailwind. Pure HTML/CSS/JS for 24/7 reliability on the Mac mini.

---

## 6.5 Live AI Tutor (Wave F)

A persistent chat-bubble tutor that follows the student through the homework journey with phase-aware behavior.

- **PREVIEW**: Open Q&A mode. The tutor explains concepts, provides examples, and decomposes complex ideas without depth restrictions.
- **PRACTICE**: Scaffolding mode. The tutor provides guiding questions and decomposition of steps but never reveals the gradeable answer.
- **BOSS**: Personalized challenge mode. The tutor adopts a chosen persona (`challenger`, `mentor`, or `analyst`), reorders questions to match the student's curve, and adds personalized framing while maintaining deterministic grading logic.

**Answer-Leak Guarantee:**
In PRACTICE and BOSS phases, the server rigorously strips all grading fields — including `answer_spec.expected`, `ans`, `accepted_answers`, and `correct` — from the question payload before it is injected into the LLM context. This safety boundary is verified by automated regex checks on all outgoing prompts.

**Endpoints** (see [`docs/API.md`](docs/API.md)):
- `POST /api/ai/tutor/chat` — Send a message to the active tutor.
- `POST /api/ai/tutor/boss-plan` — Generate a personalized boss battle sequence.
- `GET  /api/ai/tutor/history` — Retrieve the current session's chat log.

**AI Backend:**
Defaults to Kimi (`moonshot-v1-32k` for chat, `moonshot-v1-128k` for boss planning) with automatic fallback to Vertex AI or Gemini API based on the `AI_BACKEND_PREFERENCE` environment variable.

**Status:**
Wave F0 + F1 shipped (backend, PR #6 + #7). F2 (frontend widget) in PR #9. F3 (boss personalization wiring) queued. Architecture details in [`docs/TUTOR.md`](docs/TUTOR.md).

---

## 7. What NOT to do

- Don't `git push` from the Mac mini.
- Don't rename `content_json` keys (breaks existing DB records).
- Don't bypass the `answer_spec` schema for new question types.
- Don't rewrite `perfect_homework.html` from scratch; patch the existing blocks.
