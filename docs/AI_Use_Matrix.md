# NETS AI Use Matrix & Academic-Integrity Policy

**Status:** Published policy. Source-of-truth research: `docs/NETS_Academic_Integrity_AntiCheat_Research.md`. Machine-readable companion: `server/services/ai_use_policy.py` (`policy_for(phase, subphase)`).

NETS is an AI-driven learning platform, so it carries an integrity responsibility the credential authorities (AP / IB / Cambridge) don't have: **NETS operates the AI.** This document states, per content type, what NETS's own AI does and what external AI is permitted — and the principles that govern how integrity is handled.

## Principles (non-negotiable)

1. **Process-supervision-first, NOT detection software.** AP, IB, and Cambridge all explicitly decline to rely on AI-detection tools. Detection has a ~61% false-positive rate for non-native English speakers — exactly the NETS user base. **NETS does not run, and will not market, AI-detection as a primary integrity mechanism.**
2. **Signals are teacher intelligence, never automatic punishment.** Behavioral signals (response timing, paste, sudden-mastery patterns) are routed to a teacher Review Queue as *context*. They never auto-fail, auto-block, or apply a grade penalty (Cambridge explicitly bans grade-as-discipline).
3. **Soft friction is allowed; it is non-punitive.** A strong signal may surface a gentle "explain your reasoning in your own words" nudge. The nudge never gates progress; the answer is already graded; the student is never blocked.
4. **Inference, not retrieval.** Assessments (Boss Arena, Real-Life Challenge, CBP reasoning) test the *mechanic*, not a memorizable answer — structurally cheat-resistant. Retakes use the same concepts, different questions.
5. **NETS's own AI never leaks answers.** The Socratic Tutor, Boss generator, and graders never reveal an upcoming answer, and cannot be manipulated (prompt-injection) into doing so. Student free-text is fenced as untrusted; answer keys are stripped before any client response.

## The Matrix (per content type)

| Phase / surface | `policy_for` key | NETS's own AI | External AI | Assessment? |
|---|---|---|---|---|
| Hub / Case-Based Preview setup | `preview` | Socratic Tutor active; no answer reveals | Not permitted (supervised block) | No |
| Case-Based Preview checkpoints + reasoning | `practice/case_based` | Tutor active; answer_spec redacted at the boundary | Not permitted | **Yes** |
| Flashcards | `practice` | Hints, explanations | Permitted for independent study | No |
| Memory Check (Quizlet-style) | `practice` | Explains on a wrong answer | Permitted for study; not during the timed run | No |
| Practice Arc games (8) | `practice` | Hints only; no formula/answer leak | Not permitted | No |
| Real-Life Challenge | `practice` | No formula reveal, no answer leak | Not permitted | No |
| **Boss Arena** | `boss` | **None — assessment moment** | Not permitted | **Yes** |
| Reflection / Debrief | `practice/reflection` | Active (post-hoc coaching) | Permitted with acknowledgment | No |
| Outcome-track exam simulation (future) | — | None (proctored-condition sim) | Not permitted | **Yes** |

`policy_for(phase, subphase)` resolves `phase + "/" + subphase`, then `phase`, then a safe default `{tutor: False, external_ai: False, assessment: True}`. The integrity-flag engine reads `assessment` to weight a paste on the Boss/CBP far more heavily than a paste during free practice.

## How integrity works in software

- **Hybrid Grading + Review Queue** is the backbone (`review_queue` table, `/api/ai/review-queue`). Low-confidence AI grades AND behavioral integrity flags land here for a teacher with student context — never an automatic adverse action.
- **Behavioral signals (advisory):** the runtime forwards optional `client_time_ms` + `paste_detected` (server-clamped); they populate `phase_attempts.time_ms` + a `session_events` `integrity:paste` event. They **never** affect `score`/`is_correct`/`hp`/gating.
- **Flag engine** (`server/services/integrity_signals.py`, conservative + opt-in): `too_fast` (off by default), `paste_on_assessment`, `sudden_mastery` (needs prior-mastery ≤ 0.40 AND assessment correct-rate ≥ 0.90 AND ≥ 3 items). A genuinely-ready student is not flagged (regression-tested).
- **Soft friction:** a *strong* flag attaches an `integrity_nudge {type, message}` to the response; the student sees a dismissible "explain your reasoning" card beside the feedback — never a block. `reason_code`/thresholds are never sent to the client.
- **Authentication of Authorship** (AP-Capstone model): a teacher affirms a session is authentic via `POST /api/integrity/affirm`; the affirmation can resolve linked integrity flags. Process supervision documented in software — not AI detection.

## What NETS does NOT build
AI-detection software as a primary mechanism; Turnitin as a default-on feature (optional integration only, with the disclosure that scores are signals, not proof); automatic grade penalties from behavioral signals.

## Appeals
A flag is never the sole basis for an adverse action. In a supervised block the teacher affirmation resolves it; the student's record is not marked from a signal alone.
