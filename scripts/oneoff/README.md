# One-shot scripts

Throwaway scripts that fixed up a specific homework, migrated a one-off
data shape, or otherwise solved a problem that won't recur. Kept in the
repo for **historical reference** so the next person hitting a similar
situation can see how it was solved — but they're **not** part of the
prod runtime, not run on a schedule, and not exercised by tests.

## Lifecycle

When a script lands here, write a one-liner in the table below saying
**when it ran** and **what it did**. After ~6 months, prune stale entries.

## Catalogue

| Script | When | What it did |
|---|---|---|
| `rebuild_hw008_from_md.py` | 2026-04-28 | Rebuilt `HW-20260427-008` (Aylana grade-8 geometry) from the source MD after the original push-from-playable importer left several sloppy artifacts (✓ markers in MS prompts, broken panel titles, RL Q5 mis-mapped to Phase 5 text). One-time fixup; the underlying importer was not retroactively fixed because the bug only affected this single record. |

## Running

```bash
python scripts/oneoff/<name>.py     # most are self-contained against the live API
```

If a script in here mutates a remote service, **read its docstring first**
— some only worked against a specific snapshot of state.
