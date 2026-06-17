    (function () {
        // Wave F2 — persistent floating tutor widget. Listens for `nets:phase-change`,
        // talks to /api/ai/tutor/{chat,history}. Pure vanilla JS, all assets inline.

        const PHASE_LABELS = {
            en: {
                preview:  'Preview — ask me anything',
                practice: "Practice — I'll guide you",
                boss:     "Boss — let's go",
                send:     'Send',
                placeholder: 'Type your question…',
                cap:      'Session limit reached.',
                error:    'Something went wrong. Please try again.',
                offline:  'Tutor is offline right now.',
            },
            uz: {
                preview:  "Ko'rib chiqish — istalgan savolni bering",
                practice: "Mashq — yo'l ko'rsataman",
                boss:     "Boss — boshladik",
                send:     'Yuborish',
                placeholder: "Savolingizni yozing…",
                cap:      "Sessiya chegarasiga yetildi.",
                error:    "Xatolik yuz berdi. Qaytadan urinib ko'ring.",
                offline:  "Tyutor hozir ishlamaydi.",
            },
            ru: {
                preview:  'Превью — спрашивайте, что хотите',
                practice: 'Практика — буду направлять',
                boss:     'Босс — поехали',
                send:     'Отправить',
                placeholder: 'Введите вопрос…',
                cap:      'Достигнут лимит сообщений.',
                error:    'Что-то пошло не так. Попробуйте ещё раз.',
                offline:  'Тьютор сейчас недоступен.',
            },
        };

        function detectLang() {
            const ctx = window.NETS_CTX || {};
            const raw = (ctx.lang || document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
            return PHASE_LABELS[raw] ? raw : 'en';
        }

        const lang = detectLang();
        const L = PHASE_LABELS[lang];
        const SESSION_CAP = 60;

        // Generate UUID without crypto.randomUUID (older Safari).
        function uuid() {
            if (window.crypto && typeof window.crypto.randomUUID === 'function') {
                return window.crypto.randomUUID();
            }
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
                const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        // NOTE: this inline script runs BEFORE the injector's
        // <script>window.NETS_CTX={...}<\/script><script src="/static/runtime/runtime.js"><\/script>
        // tags (which the injector appends just before <\/body>). So we cannot
        // read NETS_CTX or NETS_AI at IIFE-init — they aren't defined yet.
        // Resolve hwId lazily on first read so it picks up NETS_CTX once the
        // injector's scripts have executed.
        function currentHwId() {
            const c = window.NETS_CTX || {};
            return c.hwId
                || (document.body.dataset && document.body.dataset.hwId)
                || '';
        }

        const state = {
            sessionId: localStorage.getItem('nets_tutor_session') || uuid(),
            get hwId() { return currentHwId(); },
            currentPhase: 'preview',
            currentQuestionId: null,
            messageCount: 0,
            isOpen: false,
            isSending: false,
            // Wave J / T4: warning + fail state (per page-load).
            homeworkFailed: false,
            bigWarningDismissed: false,
            lastTypingIndex: null,
        };
        try { localStorage.setItem('nets_tutor_session', state.sessionId); } catch (e) { /* private mode */ }

        // ── FE-3 — mirror active question metadata to window.NETS_STATE ──
        // runtime.js#collectRuntimeContext reads [data-nets-active] markers
        // first and falls back to window.NETS_STATE. We do BOTH:
        //   1. Tag the currently visible screen wrapper with
        //      data-nets-active="true" / data-question-id / data-subphase so
        //      the collector scrapes screen_context only from that one node.
        //      (.screen.active is the single phase root the runtime keeps
        //      shown at any time; using it as the active container means
        //      screen_context never carries content from a hidden screen.)
        //   2. Mirror the same triplet onto window.NETS_STATE for the
        //      fallback path (e.g., a brief gap between phase transitions
        //      when no .screen has the .active class yet).
        function syncNetsState() {
            window.NETS_STATE = window.NETS_STATE || {};
            window.NETS_STATE.phase = state.currentPhase;
            window.NETS_STATE.subphase = (typeof currentSubphase !== 'undefined') ? currentSubphase : null;
            window.NETS_STATE.questionId = state.currentQuestionId;
            // Strip any previously tagged active node before tagging a new
            // one so the collector never sees two "active" wrappers.
            try {
                document.querySelectorAll('[data-nets-active="true"]').forEach(function(n) {
                    n.removeAttribute('data-nets-active');
                });
            } catch (e) { /* DOM unavailable */ }
            try {
                const activeScreen = document.querySelector('.screen.active');
                if (activeScreen) {
                    activeScreen.setAttribute('data-nets-active', 'true');
                    if (state.currentQuestionId) {
                        activeScreen.setAttribute('data-question-id', String(state.currentQuestionId));
                    } else {
                        activeScreen.removeAttribute('data-question-id');
                    }
                    if (typeof currentSubphase !== 'undefined' && currentSubphase) {
                        activeScreen.setAttribute('data-subphase', String(currentSubphase));
                    } else {
                        activeScreen.removeAttribute('data-subphase');
                    }
                }
            } catch (e) { /* DOM unavailable */ }
        }

        // ── DOM refs ────────────────────────────────────────────
        const root        = document.getElementById('nets-ai-tutor');
        const fab         = document.getElementById('nets-tutor-fab');
        const panel       = document.getElementById('nets-tutor-panel');
        const badge       = document.getElementById('nets-tutor-phase-badge');
        const closeBtn    = document.getElementById('nets-tutor-close');
        const avatarEl    = document.getElementById('nets-tutor-avatar');
        const messages  = document.getElementById('nets-tutor-messages');
        const inputForm = document.getElementById('nets-tutor-input-form');
        const input     = document.getElementById('nets-tutor-input');
        const sendBtn   = document.getElementById('nets-tutor-send');
        const capEl     = document.getElementById('nets-tutor-cap-warning');
        // Wave J / T4: warning UI refs. Optional — fall back gracefully
        // if any are missing (e.g., older cached template).
        const warningChip   = document.getElementById('nets-tutor-warning-chip');
        const warningCount  = warningChip && warningChip.querySelector('.nets-tutor-warning-count');
        const bigWarning    = document.getElementById('nets-tutor-big-warning');
        const bigWarningTxt = bigWarning && bigWarning.querySelector('.nets-tutor-big-warning-text');
        const bigWarningX   = bigWarning && bigWarning.querySelector('.nets-tutor-big-warning-dismiss');
        const failOverlay   = document.getElementById('nets-tutor-fail-overlay');
        const failTitle     = failOverlay && failOverlay.querySelector('.nets-tutor-fail-title');
        const failSubtitle  = failOverlay && failOverlay.querySelector('.nets-tutor-fail-subtitle');

        if (!root) return;  // safety

        // Apply localized labels.
        input.placeholder = L.placeholder;
        sendBtn.textContent = L.send;
        capEl.textContent = L.cap;
        updateBadge('preview');

        // ── Markdown subset rendering — XSS-safe via textContent ───
        // Supports: paragraphs (blank-line split), **bold**, *italic*,
        // `code`, line breaks, and "- " or "1. " lists.
        function renderMarkdownInto(parent, text) {
            if (!text) return;
            const blocks = String(text).split(/\n{2,}/);
            for (const block of blocks) {
                const trimmed = block.trim();
                if (!trimmed) continue;
                const lines = trimmed.split('\n');
                const isUl = lines.every(l => /^\s*[-*]\s+/.test(l));
                const isOl = lines.every(l => /^\s*\d+[.)]\s+/.test(l));
                if (isUl || isOl) {
                    const list = document.createElement(isUl ? 'ul' : 'ol');
                    for (const line of lines) {
                        const li = document.createElement('li');
                        const stripped = line.replace(/^\s*(?:[-*]|\d+[.)])\s+/, '');
                        appendInline(li, stripped);
                        list.appendChild(li);
                    }
                    parent.appendChild(list);
                } else {
                    const p = document.createElement('p');
                    const segments = trimmed.split('\n');
                    segments.forEach((seg, idx) => {
                        appendInline(p, seg);
                        if (idx < segments.length - 1) p.appendChild(document.createElement('br'));
                    });
                    parent.appendChild(p);
                }
            }
        }

        // Inline markdown — bold, italic, code, strikethrough. Token-based
        // to avoid regex pitfalls. Code is highest precedence (so backticks
        // inside it are literal), then ~~strike~~, then **bold**/*italic*.
        // Emoji preservation note: we tokenize on ASCII punctuation only —
        // multibyte emoji codepoints inside a token are copied through via
        // textContent verbatim, so `**Yaxshi 💯**` renders as
        // `<strong>Yaxshi 💯</strong>`.
        function appendInline(parent, text) {
            // Split by `code` first (highest precedence), then bold/italic inside.
            const parts = String(text).split(/(`[^`]+`)/g);
            for (const part of parts) {
                if (!part) continue;
                if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
                    const code = document.createElement('code');
                    code.textContent = part.slice(1, -1);
                    parent.appendChild(code);
                } else {
                    appendStrikethrough(parent, part);
                }
            }
        }

        function appendStrikethrough(parent, text) {
            // Tokenize ~~strike~~ before bold/italic. The character class
            // [\s\S]+? (non-greedy any-char incl newlines) keeps emojis intact.
            const re = /~~([\s\S]+?)~~/g;
            let lastIndex = 0;
            let m;
            while ((m = re.exec(text)) !== null) {
                if (m.index > lastIndex) {
                    appendBoldItalic(parent, text.slice(lastIndex, m.index));
                }
                const s = document.createElement('s');
                appendBoldItalic(s, m[1]);
                parent.appendChild(s);
                lastIndex = re.lastIndex;
            }
            if (lastIndex < text.length) {
                appendBoldItalic(parent, text.slice(lastIndex));
            }
        }

        function appendBoldItalic(parent, text) {
            // Tokenize **bold** and *italic*. Greedy on bold first.
            // Use [\s\S] (incl emoji codepoints) instead of [^*] — the
            // bare-negated class works fine but [^*]+? is identical and
            // clearer. Emoji are preserved verbatim via textContent.
            const re = /(\*\*[^*]+?\*\*|\*[^*\n]+?\*)/g;
            let lastIndex = 0;
            let m;
            while ((m = re.exec(text)) !== null) {
                if (m.index > lastIndex) {
                    parent.appendChild(document.createTextNode(text.slice(lastIndex, m.index)));
                }
                const tok = m[0];
                if (tok.startsWith('**') && tok.endsWith('**')) {
                    const s = document.createElement('strong');
                    s.textContent = tok.slice(2, -2);
                    parent.appendChild(s);
                } else if (tok.startsWith('*') && tok.endsWith('*')) {
                    const e = document.createElement('em');
                    e.textContent = tok.slice(1, -1);
                    parent.appendChild(e);
                }
                lastIndex = re.lastIndex;
            }
            if (lastIndex < text.length) {
                parent.appendChild(document.createTextNode(text.slice(lastIndex)));
            }
        }

        // ── Assistant-only formatter ─────────────────────────────
        // Tries JSON first, then markdown (with fenced code blocks).
        // XSS-safe: every string lands in textContent / createTextNode;
        // we never assign untrusted output to innerHTML. KaTeX runs
        // afterwards on the built DOM so $x^2$ etc. render too.
        function _isPrimitive(v) {
            return v === null || typeof v !== 'object';
        }
        function _hasNestedObject(v) {
            if (Array.isArray(v)) {
                return v.some(item => !_isPrimitive(item));
            }
            if (v && typeof v === 'object') {
                return Object.values(v).some(item => !_isPrimitive(item));
            }
            return false;
        }
        function renderJsonInto(parent, value) {
            const wrap = document.createElement('div');
            wrap.className = 'nets-tutor-json';
            const renderAsPre = Array.isArray(value) || _hasNestedObject(value);
            if (renderAsPre) {
                const pre = document.createElement('pre');
                const code = document.createElement('code');
                code.textContent = JSON.stringify(value, null, 2);
                pre.appendChild(code);
                wrap.appendChild(pre);
            } else {
                const dl = document.createElement('dl');
                dl.className = 'nets-tutor-json-dl';
                for (const key of Object.keys(value)) {
                    const dt = document.createElement('dt');
                    dt.textContent = String(key);
                    const dd = document.createElement('dd');
                    const v = value[key];
                    if (v === null) {
                        dd.textContent = 'null';
                    } else if (typeof v === 'string') {
                        appendInline(dd, v);
                    } else {
                        dd.textContent = String(v);
                    }
                    dl.appendChild(dt);
                    dl.appendChild(dd);
                }
                wrap.appendChild(dl);
            }
            parent.appendChild(wrap);
        }

        // Markdown-with-fences rendering — XSS-safe via textContent.
        // Whitelisted tags: p, ul, ol, li, code, pre, strong, em, br.
        function renderMarkdownWithFencesInto(parent, text) {
            if (!text) return;
            const src = String(text);
            const lines = src.split('\n');
            let i = 0;
            const buf = [];
            const flushBuf = () => {
                if (!buf.length) return;
                const joined = buf.join('\n');
                if (joined.trim()) renderMarkdownInto(parent, joined);
                buf.length = 0;
            };
            while (i < lines.length) {
                const line = lines[i];
                const fence = /^\s*```(.*)$/.exec(line);
                if (fence) {
                    flushBuf();
                    const codeLines = [];
                    i += 1;
                    while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) {
                        codeLines.push(lines[i]);
                        i += 1;
                    }
                    if (i < lines.length) i += 1;
                    const pre = document.createElement('pre');
                    const code = document.createElement('code');
                    code.textContent = codeLines.join('\n');
                    pre.appendChild(code);
                    parent.appendChild(pre);
                    continue;
                }
                buf.push(line);
                i += 1;
            }
            flushBuf();
        }

        function _maybeRenderMath(container) {
            try {
                if (window.renderMathInElement) {
                    window.renderMathInElement(container, {
                        delimiters: [
                            { left: '$$', right: '$$', display: true },
                            { left: '$',  right: '$',  display: false },
                            { left: '\\(', right: '\\)', display: false },
                            { left: '\\[', right: '\\]', display: true }
                        ],
                        throwOnError: false,
                        ignoredTags: ['script','noscript','style','textarea','pre','code','option']
                    });
                }
            } catch (e) { /* best-effort */ }
        }

        function formatAssistantMessage(text, container) {
            const raw = String(text == null ? '' : text);
            const trimmed = raw.trim();
            if (trimmed && (trimmed[0] === '{' || trimmed[0] === '[')) {
                try {
                    const parsed = JSON.parse(trimmed);
                    if (parsed !== null && typeof parsed === 'object') {
                        renderJsonInto(container, parsed);
                        _maybeRenderMath(container);
                        return container;
                    }
                } catch (e) { /* fall through to markdown */ }
            }
            renderMarkdownWithFencesInto(container, raw);
            if (!container.firstChild) container.textContent = raw;
            _maybeRenderMath(container);
            return container;
        }

        // Expose for tests / future callers.
        window._netsFormatAssistantMessage = formatAssistantMessage;

        // ── Message rendering ───────────────────────────────────
        function appendMessage(role, content) {
            const el = document.createElement('div');
            el.className = 'nets-tutor-msg ' + (role === 'user' ? 'user' : (role === 'error' ? 'error' : 'assistant'));
            if (role === 'user' || role === 'error') {
                renderMarkdownInto(el, content);
                if (!el.firstChild) el.textContent = String(content || '');
            } else {
                formatAssistantMessage(content, el);
            }
            messages.appendChild(el);
            messages.scrollTop = messages.scrollHeight;
            return el;
        }

        function appendTyping() {
            const el = document.createElement('div');
            el.className = 'nets-tutor-typing';
            el.id = 'nets-tutor-typing-indicator';
            for (let i = 0; i < 3; i++) el.appendChild(document.createElement('span'));
            messages.appendChild(el);
            // Wave J / T4: rotating thinking phrase under the dots.
            const phraseEl = document.createElement('div');
            phraseEl.className = 'nets-tutor-typing-phrase';
            phraseEl.id = 'nets-tutor-typing-phrase';
            phraseEl.textContent = pickTypingPhrase();
            messages.appendChild(phraseEl);
            // Force a reflow so the fade-in transition fires (CSS opacity 0 → 1).
            // Reading offsetHeight is the canonical "flush layout" idiom.
            void phraseEl.offsetHeight;
            phraseEl.classList.add('visible');
            messages.scrollTop = messages.scrollHeight;
            return el;
        }
        function removeTyping() {
            const el = document.getElementById('nets-tutor-typing-indicator');
            if (el && el.parentNode) el.parentNode.removeChild(el);
            const ph = document.getElementById('nets-tutor-typing-phrase');
            if (ph && ph.parentNode) ph.parentNode.removeChild(ph);
        }

        // ── Phase badge ─────────────────────────────────────────
        function updateBadge(phase) {
            const p = (phase === 'practice' || phase === 'boss') ? phase : 'preview';
            badge.dataset.phase = p;
            badge.textContent = L[p];
        }

        // ── Cap handling ────────────────────────────────────────
        function applyCap() {
            // Wave J / T4: a homework_failed lock is sticky — the cap
            // path must not re-enable the input even if messageCount
            // happens to be under SESSION_CAP.
            if (state.homeworkFailed) {
                input.disabled = true;
                sendBtn.disabled = true;
                capEl.hidden = true;
                return;
            }
            if (state.messageCount >= SESSION_CAP) {
                input.disabled = true;
                sendBtn.disabled = true;
                capEl.hidden = false;
            } else {
                input.disabled = false;
                sendBtn.disabled = state.isSending;
                capEl.hidden = true;
            }
        }

        // ── Wave J / T4: warning chip + banner + fail overlay ──
        // The state machine (server/services/warnings.py) tells us
        // the *current* level + cumulative deduction on every reply.
        // The chip shows running state; the banner only fires on the
        // single response that triggered level 8 (is_big_warning).
        // bigWarningDismissed is sticky-per-session-load — once the
        // student ×s the banner we don't re-show it for the same
        // page-load even if the level stays at 8.
        const WARNING_TOOLTIPS = {
            uz: function (lvl) {
                if (lvl >= 8) return "So'nggi ogohlantirish — −15% jami. Yana bitta = uy vazifasi failga ketadi.";
                if (lvl === 7) return "7-strayk — −5% qulflandi. Yana bitta = −10%.";
                return lvl + " mayda ogohlantirish — −5% gacha yana " + (7 - lvl) + " ta.";
            },
            ru: function (lvl) {
                if (lvl >= 8) return "Последнее предупреждение — −15% всего. Ещё одно = провал.";
                if (lvl === 7) return "7-й страйк — −5% зафиксировано. Ещё одно = −10%.";
                return lvl + " мягких предупреждений — до −5% ещё " + (7 - lvl) + ".";
            },
            en: function (lvl) {
                if (lvl >= 8) return "Last chance — −15% total. One more = homework fails.";
                if (lvl === 7) return "Strike 7 hit — −5% locked. 1 more = −10%.";
                return lvl + " mild warning" + (lvl === 1 ? "" : "s") + " — " + (7 - lvl) + " more before −5%.";
            },
        };
        const BIG_WARNING_TEXT = {
            uz: "So'nggi ogohlantirish — yana bitta = uy vazifasi failga ketadi. Hozirgi jarima: −15%",
            ru: "Последнее предупреждение — ещё одно = провал. Текущий штраф: −15%",
            en: "Last chance — one more = homework fails. Current penalty: −15%",
        };
        const FAIL_LABELS = {
            uz: { title: "Uy vazifasi tugadi",  subtitle: "Refleksiyaga o'tamiz..." },
            ru: { title: "Урок не пройден",       subtitle: "Переходим к рефлексии..." },
            en: { title: "Homework failed",      subtitle: "Skipping to reflection..." },
        };

        function updateWarningChip(level, cumulativeDeductionPct) {
            if (!warningChip || !warningCount) return;
            const lvl = Number(level) || 0;
            if (lvl <= 0) {
                warningChip.hidden = true;
                return;
            }
            warningChip.hidden = false;
            warningCount.textContent = String(lvl);
            // Tier: 1-6 yellow (default), 7 orange, >=8 red.
            let tier;
            if (lvl >= 8)      tier = 'red';
            else if (lvl >= 7) tier = 'orange';
            else               tier = 'yellow';
            warningChip.dataset.tier = tier;
            const tipFn = WARNING_TOOLTIPS[lang] || WARNING_TOOLTIPS.en;
            warningChip.title = tipFn(lvl);
            warningChip.setAttribute('aria-label', tipFn(lvl));
        }

        let bigWarningTimer = null;
        function showBigWarningBanner() {
            if (!bigWarning || !bigWarningTxt) return;
            if (state.bigWarningDismissed) return;  // sticky for the page-load
            bigWarningTxt.textContent = BIG_WARNING_TEXT[lang] || BIG_WARNING_TEXT.en;
            bigWarning.hidden = false;
            if (bigWarningTimer) clearTimeout(bigWarningTimer);
            bigWarningTimer = setTimeout(function () {
                bigWarning.hidden = true;
            }, 8000);
        }
        function dismissBigWarning() {
            if (!bigWarning) return;
            bigWarning.hidden = true;
            state.bigWarningDismissed = true;
            if (bigWarningTimer) { clearTimeout(bigWarningTimer); bigWarningTimer = null; }
        }
        if (bigWarningX) bigWarningX.addEventListener('click', dismissBigWarning);

        function showFailOverlay(cumulativeDeductionPct) {
            if (state.homeworkFailed) return;  // already triggered
            state.homeworkFailed = true;
            // Lock all input.
            input.disabled = true;
            sendBtn.disabled = true;
            removeTyping();
            capEl.hidden = true;
            const labels = FAIL_LABELS[lang] || FAIL_LABELS.en;
            if (failOverlay) {
                if (failTitle)    failTitle.textContent = labels.title;
                if (failSubtitle) failSubtitle.textContent = labels.subtitle;
                failOverlay.hidden = false;
            }
            // After a beat, dispatch phase-change + custom event so the
            // runtime jumps to reflection. detail.failed=true lets the
            // reflection phase render the fail-aware variant.
            const deductionPct = Number(cumulativeDeductionPct) || 0;
            setTimeout(function () {
                try {
                    document.dispatchEvent(new CustomEvent('nets:phase-change', {
                        detail: {
                            phase: 'reflection',
                            failed: true,
                            reason: 'troll-strikes',
                            deduction_pct: deductionPct,
                        },
                    }));
                } catch (e) { /* DOM may not support CustomEvent */ }
                try {
                    window.dispatchEvent(new CustomEvent('nets:homework-failed', {
                        detail: {
                            reason: 'troll-strikes',
                            deduction_pct: deductionPct,
                        },
                    }));
                } catch (e) { /* swallow */ }
            }, 2000);
        }

        // ── Wave J / T4: anti-repetition hint extraction ───────
        // We inspect the last 3 assistant messages currently in the
        // DOM and pull the first 3 words of each. Sent as
        // recent_assistant_phrases on every chat turn — the backend
        // forwards as RECENT_OPENINGS to the prompt.
        function extractRecentOpenings() {
            if (!messages) return [];
            const nodes = messages.querySelectorAll('.nets-tutor-msg.assistant');
            const out = [];
            const start = Math.max(0, nodes.length - 3);
            for (let i = start; i < nodes.length; i++) {
                const txt = (nodes[i].textContent || '').trim();
                if (!txt) continue;
                const words = txt.split(/\s+/).slice(0, 3).join(' ');
                if (words) out.push(words);
            }
            return out;
        }

        // ── Wave J / T4: typing-indicator phrase rotation ─────
        const TYPING_PHRASES = {
            uz: [
                "hisoblayapman...",
                "bir soniya...",
                "miya zo'r ishlayapti 🧠",
                "tayyor bo'lyapman...",
                "yaxshi savol — kutib turing...",
            ],
            ru: [
                "считаю...",
                "секунду...",
                "мозг включился 🧠",
                "готовлю ответ...",
                "хороший вопрос — момент...",
            ],
            en: [
                "computing...",
                "one sec...",
                "brain warming up 🧠",
                "cooking response 🔥",
                "good question — hold on...",
            ],
        };
        function pickTypingPhrase() {
            const pool = TYPING_PHRASES[lang] || TYPING_PHRASES.en;
            // No-consecutive-repeat: filter the last-shown index out of
            // the candidate set, then pick uniformly. Single-element
            // pool degenerates to the same string (impossible here).
            let candidates;
            if (state.lastTypingIndex == null || pool.length <= 1) {
                candidates = pool.map((p, i) => i);
            } else {
                candidates = pool.map((_, i) => i).filter(i => i !== state.lastTypingIndex);
            }
            const pick = candidates[Math.floor(Math.random() * candidates.length)];
            state.lastTypingIndex = pick;
            return pool[pick];
        }

        // ── Open / close panel ──────────────────────────────────
        // The wrapper's `nets-tutor-collapsed` class is the single
        // source of truth — the CSS handles fade + scale transition
        // in both directions. We DON'T toggle the `[hidden]` attribute
        // on the panel at runtime any more (it would short-circuit
        // the close transition); we drop it once on first open so it
        // doesn't keep overriding the visibility cascade afterwards.
        function openPanel() {
            if (state.isOpen) return;
            if (panel.hasAttribute('hidden')) panel.removeAttribute('hidden');
            fab.setAttribute('aria-expanded', 'true');
            state.isOpen = true;
            root.classList.remove('nets-tutor-collapsed');
            // Wait long enough for the transition to start before
            // pulling focus, otherwise mobile Safari snaps the
            // panel into view without animating.
            setTimeout(() => { try { input.focus(); } catch (e) {} }, 80);
        }
        function closePanel() {
            if (!state.isOpen) return;
            fab.setAttribute('aria-expanded', 'false');
            state.isOpen = false;
            root.classList.add('nets-tutor-collapsed');
            // Return focus to the FAB so keyboard users don't lose
            // their place in the document. preventScroll avoids a
            // jarring viewport shift.
            try { fab.focus({ preventScroll: true }); } catch (e) { try { fab.focus(); } catch (_) {} }
        }
        fab.addEventListener('click', openPanel);
        closeBtn.addEventListener('click', closePanel);

        // ── Escape closes the panel (ARIA dialog convention) ────
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && state.isOpen) {
                e.preventDefault();
                closePanel();
            }
        });

        // ── Wave J: Theme — read-only mirror of the navbar toggle ─
        // The runtime player no longer ships its own light/dark
        // toggle. The page-level navbar toggle (frontend/js/theme.js)
        // writes `nets_theme` to localStorage; we apply the saved
        // value at boot and resync via the `storage` event so a
        // toggle in a sibling tab/document is reflected here too.
        const PERSONA_AVATARS = {
            challenger: '⚔️',
            mentor:     '🦉',
            analyst:    '🔬',
        };
        const THEME_KEY = 'nets_theme';

        function applyTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
        }

        function applyStoredTheme() {
            const saved = (function () {
                try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
            }());
            applyTheme(saved === 'dark' ? 'dark' : 'light');
            window.addEventListener('storage', function (e) {
                if (e.key !== THEME_KEY) return;
                applyTheme(e.newValue === 'dark' ? 'dark' : 'light');
            });
        }
        applyStoredTheme();

        // ── Wave J: Avatar update ────────────────────────────────
        function updateAvatar(phase) {
            if (!avatarEl) return;
            if (phase === 'boss') {
                const bs = window.bossState || {};
                const traits = (bs.persona_traits && bs.persona_traits[0]) || 'mentor';
                avatarEl.textContent = PERSONA_AVATARS[traits] || '🦉';
            } else {
                avatarEl.textContent = '🎓';
            }
        }

        // ── Wave J.2 / T2: fine-grained subphase tracking ───────
        // The runtime emits `nets:phase-change` events with detail
        // `{ phase, stage, questionId }` (from setStage at ~line 5748)
        // or `{ phase: 'reflection', failed, ... }` (from the fail
        // overlay at ~line 10810). The 3-cat `phase` covers the
        // tutor-prompt branch selection; `currentSubphase` adds a
        // finer-grained label (memory-sprint, adaptive-quiz, ...) that
        // the backend Wave J.2 prompt rebuild consumes.
        let currentSubphase = 'preview';

        // Map gbState.subGame index → subphase string (matches
        // gbActiveGameOrder() at ~line 7019).
        const GB_SUBGAME_TO_SUBPHASE = {
            0: 'adaptive-quiz',
            1: 'sentence-fill', // legacy mislabel — Why Chain panel still subscribes to 'sentence-fill' tutor context until renamed
            2: 'tile-match',
            3: 'puzzle-lock',
            4: 'mystery-box',
            5: 'tile-match', // ttt has no listed subphase; degrade to nearest game.
            6: 'sentence-fill', // new Sentence Fill panel (gb-panel-sf)
        };

        function deriveSubphase(detail) {
            const phase = detail && detail.phase;
            const stage = (detail && typeof detail.stage === 'number') ? detail.stage : null;
            // Direct hit: reflection dispatch site sets phase='reflection'.
            if (phase === 'reflection') return 'reflection';
            // Boss range: 7..7.7 → final-boss; 7.7+ → reflection (but
            // reflection comes via its own event above).
            if (phase === 'boss') return 'final-boss';
            if (phase === 'practice') {
                // Practice covers: flashcards (2.5–3.5), memory-sprint
                // (4–4.5), reading (4.7), game-breaks (5), real-life (6),
                // consolidation (6.5).
                if (stage === null) return 'preview';
                if (stage >= 4 && stage < 4.7)  return 'memory-sprint';
                if (stage >= 4.7 && stage < 5)  return 'consolidation'; // reading checkpoints share the reading-cp-input pattern
                if (stage >= 5 && stage < 6) {
                    const idx = (typeof gbState !== 'undefined' && gbState) ? gbState.subGame : 0;
                    return GB_SUBGAME_TO_SUBPHASE[idx] || 'adaptive-quiz';
                }
                if (stage >= 6 && stage < 6.5)   return 'real-life';
                if (stage >= 6.5 && stage < 7)   return 'consolidation';
                // 2.5–3.5 (flashcards) and any other practice fallthrough.
                return 'preview';
            }
            return 'preview';
        }

        // ── Phase-change listener ───────────────────────────────
        document.addEventListener('nets:phase-change', (ev) => {
            const detail = (ev && ev.detail) || {};
            const phase = detail.phase || 'preview';
            state.currentPhase = (phase === 'practice' || phase === 'boss') ? phase : 'preview';
            state.currentQuestionId = detail.questionId || null;
            currentSubphase = deriveSubphase(detail);
            syncNetsState();
            updateBadge(state.currentPhase);
            updateAvatar(state.currentPhase);
        });

        // ── Wave J.2 / T2: per-subphase active-input extractor ──
        // Returns the student's CURRENT raw input on the active screen
        // (text typed or option label most-recently picked). Each branch
        // is a thin DOM read; falls back to null when nothing's typed.
        function extractStudentWork(subphase) {
            const get = (sel) => {
                const el = document.querySelector(sel);
                return el ? (el.value != null ? el.value : null) : null;
            };
            const SELECTORS = {
                'real-life': () => {
                    const idx = (typeof stage6State !== 'undefined' && stage6State) ? (stage6State.qIndex != null ? stage6State.qIndex : 0) : 0;
                    // stage6State.qIndex is 0-indexed; DOM ids are rl-q1-input..rl-q6-input.
                    return get('#rl-q' + (idx + 1) + '-input');
                },
                'consolidation': () => {
                    // Reading checkpoint inputs are id=`reading-cp-input-N`.
                    // We grab the first non-empty enabled one (the "active"
                    // checkpoint the student is on).
                    const inputs = document.querySelectorAll('input[id^="reading-cp-input-"]');
                    for (let i = 0; i < inputs.length; i++) {
                        const el = inputs[i];
                        if (!el.disabled && el.value) return el.value;
                    }
                    // Fall back to the first one even if empty/disabled.
                    return inputs.length ? (inputs[0].value || null) : null;
                },
                'adaptive-quiz': () => get('#gb-aq-textarea'),
                'sentence-fill': () => {
                    // Slot 6 (new Sentence Fill panel) takes precedence when active.
                    // Slot 1 (legacy Why Chain) still subscribes to 'sentence-fill'
                    // until the WC subphase rename ships separately.
                    const sfPanel = document.getElementById('gb-panel-sf');
                    if (sfPanel && sfPanel.classList.contains('active')) {
                        const focused = document.activeElement;
                        if (focused && focused.classList && focused.classList.contains('gb-sf-recall-input')) {
                            return focused.value || null;
                        }
                        const filled = sfPanel.querySelectorAll('.gb-sf-blank[data-value]:not([data-value=""])');
                        if (filled.length) {
                            const last = filled[filled.length - 1];
                            return last.getAttribute('data-value') || null;
                        }
                        return null;
                    }
                    return get('#gb-wc-textarea');
                },
                'mystery-box': () => {
                    const v = get('#gb-mb-solve-input');
                    if (v) return v;
                    return (typeof gbState !== 'undefined' && gbState && gbState.mb && gbState.mb.pickedLabel) || null;
                },
                'puzzle-lock': () => get('#gb-pl-input'),
                'tile-match': () => {
                    const tm = (typeof gbState !== 'undefined' && gbState) ? gbState.tm : null;
                    if (!tm) return null;
                    // Runtime uses `selectedLeft = {id, el}` for the currently-
                    // selected left tile (state machine clears it once a pair
                    // attempt resolves, so this only fires while a left is held).
                    if (tm.selectedLeft && tm.selectedLeft.el) {
                        const txt = tm.selectedLeft.el.textContent || '';
                        return txt.trim() ? ('selected: ' + txt.trim().slice(0, 80)) : null;
                    }
                    return null;
                },
                'memory-sprint': () => {
                    // msState only tracks {index, score, isAnimating} —
                    // there is no last-selected-label field. Surface the
                    // current question index instead so the tutor knows
                    // which item the student is on.
                    if (typeof msState === 'undefined' || !msState) return null;
                    return 'ms question index: ' + (msState.index != null ? msState.index : 0);
                },
                'story-mode': () => {
                    // Story mode shares stage6State (it's the intro screen
                    // for real-life). No dedicated input; return null and
                    // let screen_context carry the visible text.
                    return null;
                },
                'final-boss': () => get('#boss-input'),
                'reflection': () => {
                    // Reflection screen has no input field — it's display-
                    // only. Return null so the tutor sees only screen_ctx.
                    return null;
                },
            };
            try {
                const fn = SELECTORS[subphase];
                const v = fn ? fn() : null;
                if (typeof v === 'string' && v.length) return v.slice(0, 2000);
                return null;
            } catch (e) {
                return null;
            }
        }

        // ── Wave J.2 / T2: answer-key DOM scrub ─────────────────
        // Walks the active root, removes nodes flagged as answer-key
        // (data-correct=true, data-expected, .correct, etc.) BEFORE
        // serializing to text — so the tutor never sees the answer it's
        // supposed to be coaching the student toward.
        function sanitizeScreenContext(activeRoot) {
            if (!activeRoot) return '';
            let clone;
            try {
                clone = activeRoot.cloneNode(true);
            } catch (e) {
                return '';
            }
            const SCRUB_SELECTORS = [
                '[data-correct="true"]',
                '[data-expected]',
                '[data-answer]',
                '.correct',
                '.is-correct',
                '.answer-key',
                '.gb-aq-answer',
            ];
            for (let i = 0; i < SCRUB_SELECTORS.length; i++) {
                const matches = clone.querySelectorAll(SCRUB_SELECTORS[i]);
                for (let j = 0; j < matches.length; j++) {
                    const n = matches[j];
                    if (n && n.parentNode) n.parentNode.removeChild(n);
                }
            }
            // Strip any expected/answer attributes that leak through on
            // surviving nodes (e.g., questions that hold the expected
            // answer in a data-* attribute for client-side checking).
            const attrLeaks = clone.querySelectorAll('[data-expected], [data-answer]');
            for (let k = 0; k < attrLeaks.length; k++) {
                attrLeaks[k].removeAttribute('data-expected');
                attrLeaks[k].removeAttribute('data-answer');
            }
            const raw = (clone.innerText || clone.textContent || '');
            return raw.replace(/\s+/g, ' ').trim().slice(0, 2000);
        }

        // ── API ─────────────────────────────────────────────────
        function apiAvailable() {
            return !!(window.NETS_AI && typeof window.NETS_AI.tutorChat === 'function'
                      && window.NETS_AI.isAvailable && window.NETS_AI.isAvailable()
                      && state.hwId);
        }

        async function sendMessage(text) {
            if (state.isSending || !text) return;
            if (state.homeworkFailed) return;  // Wave J / T4: hard lock
            state.isSending = true;
            sendBtn.disabled = true;
            appendMessage('user', text);
            const typing = appendTyping();
            try {
                if (!apiAvailable()) {
                    removeTyping();
                    appendMessage('error', L.offline);
                    return;
                }
                // Only count this turn against the cap once we know the API
                // is reachable. Pre-fix code incremented before the offline
                // guard, burning 1/SESSION_CAP for every failed offline ping.
                state.messageCount += 1;
                const activeScreen = document.querySelector('.screen.active');
                // Wave J.2 / T2: sanitize answer-key markers BEFORE the
                // text leaves the browser. sanitizeScreenContext clones
                // the active root, drops [data-correct=true], .correct,
                // .answer-key, etc., then serializes to plain text.
                const screenContext = sanitizeScreenContext(activeScreen);
                // Wave J.2 / T2: per-subphase active-input read. The
                // backend uses this as `student_work_text` so the tutor
                // sees what the student actually typed/picked, not just
                // the surrounding chrome.
                const studentWork = extractStudentWork(currentSubphase);
                // Wave J / T4: collect last 3 assistant openings BEFORE
                // we inject the new turn so we get the previous tone, not
                // the one we're about to send.
                const recentOpenings = extractRecentOpenings();
                const res = await window.NETS_AI.tutorChat({
                    session_id: state.sessionId,
                    hw_id: state.hwId,
                    phase: state.currentPhase,
                    question_id: state.currentQuestionId || undefined,
                    message: text,
                    screen_context: screenContext || undefined,
                    student_work_text: studentWork || undefined,
                    subphase: currentSubphase || undefined,
                    recent_assistant_phrases: recentOpenings.length ? recentOpenings : undefined,
                });
                removeTyping();
                // Wave J / T4: warning state machine — handle BEFORE any
                // success/error branching so the fail short-circuit + chip
                // updates fire even when response text is the canned
                // server-generated fail message.
                if (res && typeof res === 'object' && !res._error && !res._cap) {
                    if (res.homework_failed) {
                        // Render the fail line (server gives a localized one)
                        // before locking — kids see *why*, not just an overlay.
                        if (res.response) appendMessage('assistant', res.response);
                        showFailOverlay(res.cumulative_deduction_pct);
                        return;
                    }
                    if (typeof res.warning_level === 'number') {
                        updateWarningChip(res.warning_level, res.cumulative_deduction_pct);
                    }
                    if (res.is_big_warning) {
                        showBigWarningBanner(res.cumulative_deduction_pct);
                    }
                }
                if (res && res._cap) {
                    state.messageCount = SESSION_CAP;
                    appendMessage('error', L.cap);
                } else if (res && res._error) {
                    appendMessage('error', res.message || L.error);
                } else if (res && res.response) {
                    appendMessage('assistant', res.response);
                    state.messageCount += 1;
                } else {
                    appendMessage('error', L.error);
                }
            } catch (e) {
                removeTyping();
                appendMessage('error', L.error);
            } finally {
                state.isSending = false;
                applyCap();
            }
        }

        inputForm.addEventListener('submit', (ev) => {
            ev.preventDefault();
            const text = (input.value || '').trim();
            if (!text) return;
            input.value = '';
            sendMessage(text);
        });

        // Submit on Enter, newline on Shift+Enter.
        input.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter' && !ev.shiftKey) {
                ev.preventDefault();
                inputForm.requestSubmit ? inputForm.requestSubmit() : inputForm.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        });

        // ── History restore on load ─────────────────────────────
        async function restoreHistory() {
            if (!apiAvailable() || !window.NETS_AI.tutorHistory) return;
            try {
                const res = await window.NETS_AI.tutorHistory({
                    session_id: state.sessionId,
                    hw_id: state.hwId,
                });
                const turns = (res && res.turns) || [];
                let count = 0;
                for (const t of turns) {
                    if (!t || !t.role || !t.content) continue;
                    if (t.role === 'system') continue;
                    appendMessage(t.role === 'user' ? 'user' : 'assistant', t.content);
                    count += 1;
                }
                state.messageCount = count;
                applyCap();
            } catch (e) { /* swallow — history is best-effort */ }
        }

        // ── Wave F4: Stuck? Ask tutor CTA ──────────────────────
        const CTA_LABELS = {
            uz: 'Tushunmadingmi? Tyutorga ayt',
            en: 'Stuck? Ask the tutor →',
            ru: 'Не понял? Спроси у тьютора →',
        };
        const CTA_PREFILL = {
            uz: "Tushunmadingmi? '",
            en: "Stuck on: '",
            ru: "Не понял: '",
        };
        const ctaBtn = document.getElementById('nets-tutor-cta');
        const ctaLabel = ctaBtn && ctaBtn.querySelector('.nets-tutor-cta-label');

        if (ctaBtn && ctaLabel) {
            ctaLabel.textContent = CTA_LABELS[lang] || CTA_LABELS.uz;

            document.addEventListener('nets:result', function (ev) {
                const detail = (ev && ev.detail) || {};
                // FE-7: dispatcher migrated to 'legacy-tutor' (still uses
                // guidance_type for verdict). Only wire CTA for practice
                // phase, not boss phase.
                if (detail.kind !== 'legacy-tutor') return;
                if (state.currentPhase === 'boss') return;
                const result = detail.result || {};
                const aiCorrect = (result.guidance_type || '').toLowerCase() === 'validation'
                               || (result.guidance_type || '').toLowerCase() === 'correct';
                if (aiCorrect) {
                    ctaBtn.hidden = true;
                    return;
                }
                // Wrong answer — surface the CTA.
                // Resolve active question id + text from RL_SCENARIO.
                const rlScenario = (typeof RL_SCENARIO !== 'undefined') ? RL_SCENARIO : null;
                const rlState   = (typeof stage6State !== 'undefined') ? stage6State : null;
                const idx       = rlState ? rlState.qIndex : null;
                const q         = (rlScenario && idx !== null) ? (rlScenario.questions || [])[idx] : null;
                state.pendingCtaQuestion = {
                    id:   (q && (q.id || ('rl-' + (idx + 1)))) || state.currentQuestionId,
                    text: (q && (q.prompt || q.label)) || '',
                };
                // Append CTA into the active feedback div if possible.
                if (idx !== null) {
                    const fbEl = document.getElementById('rl-q' + (idx + 1) + '-fb');
                    if (fbEl && !fbEl.contains(ctaBtn)) fbEl.appendChild(ctaBtn);
                }
                ctaBtn.hidden = false;
            });

            ctaBtn.addEventListener('click', function () {
                const pending = state.pendingCtaQuestion || {};
                if (pending.id)   state.currentQuestionId = pending.id;
                syncNetsState();
                openPanel();
                updateBadge(state.currentPhase);
                const prefill = (CTA_PREFILL[lang] || CTA_PREFILL.uz)
                    + (pending.text ? pending.text.replace(/<[^>]+>/g, '') : '') + "'";
                input.value = prefill;
                setTimeout(function () { try { input.focus(); } catch (e) {} }, 60);
                ctaBtn.hidden = true;
            });
        }

        // Kick off after a tick so runtime.js has registered.
        setTimeout(restoreHistory, 0);
    })();
