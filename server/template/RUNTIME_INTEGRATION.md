# NETS_AI Runtime Integration Guide

When the homework is served by the NETS backend (not opened as a file), `window.NETS_AI` is available.

## Check AI availability

```js
if (window.NETS_AI && window.NETS_AI.isAvailable()) {
    // AI tutor accessible
}
```

## Adaptive Quiz integration example

Where the existing code compares against `ans[]`:

```js
// Existing fast path
if (GB_ADAPTIVE_QUIZ[i].ans.includes(userAnswer)) {
    markCorrect();
    return;
}

// Fallback: ask AI
if (window.NETS_AI?.isAvailable()) {
    const r = await window.NETS_AI.checkAnswer({
        question: GB_ADAPTIVE_QUIZ[i].q,
        studentAnswer: userAnswer,
        expectedAnswers: GB_ADAPTIVE_QUIZ[i].ans,
        tier: GB_ADAPTIVE_QUIZ[i].tier,
    });
    if (r.correct) {
        markCorrect(r.feedback);
    } else {
        markWrong(r.feedback);
    }
}
```

## Boss integration example

```js
const turn = await window.NETS_AI.bossTurn({
    bossQuestion: BOSS_QUESTIONS[i].q,
    studentAnswer: userAnswer,
    expectedAnswers: BOSS_QUESTIONS[i].ans,
    damageValue: BOSS_QUESTIONS[i].dmg,
    hpRemaining: currentHP,
    attemptNumber: attempts[i],
});
// Use turn.boss_response to display boss dialogue
// Use turn.hint to show a hint after 2nd failed attempt
// Apply turn.damage_dealt to HP
```

## Reflection integration

```js
const fb = await window.NETS_AI.reflectionFeedback({
    studentReflection: reflectionText,
    performance: {
        correct: sessionCorrectCount,
        total: sessionTotalCount,
        time_minutes: elapsedMinutes,
        weak_phase: weakestPhaseKey,
    },
});
displayReflectionCoaching(fb.feedback, fb.next_steps, fb.encouragement);
```

## General tutor (open-ended help)

```js
const r = await window.NETS_AI.tutor({
    phase: 'real_life',
    question: RL_SCENARIO.questions[i].text,
    studentInput: userAnswer,
});
showTutorMessage(r.response);
```

## Live AI Tutor (Wave F2)

Three new methods talk to the persistent floating tutor backend (`/api/ai/tutor/*`).
All three are thin async wrappers; no payload mutation.

### `NETS_AI.tutorChat({ session_id, hw_id, phase, question_id?, message })`

POSTs to `/api/ai/tutor/chat`. Returns `{ response, message_id }` on success.
On the 60-message session cap, returns `{ _cap: true, _error: true, message }`.
On any other error, returns `{ _error: true, message }`.

```js
const res = await window.NETS_AI.tutorChat({
    session_id: localStorage.getItem('nets_tutor_session'),
    hw_id: window.NETS_CTX.hwId,
    phase: 'practice',           // 'preview' | 'practice' | 'boss'
    question_id: 'boss_q1',      // optional; null/undefined in preview
    message: 'How do I start this one?',
});
if (res.response) showTutorMessage(res.response);
```

### `NETS_AI.tutorHistory({ session_id, hw_id })`

GETs `/api/ai/tutor/history`. Returns `{ turns: [{phase, question_id?, role, content, created_at}, ...] }` (last 50, chronological).
The widget uses this on page load to restore the conversation.

### `NETS_AI.bossPlan({ session_id, hw_id })`

POSTs to `/api/ai/tutor/boss-plan`. Returns `{ ordered: [{question_id, framing_text}, ...], persona_traits: string[] }`.
F3 will call this at boss-start to reorder the question pool and prepend personalized framing. Available as a method now so F3 ships as pure frontend wiring.

## `nets:phase-change` event

Fires from `setStage(n)` whenever the runtime advances the homework phase.
The persistent tutor widget (injected near `</body>`) listens to this and swaps its mode badge automatically.

```js
document.dispatchEvent(new CustomEvent('nets:phase-change', {
    detail: {
        phase: 'preview' | 'practice' | 'boss',
        stage: numericStage,
        questionId: 'optional-id',
    },
}));
```

Stage→phase mapping (matches the existing `phaseMap` for the progress bar):
- stages `0`, `1`, `2`            → `preview`
- stages `2.5` through `6.5`      → `practice` (flashcards, memory_sprint, gb_*, real_life, reading, consolidation)
- stages `7`, `7.5`               → `boss`
- stages `7.7+` (reflection/done) → `preview` (reverts to open Q&A)

## Graceful offline degradation

When served as `file://`, `isAvailable()` returns false. Homework falls back to existing `ans[]` string match only. No errors thrown.

## How it gets injected

The backend's `inject()` function (`server/services/injector.py`) appends two `<script>` tags before `</body>`:

1. `<script>window.NETS_CTX = { apiBase, subject, grade, homeworkTitle, homeworkSummary };</script>`
2. `<script src="/static/runtime/runtime.js"></script>`

Both `/api/homeworks/{id}/preview` and `/h/{id}` always inject these via the shared `render_homework()` helper in `server/routes/homework_page.py`.
