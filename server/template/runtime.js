/**
 * NETS_AI — Runtime tutor bridge.
 * Loaded by the homework HTML when served by the backend (not standalone).
 * Exposes window.NETS_AI with 4 async methods mirroring /api/ai/* endpoints.
 *
 * The homework template should call these from its answer-check paths.
 */
(function() {
    // Detect if we're running inside the NETS backend (has /api routes available)
    // vs standalone file:// — fall back to no-AI mode gracefully.
    const isBackendHosted = window.location.protocol !== 'file:'
                         && window.location.origin
                         && !window.location.origin.startsWith('null');

    // Subject/grade injected by backend into the page (via data attributes on <body> or a global).
    // Fallback to safe defaults if missing.
    const ctx = window.NETS_CTX || {};

    const API_BASE = (ctx.apiBase || '') + '/api/ai';

    async function _post(path, body) {
        if (!isBackendHosted) {
            return { _offline: true, correct: null, feedback: 'AI tutor not available offline.' };
        }
        try {
            const res = await fetch(API_BASE + path, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                // Wave F2: surface session-cap (429) so the widget can lock input.
                if (res.status === 429) {
                    return { _cap: true, _error: true, message: err.detail?.error || 'Session limit reached.' };
                }
                return { _error: true, message: err.detail?.error || res.statusText };
            }
            return await res.json();
        } catch (e) {
            return { _error: true, message: String(e) };
        }
    }

    async function _get(path, query) {
        if (!isBackendHosted) {
            return { _offline: true, turns: [] };
        }
        try {
            const qs = new URLSearchParams(query || {}).toString();
            const url = API_BASE + path + (qs ? ('?' + qs) : '');
            const res = await fetch(url, { method: 'GET' });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                return { _error: true, message: err.detail?.error || res.statusText };
            }
            return await res.json();
        } catch (e) {
            return { _error: true, message: String(e) };
        }
    }

    /**
     * Check a typed answer semantically.
     * Use when exact string match against ans[] fails but you want to give partial credit.
     * @param {Object} opts
     * @param {string} opts.question - The question text
     * @param {string} opts.studentAnswer - What the student typed
     * @param {string[]} opts.expectedAnswers - The accepted answers from ans[]
     * @param {string} opts.tier - "EASY" | "MEDIUM" | "HARD"
     * @param {string} [opts.context] - Optional extra context (e.g., recent flashcards)
     * @returns {Promise<{correct, score, feedback, matched_expected}>}
     */
    async function checkAnswer(opts) {
        return _post('/check-answer', {
            question: opts.question,
            student_answer: opts.studentAnswer,
            expected_answers: opts.expectedAnswers || [],
            subject: ctx.subject || 'math-algebra',
            grade: ctx.grade || 8,
            tier: opts.tier || 'MEDIUM',
            context: opts.context || null,
        });
    }

    /**
     * Boss combat turn. Call on every boss answer submission.
     * @param {Object} opts
     * @param {string} opts.bossQuestion
     * @param {string} opts.studentAnswer
     * @param {string[]} opts.expectedAnswers
     * @param {number} opts.damageValue - base damage for this question
     * @param {number} opts.hpRemaining - boss HP remaining
     * @param {number} opts.attemptNumber - 1 for first try, 2 for retry, etc
     * @returns {Promise<{correct, damage_dealt, boss_response, hint, score}>}
     */
    async function bossTurn(opts) {
        const body = {
            boss_question: opts.bossQuestion,
            student_answer: opts.studentAnswer,
            expected_answers: opts.expectedAnswers || [],
            damage_value: opts.damageValue || 10,
            hp_remaining: opts.hpRemaining || 100,
            attempt_number: opts.attemptNumber || 1,
            subject: ctx.subject || 'math-algebra',
            grade: ctx.grade || 8,
        };
        // Wave F3: forward persona_traits when present (from boss_plan response).
        if (opts.persona_traits && opts.persona_traits.length) {
            body.persona_traits = opts.persona_traits;
        }
        return _post('/boss-turn', body);
    }

    /**
     * Get personalized reflection feedback.
     * @param {Object} opts
     * @param {string} opts.studentReflection
     * @param {Object} opts.performance - {correct, total, time_minutes, weak_phase}
     * @returns {Promise<{feedback, next_steps, encouragement}>}
     */
    async function reflectionFeedback(opts) {
        return _post('/reflection', {
            homework_title: ctx.homeworkTitle || '',
            homework_summary: ctx.homeworkSummary || '',
            student_reflection: opts.studentReflection,
            performance: opts.performance || {},
            subject: ctx.subject || 'math-algebra',
            grade: ctx.grade || 8,
        });
    }

    /**
     * General tutor help. Use for open-ended questions, "I'm stuck" prompts, etc.
     * @param {Object} opts
     * @param {string} opts.phase - current phase name
     * @param {string} opts.question
     * @param {string} opts.studentInput
     * @param {string} [opts.context]
     * @returns {Promise<{response, guidance_type}>}
     */
    async function tutor(opts) {
        return _post('/tutor', {
            phase: opts.phase,
            question: opts.question,
            student_input: opts.studentInput,
            subject: ctx.subject || 'math-algebra',
            grade: ctx.grade || 8,
            context: opts.context || null,
        });
    }

    // Convenience: check if AI is available right now
    function isAvailable() { return isBackendHosted; }

    // ─── Wave F2 — live tutor widget endpoints ───────────────────
    /**
     * Send one tutor chat turn.
     * @param {Object} opts
     * @param {string} opts.session_id  - client-side UUID, persisted in localStorage
     * @param {string} opts.hw_id
     * @param {string} opts.phase       - 'preview' | 'practice' | 'boss'
     * @param {string} [opts.question_id]
     * @param {string} opts.message
     * @returns {Promise<{response: string, message_id: number} | {_error|_cap|_offline: true, message?: string}>}
     */
    async function tutorChat(opts) {
        const body = {
            session_id: opts.session_id,
            hw_id: opts.hw_id,
            phase: opts.phase,
            message: opts.message,
        };
        if (opts.question_id) body.question_id = opts.question_id;
        if (opts.screen_context) body.screen_context = opts.screen_context;
        return _post('/tutor/chat', body);
    }

    /**
     * Fetch saved chat history for a session (last 50 turns, chronological).
     * @param {Object} opts
     * @param {string} opts.session_id
     * @param {string} opts.hw_id
     * @returns {Promise<{turns: Array<{phase, question_id?, role, content, created_at}>}>}
     */
    async function tutorHistory(opts) {
        return _get('/tutor/history', {
            session_id: opts.session_id,
            hw_id: opts.hw_id,
        });
    }

    /**
     * Build a personalized boss-question plan. Used by F3 (exposed now).
     * @param {Object} opts
     * @param {string} opts.session_id
     * @param {string} opts.hw_id
     * @returns {Promise<{ordered: Array<{question_id, framing_text}>, persona_traits: string[]}>}
     */
    async function bossPlan(opts) {
        return _post('/tutor/boss-plan', {
            session_id: opts.session_id,
            hw_id: opts.hw_id,
        });
    }

    // Expose
    window.NETS_AI = {
        checkAnswer,
        bossTurn,
        reflectionFeedback,
        tutor,
        tutorChat,
        tutorHistory,
        bossPlan,
        isAvailable,
        _ctx: ctx,
    };

    // ---------------------------------------------------------------
    // Generic event bridge — template code (or other editors) can dispatch
    // CustomEvents instead of calling NETS_AI directly, so hooks remain
    // declarative. Events consumed:
    //   document.dispatchEvent(new CustomEvent('nets:submit', { detail: {
    //       kind: 'boss' | 'answer' | 'reflection' | 'tutor',
    //       payload: {...},          // matches NETS_AI.<method> opts
    //       onResult: (res) => {},   // optional callback
    //   }}))
    // Fallback feedback is always delivered so the session never stalls.
    // ---------------------------------------------------------------
    const FALLBACK = {
        boss: { correct: null, damage_dealt: 0, boss_response: 'Davom eting!', hint: null, score: 0 },
        answer: { correct: null, score: 0, feedback: 'Javob qabul qilindi.', matched_expected: null },
        reflection: { feedback: 'Sessiya yakunlandi. Ajoyib ish!', next_steps: [], encouragement: 'Davom eting!' },
        tutor: { response: 'Yordam hozircha mavjud emas. Qayta urinib ko\'ring.', guidance_type: 'encouragement' },
    };

    document.addEventListener('nets:submit', async (ev) => {
        const detail = ev.detail || {};
        const kind = detail.kind;
        const payload = detail.payload || {};
        const cb = typeof detail.onResult === 'function' ? detail.onResult : null;
        let result;
        try {
            if (kind === 'boss') result = await bossTurn(payload);
            else if (kind === 'answer') result = await checkAnswer(payload);
            else if (kind === 'reflection') result = await reflectionFeedback(payload);
            else if (kind === 'tutor') result = await tutor(payload);
            else { console.warn('[NETS_AI] unknown nets:submit kind:', kind); return; }
            if (result && (result._error || result._offline)) {
                result = Object.assign({}, FALLBACK[kind] || {}, { _fallback: true, _reason: result });
            }
        } catch (err) {
            console.warn('[NETS_AI] nets:submit failed:', err);
            result = Object.assign({}, FALLBACK[kind] || {}, { _fallback: true, _reason: String(err) });
        }
        if (cb) { try { cb(result); } catch (e) { console.warn('[NETS_AI] onResult threw:', e); } }
        document.dispatchEvent(new CustomEvent('nets:result', { detail: { kind, result } }));
    });

    // Log readiness once
    console.log('[NETS_AI] ready. Available:', isAvailable(), 'Context:', ctx);
})();
