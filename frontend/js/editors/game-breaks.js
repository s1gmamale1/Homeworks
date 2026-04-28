// frontend/js/editors/game-breaks.js
// Game Breaks coordinator: routes each production game to its own editor module.
// Requires:
// - /js/editors/games/adaptive-quiz.js
// - /js/editors/games/sentence-fill.js
// - /js/editors/games/tile-match.js
// - /js/editors/games/puzzle-lock.js

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
      label: "Sentence Fill",
      icon: "🧩",
      editor: "sentenceFill",
      description: "Production cloze/fill game mapped to gb_why_chain: q, inv, reprompts[].",
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

  function normalizeSentenceFill(items) {
    return Array.isArray(items)
      ? items.map((item) => ({
          q: item?.q || "",
          inv: item?.inv || "",
          reprompts: Array.isArray(item?.reprompts) && item.reprompts.length ? item.reprompts : [""],
        }))
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

  function normalize(data) {
    const safe = data && typeof data === "object" ? data : {};

    // Accept both unprefixed and gb_-prefixed keys on input (defensive).
    // Emit unprefixed — builder.js maps these back to CONTRACTS' gb_* keys on save.
    return {
      adaptive_quiz: normalizeAdaptiveQuiz(safe.adaptive_quiz ?? safe.gb_adaptive_quiz),
      why_chain: normalizeSentenceFill(safe.why_chain ?? safe.gb_why_chain),
      memory_match: normalizeTileMatch(safe.memory_match ?? safe.gb_memory_match),
      puzzle_lock: normalizePuzzleLock(safe.puzzle_lock ?? safe.gb_puzzle_lock),
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
    if (tabId === "memory_match") return state.memory_match;
    if (tabId === "puzzle_lock") return state.puzzle_lock;
    return [];
  }

  function setTabData(state, tabId, value) {
    if (tabId === "adaptive_quiz") state.adaptive_quiz = normalizeAdaptiveQuiz(value);
    if (tabId === "why_chain") state.why_chain = normalizeSentenceFill(value);
    if (tabId === "memory_match") state.memory_match = normalizeTileMatch(value);
    if (tabId === "puzzle_lock") state.puzzle_lock = normalizePuzzleLock(value);
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
              Split by production game: Adaptive Quiz, Sentence Fill, Tile Match, and Puzzle Lock. Each game owns its own JS editor.
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
