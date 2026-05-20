# Archive — 2026-05-21 Cleanup

Stale planning, debate, and audit artifacts moved here on 2026-05-21 so the repo root and `docs/` stop carrying superseded session outputs. Nothing is deleted — restore by moving back if any of these become useful again.

Filename mangling: paths flattened with `--` as the path separator so the archive directory stays flat (e.g. `docs--audits--2026-05-09-FLOW-DEBATE.md` was originally `docs/audits/2026-05-09-FLOW-DEBATE.md`).

## Contents

### Repo-root planning artifacts

| Archived | Origin | Reason |
|---|---|---|
| `AI_OPERATING_PLAYBOOK.md` | `AI_OPERATING_PLAYBOOK.md` | One-off playbook, no inbound link |
| `TASKBOARD_PLAN.md` | `TASKBOARD_PLAN.md` | Superseded by the Class A Education Trello board |
| `WHY_CHAIN_BACKEND_PLAN.md` | `WHY_CHAIN_BACKEND_PLAN.md` | Backend plan for the Why-chain, superseded by `docs/HOMEWORK_FLOW_V2_PLAN.md` |

### PR#169 architecture plan tree (entire folder, 9+ files)

| Archived | Origin |
|---|---|
| `docs--AI_Architecture_plan/` | `docs/AI Architecture plan/homeworks_ai_architecture_plan_pr169_adjusted/*` |

No inbound link from CLAUDE.md / README.md / STATE.md. Superseded by the 2026-05-09 audit set + `HOMEWORK_FLOW_V2_PLAN.md`.

### Old audits (2026-05-06 / 2026-05-07)

| Archived | Origin |
|---|---|
| `docs--math-geometriya-demo-polish-audit-2026-05-06.md` | `docs/math-geometriya-demo-polish-audit-2026-05-06.md` |
| `docs--game-break-audit-2026-05-07.md` | `docs/game-break-audit-2026-05-07.md` |
| `docs--LLM_API_ARCHITECTURE.md` | `docs/LLM_API_ARCHITECTURE.md` |

### 2026-05-09 flow + game debate session outputs (9 files)

| Archived | Origin |
|---|---|
| `docs--audits--2026-05-09-flow-recon.md` | input to flow debate |
| `docs--audits--2026-05-09-flow-reform.md` | input to flow debate |
| `docs--audits--2026-05-09-flow-skeptic.md` | input to flow debate |
| `docs--audits--2026-05-09-FLOW-DEBATE.md` | synthesis output |
| `docs--audits--2026-05-09-game-proposals.md` | input to game debate |
| `docs--audits--2026-05-09-game-pedagogy.md` | input to game debate |
| `docs--audits--2026-05-09-game-feasibility.md` | input to game debate |
| `docs--audits--2026-05-09-GAME-DEBATE.md` | synthesis output |
| `docs--audits--2026-05-09-debates.html` | HTML rendering of the synthesis |

These informed `HOMEWORK_FLOW_V2_PLAN.md` but are no longer the source-of-truth.

### Research / inventory snapshots

| Archived | Origin |
|---|---|
| `docs--enterprise_ai_architecture_research.md` | `docs/enterprise_ai_architecture_research.md` |
| `docs--homeworks_ai_remaining_fix_report.md` | `docs/homeworks_ai_remaining_fix_report.md` |
| `docs--unified_research_report.md` | `docs/unified_research_report.md` |
| `docs--audits--nets_homework_builder_issues_inventory.md` | `docs/audits/nets_homework_builder_issues_inventory.md` |

## What still lives in `docs/audits/`

The 5 audit docs that **informed `HOMEWORK_FLOW_V2_PLAN.md`** stayed in place — they're the live evidence base for the v2 implementation:

- `docs/audits/2026-05-09-MASTER.md`
- `docs/audits/2026-05-09-cycle-and-engine.md`
- `docs/audits/2026-05-09-ai-behavior.md`
- `docs/audits/2026-05-09-content-gaps.md`
- `docs/audits/2026-05-09-engagement.md`

## Restoration

```bash
# Restore a single file
git mv docs/_archive/2026-05-21-cleanup/<flattened-name> <original-path>

# Restore the whole archive
git mv docs/_archive/2026-05-21-cleanup/* docs/   # then manually rebuild any deep paths
```
