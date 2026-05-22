# Toriqli Frontend Audit Handoff — Claude Code

Branch: `Toriqli`
Base: `DaddysBranch`
Local preview: `http://127.0.0.1:8765/h/HW-20260521-001`

## Required Skills And Plugins

Claude Code should use:

- Browser / browser-use plugin for local visual QA, screenshots, click-throughs,
  and mobile viewport checks.
- Playwright-style browser checks for desktop and mobile screenshots.
- Existing repo tests before and after edits:
  - `npm run build` in `frontend/app`
  - targeted pytest for changed surfaces
  - full `pytest tests/ -q` before PR handoff

Do not rely on a plain static server for this SPA. Use FastAPI/uvicorn so `/h/*`
injects `window.NETS_CTX`, `/app/assets/*` resolves, and `/api/runtime/*` works.

## Current Audit Findings

- The blank local preview at `127.0.0.1:8781` was caused by serving
  `frontend/app/dist` directly at `/`; Vite builds assets for `/app/assets/*`.
  Use `127.0.0.1:8765/h/<HW_ID>` instead.
- The Learning Hub/menu itself should remain the current DaddysBranch home
  experience. Do not redesign the whole Hub when fixing Flashcards.
- Owner correction: the Flashcards stage should visually feel like it belongs
  to the home/menu page. Apply the menu/path visual language to Flashcards and
  related learning sub-screens, not to the overall app shell.
- Flashcards retry now has a real weak-card affordance: missed Memory Check
  items map through `flashcard_ref` and show `Weak — review` on linked cards.
- Memory Check schema accepts current v1 runtime modes only when a type is
  supplied: `mcq`, `fill_blank`, `choose_explanation`, `true_false`.

## Claude Code Frontend Task List

1. Mobile QA pass for Learning Hub.
   - Check 390x844, 430x932, 768x1024, and desktop.
   - Ensure no title/card/button text overlaps or clips.
   - Verify the tutor bubble does not cover primary CTAs.
   - Keep the current home/menu design intact unless a separate owner request
     explicitly asks for a Hub redesign.

2. Flashcards menu-style polish.
   - Flashcards should share the current home/menu feeling: light blue page,
     chunky rounded 3D controls, strong tap targets, and readable playful type.
   - Do not make the whole app look like a flashcard; the visual change belongs
     to the Flashcards stage and immediate learning sub-flow surfaces.
   - Walk all cards, flip front/back, press `Bildim` and `Bilmadim`.
   - Confirm `Start Memory Check` unlocks only after all cards are viewed.
   - Confirm `Weak — review` chip is visible on retry-linked cards.

3. Memory Check visual QA.
   - Test MCQ, true/false, choose explanation, and fill blank.
   - Confirm feedback appears inline and does not push buttons below the visible
     safe area on mobile.
   - Verify wrong answers do not reveal the exact expected answer unless the
     authored feedback intentionally does so.

4. Unlock flow QA.
   - Complete CBP and Memory Check, then return to Hub.
   - Confirm Homework Practices unlock state is readable and CTA is reachable.
   - Confirm locked state remains clear before both learning sections pass.

5. Builder QA for flashcard links.
   - Open Builder on a v2 homework.
   - Add/edit flashcards and Memory Check items.
   - Verify `Source flashcard` persists as `memory_check.items[].flashcard_ref`.
   - Reopen the homework and confirm links round-trip.

6. Accessibility and motion.
   - Keyboard-tab through Hub, Flashcards, Memory Check.
   - Check focus rings are visible.
   - Check `prefers-reduced-motion` does not leave hidden content or stuck
     animations.

7. Backend/API sanity for frontend assumptions.
   - Verify `/api/runtime/homeworks/<id>` strips answer keys.
   - Verify `/api/runtime/homeworks/<id>/gate-state?session_id=...` reflects
     latest attempts.
   - Verify direct practice-arc grading still returns `403 PRACTICE_LOCKED`
     before unlock.

## Suggested Regression Tests

- Add Playwright screenshot smoke for Hub + Flashcards + Memory Check on mobile.
- Add a source-level guard that Flashcards keeps menu-style tokens/classes while
  Learning Hub is not rewritten by unrelated Flashcards work.
- Add builder round-trip test for `flashcard_ref`.
