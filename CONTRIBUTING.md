# Contributing to NETS Homeworks

The team's working model: 4 devs landing PRs into `server`, often touching adjacent files. The two big ways things go wrong are (1) someone accidentally re-introduces a bug another PR already fixed, and (2) a stale branch overwrites recent work without a visible conflict. Both are handled below.

## The merge gate

Branch protection on `server`:

- ✅ Require pull request before merging (1 approving review)
- ✅ **Require branches up to date before merging** — your branch must be rebased onto current `server` before the merge button activates
- ✅ Stale approvals dismissed when new commits land
- ✅ `pytest` status check required (added once the CI workflow lands)
- ❌ Force-pushes to `server` blocked
- ❌ Deletion of `server` blocked

If your PR is held by the "branches must be up to date" gate:

```bash
git fetch origin
git rebase origin/server
git push --force-with-lease
```

`--force-with-lease` (not plain `--force`) is the safer flavour — it refuses to overwrite if someone else pushed to your branch in the meantime.

## The regression-test rule

> **Every fix ships a regression test that fails on the pre-fix code.**

Tests are how we make a fix permanent. A bug fix without a test gives a future PR (yours or someone else's) silent permission to re-introduce the same bug — typically by resolving a merge conflict the wrong way. With the test in place, the same regression fails CI before it can land.

This isn't aspirational — it's how this codebase already works. Two examples to copy from:

### Example 1 — `tests/test_static_cache_bust.py`

PR #31 added cache-busting via a `?v=__VERSION__` placeholder. PR #32 (merged in parallel) added a new `<script src="/js/editors/games/puzzle-lock.js">` tag without the suffix, silently bypassing the cache-bust. The footgun was caught by hand at review time.

PR #35 fenced the pattern with a strict assertion:

```python
@pytest.mark.parametrize("path", ["/", "/builder.html", "/library.html"])
def test_no_internal_script_or_link_tag_skips_cache_bust(client, path):
    """Every same-origin <script src=> / <link href=> on every dashboard
    page must carry ?v=<sha>. Catches the footgun where a future PR adds
    a new tag under any path and forgets the suffix."""
    r = client.get(path)
    refs = _internal_asset_refs(r.text)
    for ref in refs:
        assert "?v=" in ref, (
            f"missing cache-bust on {path}: {ref}\n"
            f"add ?v=__VERSION__ to the tag"
        )
```

The error message tells the next dev exactly what to fix. That's the bar.

### Example 2 — `tests/test_tutor_chat.py::test_tutor_chat_accepts_screen_context`

PR #24 fixed the tutor giving generic answers because it never received the on-screen context. The fix was 8 LOC. The test asserts the end-to-end chain holds: client `screen_context` → `hw_meta["preview_context"]` → `PREVIEW_CONTEXT:` section in the generated prompt. If a future refactor breaks any link in that chain, the test fails — even if no individual file shows an obvious change.

### Patterns to prefer

- **Assert the bad state cannot return**, not just "the good path works." Use `assert "X" not in body` / `assert key not in response` style when guarding against regressions.
- **Name the test after the regression it guards**, e.g., `test_no_internal_script_or_link_tag_skips_cache_bust`, not `test_cache_bust_works`.
- **Include the why in the docstring or assertion message**, with enough context that a future contributor hitting the failure understands what they broke.
- **Parametrize over the surfaces** that share the invariant — three pages, ten endpoints, etc. — instead of one `assert` per surface.

### When a test isn't possible

If the fix is in a layer pytest can't reach (browser-only behaviour, race conditions, infrastructure), add a script under `scripts/e2e/` (Puppeteer / shell) that exercises it and document the manual run command. The `scripts/e2e/post_reallife_advance.cjs` regression script is the model — it reproduces a real bug and exits non-zero when the bug returns.

## What makes a PR likely to land quickly

- Targets `server` directly, not a long-lived feature branch.
- Diff stays under ~300 LOC of real changes (excluding generated/whitespace churn).
- A PR body that explains the **why**, not just the what.
- For UI changes, include a screenshot or a short Loom of the new state.
- Every fix ships a regression test (see above).
- Branch is rebased onto current `server` before requesting review (the merge gate enforces this anyway).

## What blocks merge

- Conflicts against `server` (rebase first).
- `pytest` failing (run locally with `python -m pytest tests/ -q` before pushing).
- Bug fix without a regression test.
- Binary blobs (images > 100 KB) committed directly — use `static/` if they're runtime assets, or keep them out of the repo entirely.
- Hardcoded credentials of any kind. Production secrets live in launchd's environment, never in tracked files.
