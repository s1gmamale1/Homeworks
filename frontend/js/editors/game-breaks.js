// frontend/js/editors/game-breaks.js
// Game Breaks coordinator: routes each production game to its own editor module.
// Requires:
// - /js/editors/games/adaptive-quiz.js
// - /js/editors/games/why-chain.js     (legacy "Why Chain" — gb_why_chain)
// - /js/editors/games/sentence-fill.js (real cloze Sentence Fill — gb_sentence_fill)
// - /js/editors/games/tile-match.js
// - /js/editors/games/puzzle-lock.js
// - /js/editors/games/mystery-box.js
// - /js/editors/games/ttt.js

(function () {
  "use strict";

  window.Editors = window.Editors || {};
  window.GameBreakEditors = window.GameBreakEditors || {};

  const GAME_TABS = [
    {
      id: "adaptive_quiz",
      label: "Adaptive Quiz",
      icon: "🎯",
      editor: "adaptiveQuiz",
      description: "Apply-level short-answer game. Uses q, tags, tier, ans[], capture.",
    },
    {
      id: "why_chain",
      label: "Why Chain",
      icon: "🧩",
      editor: "whyChain",
      description: "Legacy Why-Chain game mapped to gb_why_chain: q, inv, reprompts[], expects[].",
    },
    {
      id: "sentence_fill",
      label: "Sentence Fill",
      icon: "📝",
      editor: "sentenceFill",
      description: "Cloze passage with multi-blank fill. Modes: word_bank (G2-7) | free_recall (G8+). Maps to gb_sentence_fill.",
    },
    {
      id: "memory_match",
      label: "Tile Match",
      icon: "🧠",
      editor: "tileMatch",
      description: "Concept-definition matching game. Uses [left, right] pairs.",
    },
    {
      id: "puzzle_lock",
      label: "Puzzle Lock",
      icon: "🧩",
      editor: "puzzleLock",
      description: "Knowledge-gated sliding-tile puzzle. Each tile has content + question + answer. 8 tiles → 3×3, 15 → 4×4.",
    },
    {
      id: "mystery_box",
      label: "Mystery Box",
      icon: "📦",
      editor: "mysteryBox",
      description: "Interleaved category recognition. Each box has category + problem + answer. Student identifies category first, then solves.",
    },
    {
      id: "ttt",
      label: "Tic Tac Toe",
      icon: "⭕",
      editor: "ttt",
      description: "Knowledge-gated 3×3 grid vs minimax AI. Each item is a MC question (q + correct + 3 distractors) consumed per cell tap. 3 games per session.",
    },
  ];

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value ?? null));
  }

  function normalizeAdaptiveQuiz(items) {
    return Array.isArray(items)
      ? items.map((item) => ({
          q: item?.q || "",
          tags: item?.tags || "[Bloom: L1 | PISA: L1]",
          tier: ["EASY", "MEDIUM", "HARD"].includes(item?.tier) ? item.tier : "EASY",
          ans: Array.isArray(item?.ans) && item.ans.length ? item.ans : [""],
          capture: Boolean(item?.capture),
        }))
      : [];
  }

  function normalizeWhyChain(items) {
    // Legacy why-chain shape (data key: gb_why_chain).
    return Array.isArray(items)
      ? items.map((item) => ({
          q: item?.q || "",
          inv: item?.inv || "",
          reprompts: Array.isArray(item?.reprompts) && item.reprompts.length ? item.reprompts : [""],
        }))
      : [];
  }

  function normalizeSentenceFill(items) {
    // Real Sentence Fill cloze shape (data key: gb_sentence_fill). Schema: §1
    // of SENTENCE_FILL_BACKEND_PLAN.md. Only normalises shape — hard validation
    // (blank count, distractor count, length matching) lives in the editor's
    // save-time validator and on the server in Pydantic.
    return Array.isArray(items)
      ? items.map((item) => {
          const mode = item?.mode === "free_recall" ? "free_recall" : "word_bank";
          const tier = item?.tier === "premium" ? "premium" : "basic";
          const passage = typeof item?.passage === "string" ? item.passage : "";
          const answers = Array.isArray(item?.answers)
            ? item.answers.map((a) => String(a ?? ""))
            : [];
          const wordBank = Array.isArray(item?.word_bank)
            ? item.word_bank.map((w) => String(w ?? ""))
            : (mode === "word_bank" ? [] : null);
          const explanations = Array.isArray(item?.explanations)
            ? item.explanations.map((e) => (e == null ? null : String(e)))
            : null;
          const blankIcons = Array.isArray(item?.blank_icons)
            ? item.blank_icons.map((b) => (b == null ? null : String(b)))
            : null;
          const colorHints =
            item?.color_hints && typeof item.color_hints === "object" && !Array.isArray(item.color_hints)
              ? Object.fromEntries(
                  Object.entries(item.color_hints).map(([k, v]) => [String(k), String(v ?? "")])
                )
              : null;
          return {
            id: typeof item?.id === "string" && item.id ? item.id : "",
            mode,
            passage,
            answers,
            word_bank: wordBank,
            explanations,
            tags: typeof item?.tags === "string" ? item.tags : "",
            pisa_level: ["L1", "L2", "L3", "L4", "L5"].includes(item?.pisa_level)
              ? item.pisa_level
              : "",
            difficulty: ["easy", "medium", "hard"].includes(item?.difficulty)
              ? item.difficulty
              : "",
            subject_hint: typeof item?.subject_hint === "string" ? item.subject_hint : "",
            color_hints: colorHints,
            blank_icons: blankIcons,
            tier,
          };
        })
      : [];
  }

  function normalizeTileMatch(items) {
    return Array.isArray(items)
      ? items.map((pair) => [
          Array.isArray(pair) ? pair[0] || "" : "",
          Array.isArray(pair) ? pair[1] || "" : "",
        ])
      : [];
  }

  function normalizePuzzleLock(items) {
    return Array.isArray(items)
      ? items.map((tile) => ({
          content: typeof tile?.content === "string" ? tile.content : "",
          q: typeof tile?.q === "string" ? tile.q : "",
          a: typeof tile?.a === "string" ? tile.a : "",
        }))
      : [];
  }

  function normalizeMysteryBox(items) {
    return Array.isArray(items)
      ? items.map((item) => ({
          category: typeof item?.category === "string" ? item.category : "",
          q: typeof item?.q === "string" ? item.q : "",
          a: typeof item?.a === "string" ? item.a : "",
        }))
      : [];
  }

  function normalizeTTT(items) {
    return Array.isArray(items)
      ? items.map((item) => {
          const distractors = Array.isArray(item?.distractors) ? item.distractors.slice(0, 3) : [];
          while (distractors.length < 3) distractors.push("");
          return {
            q: typeof item?.q === "string" ? item.q : "",
            correct: typeof item?.correct === "string" ? item.correct : "",
            distractors: distractors.map((d) => (typeof d === "string" ? d : "")),
          };
        })
      : [];
  }

  function normalize(data) {
    const safe = data && typeof data === "object" ? data : {};

    // Accept both unprefixed and gb_-prefixed keys on input (defensive).
    // Emit unprefixed — builder.js maps these back to CONTRACTS' gb_* keys on save.
    return {
      adaptive_quiz: normalizeAdaptiveQuiz(safe.adaptive_quiz ?? safe.gb_adaptive_quiz),
      why_chain: normalizeWhyChain(safe.why_chain ?? safe.gb_why_chain),
      sentence_fill: normalizeSentenceFill(safe.sentence_fill ?? safe.gb_sentence_fill),
      memory_match: normalizeTileMatch(safe.memory_match ?? safe.gb_memory_match),
      puzzle_lock: normalizePuzzleLock(safe.puzzle_lock ?? safe.gb_puzzle_lock),
      mystery_box: normalizeMysteryBox(safe.mystery_box ?? safe.gb_mystery_box),
      ttt: normalizeTTT(safe.ttt ?? safe.gb_ttt),
    };
  }

  function emit(state, onChange) {
    onChange(clone(state));
  }

  function getCount(state, tabId) {
    const value = state[tabId];
    return Array.isArray(value) ? value.length : 0;
  }

  function getTabData(state, tabId) {
    if (tabId === "adaptive_quiz") return state.adaptive_quiz;
    if (tabId === "why_chain") return state.why_chain;
    if (tabId === "sentence_fill") return state.sentence_fill;
    if (tabId === "memory_match") return state.memory_match;
    if (tabId === "puzzle_lock") return state.puzzle_lock;
    if (tabId === "mystery_box") return state.mystery_box;
    if (tabId === "ttt") return state.ttt;
    return [];
  }

  function setTabData(state, tabId, value) {
    if (tabId === "adaptive_quiz") state.adaptive_quiz = normalizeAdaptiveQuiz(value);
    if (tabId === "why_chain") state.why_chain = normalizeWhyChain(value);
    if (tabId === "sentence_fill") state.sentence_fill = normalizeSentenceFill(value);
    if (tabId === "memory_match") state.memory_match = normalizeTileMatch(value);
    if (tabId === "puzzle_lock") state.puzzle_lock = normalizePuzzleLock(value);
    if (tabId === "mystery_box") state.mystery_box = normalizeMysteryBox(value);
    if (tabId === "ttt") state.ttt = normalizeTTT(value);
  }

  function renderTabs(state, activeTab) {
    return GAME_TABS.map(
      (tab) => `
        <button class="phase-btn game-tab-btn ${tab.id === activeTab ? "active" : ""}" type="button" data-game-tab="${tab.id}">
          <span class="phase-icon" aria-hidden="true">${escapeHtml(tab.icon)}</span>
          <span>${escapeHtml(tab.label)}</span>
          <span class="mini-count">${getCount(state, tab.id)}</span>
        </button>
      `
    ).join("");
  }

  function renderMissingEditor(container, tab) {
    container.innerHTML = `
      <div class="empty-state glass-card inline-empty">
        <div class="empty-orb" aria-hidden="true">🧯</div>
        <h3>Missing game editor</h3>
        <p>${escapeHtml(tab.label)} needs <code>${escapeHtml(tab.editor)}</code> registered in window.GameBreakEditors.</p>
      </div>
    `;
  }

  function render(container, data, onChange) {
    const state = normalize(data);
    let activeTab = GAME_TABS[0].id;

    function repaintShell() {
      const active = GAME_TABS.find((tab) => tab.id === activeTab) || GAME_TABS[0];

      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header">
              <div>
                <p class="eyebrow">Game Breaks</p>
                <h3>Production games only</h3>
              </div>
            </div>
            <p class="muted-text">
              Split by production game: Adaptive Quiz, Why Chain, Sentence Fill, Tile Match, Puzzle Lock, Mystery Box, and Tic Tac Toe. Each game owns its own JS editor.
            </p>
          </section>

          <section class="editor-card game-break-layout">
            <aside class="game-tabs" aria-label="Game break tabs">
              ${renderTabs(state, activeTab)}
            </aside>

            <div class="game-editor-panel">
              <div class="editor-header">
                <div>
                  <p class="eyebrow">${escapeHtml(active.label)}</p>
                  <h3>${escapeHtml(active.description)}</h3>
                </div>
              </div>
              <div id="game-editor-root"></div>
            </div>
          </section>
        </div>
      `;

      renderActiveGame();
    }

    function renderActiveGame() {
      const active = GAME_TABS.find((tab) => tab.id === activeTab) || GAME_TABS[0];
      const root = container.querySelector("#game-editor-root");
      const editor = window.GameBreakEditors?.[active.editor];

      if (!root) return;

      if (!editor || typeof editor.render !== "function") {
        renderMissingEditor(root, active);
        return;
      }

      editor.render(root, getTabData(state, active.id), (nextData) => {
        setTabData(state, active.id, nextData);
        emit(state, onChange);
        const count = container.querySelector(`[data-game-tab="${active.id}"] .mini-count`);
        if (count) count.textContent = String(getCount(state, active.id));
      });
    }

    container.onclick = (event) => {
      const tabButton = event.target.closest("[data-game-tab]");
      if (!tabButton) return;

      activeTab = tabButton.dataset.gameTab;
      repaintShell();
    };

    repaintShell();
  }

  window.Editors.gameBreaks = { render };
})();
