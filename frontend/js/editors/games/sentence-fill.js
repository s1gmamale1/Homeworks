// frontend/js/editors/games/sentence-fill.js
// Sentence Fill (cloze) editor for production game break.
// Contract storage: content_json.gb_sentence_fill (NEW data key — distinct
// from the legacy gb_why_chain game, which lives at why-chain.js).
//
// Item shape (see SENTENCE_FILL_BACKEND_PLAN.md §1):
//   { id, mode, passage, answers[], word_bank[]?, explanations[]?,
//     tags?, pisa_level?, difficulty?, subject_hint?,
//     color_hints?, blank_icons?, tier }
//
// Mounting:
//   render(container, data, onChange, context)
//     where context = { grade, subject, tier } (defaults below if omitted).

(function () {
  "use strict";

  window.GameBreakEditors = window.GameBreakEditors || {};

  // ---------------------------------------------------------------------------
  // Helpers — grade-band defaults. Mirror _sentence-fill-helpers.js so the
  // editor works even if the helpers file isn't loaded first; the helpers file
  // is the canonical source for the regression test.
  // ---------------------------------------------------------------------------

  function defaultModeForGrade(grade) {
    return grade >= 8 ? "free_recall" : "word_bank";
  }

  function recommendedDistractorCount(grade, blanksCount) {
    if (grade <= 4) return blanksCount * 2;
    if (grade <= 7) return blanksCount * 3;
    return 0;
  }

  function detectBlanks(passage) {
    if (typeof passage !== "string") return 0;
    return (passage.match(/___/g) || []).length;
  }

  // ---------------------------------------------------------------------------
  // String / state helpers
  // ---------------------------------------------------------------------------

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value ?? []));
  }

  let _idCounter = 0;
  function nextId() {
    _idCounter += 1;
    return `sf-${String(Date.now()).slice(-6)}${_idCounter}`;
  }

  function defaultContext() {
    // free_recall is the safe default when grade is unknown.
    return { grade: 8, subject: "language", tier: "basic" };
  }

  function makeItem(context) {
    const ctx = context || defaultContext();
    const mode = defaultModeForGrade(ctx.grade);
    return {
      id: nextId(),
      mode,
      passage: "",
      answers: [],
      word_bank: mode === "word_bank" ? [] : null,
      explanations: null,
      tags: "",
      pisa_level: "",
      difficulty: "",
      subject_hint: ctx.subject || "",
      color_hints: null,
      blank_icons: null,
      tier: ctx.tier === "premium" ? "premium" : "basic",
    };
  }

  function normalize(items, context) {
    if (!Array.isArray(items)) return [];
    return items.map((raw) => {
      const ctx = context || defaultContext();
      const mode =
        raw?.mode === "free_recall" ? "free_recall" :
        raw?.mode === "word_bank"   ? "word_bank"   :
        defaultModeForGrade(ctx.grade);
      const tier = raw?.tier === "premium" ? "premium" : "basic";
      const passage = typeof raw?.passage === "string" ? raw.passage : "";
      const blanksCount = detectBlanks(passage);

      // Answers — pad / truncate to match blanks count.
      const rawAnswers = Array.isArray(raw?.answers)
        ? raw.answers.map((a) => String(a ?? ""))
        : [];
      const answers = rawAnswers.slice(0, blanksCount);
      while (answers.length < blanksCount) answers.push("");

      // Word bank — only relevant in word_bank mode.
      let wordBank = null;
      if (mode === "word_bank") {
        wordBank = Array.isArray(raw?.word_bank)
          ? raw.word_bank.map((w) => String(w ?? "")).filter((w) => w.length > 0)
          : [];
      }

      // Explanations — match answers length when present.
      let explanations = null;
      if (Array.isArray(raw?.explanations)) {
        explanations = raw.explanations.slice(0, blanksCount).map((e) =>
          e == null || e === "" ? null : String(e)
        );
        while (explanations.length < blanksCount) explanations.push(null);
      }

      // Color hints — { word -> color } dict.
      let colorHints = null;
      if (raw?.color_hints && typeof raw.color_hints === "object" && !Array.isArray(raw.color_hints)) {
        colorHints = {};
        for (const [k, v] of Object.entries(raw.color_hints)) {
          colorHints[String(k)] = String(v ?? "");
        }
      }

      // Blank icons — match answers length when present.
      let blankIcons = null;
      if (Array.isArray(raw?.blank_icons)) {
        blankIcons = raw.blank_icons.slice(0, blanksCount).map((b) =>
          b == null || b === "" ? null : String(b)
        );
        while (blankIcons.length < blanksCount) blankIcons.push(null);
      }

      return {
        id: typeof raw?.id === "string" && raw.id ? raw.id : nextId(),
        mode,
        passage,
        answers,
        word_bank: wordBank,
        explanations,
        tags: typeof raw?.tags === "string" ? raw.tags : "",
        pisa_level: ["L1", "L2", "L3", "L4", "L5"].includes(raw?.pisa_level) ? raw.pisa_level : "",
        difficulty: ["easy", "medium", "hard"].includes(raw?.difficulty) ? raw.difficulty : "",
        subject_hint: typeof raw?.subject_hint === "string" ? raw.subject_hint : (ctx.subject || ""),
        color_hints: colorHints,
        blank_icons: blankIcons,
        tier,
      };
    });
  }

  // ---------------------------------------------------------------------------
  // Validation — per item. Returns { errors, warnings } string arrays.
  // ---------------------------------------------------------------------------

  function validateItem(item, context) {
    const errors = [];
    const warnings = [];
    const blanks = detectBlanks(item.passage);
    const ctx = context || defaultContext();

    // Hard errors.
    if (blanks === 0) {
      errors.push("Passage must contain at least one ___ blank.");
    } else if (blanks > 6) {
      errors.push(`Passage has ${blanks} blanks; spec allows 1–6.`);
    }
    const filledAnswers = (item.answers || []).filter((a) => a && a.trim().length > 0);
    if (blanks > 0 && filledAnswers.length !== blanks) {
      errors.push(`Answer count (${filledAnswers.length}) must match blank count (${blanks}).`);
    }
    if (item.mode === "word_bank") {
      const bank = item.word_bank || [];
      if (!bank.length) {
        errors.push("Word bank required when mode is Word Bank.");
      } else {
        const bankSet = new Set(bank.map((w) => w.trim().toLowerCase()));
        const missing = filledAnswers.filter(
          (a) => !bankSet.has(a.trim().toLowerCase())
        );
        if (missing.length) {
          errors.push(`Word bank must include every answer (missing: ${missing.join(", ")}).`);
        }
        if (bank.length <= filledAnswers.length) {
          errors.push("Word bank must include at least one distractor.");
        }
      }
    }
    if (Array.isArray(item.explanations)) {
      const filledExpl = item.explanations.filter((e) => e != null);
      if (filledExpl.length > 0 && item.explanations.length !== filledAnswers.length) {
        errors.push(
          `Explanations length (${item.explanations.length}) must match answers (${filledAnswers.length}).`
        );
      }
    }
    if (Array.isArray(item.blank_icons)) {
      const filledIcons = item.blank_icons.filter((b) => b != null);
      if (filledIcons.length > 0 && item.blank_icons.length !== filledAnswers.length) {
        errors.push(
          `Blank icons length (${item.blank_icons.length}) must match answers (${filledAnswers.length}).`
        );
      }
    }

    // Soft warnings.
    const recommendedMode = defaultModeForGrade(ctx.grade);
    if (item.mode !== recommendedMode) {
      warnings.push(
        `Recommended mode for Grade ${ctx.grade} is ${recommendedMode === "word_bank" ? "Word Bank" : "Free Recall"}.`
      );
    }
    if (item.mode === "word_bank") {
      const recommendedBank = filledAnswers.length + recommendedDistractorCount(ctx.grade, filledAnswers.length);
      if ((item.word_bank || []).length < recommendedBank && filledAnswers.length > 0) {
        warnings.push(
          `For Grade ${ctx.grade}, ${recommendedDistractorCount(ctx.grade, filledAnswers.length)} extra distractors are recommended.`
        );
      }
    }
    // Soft: blank at sentence start/end (first/last word "protected").
    if (item.passage) {
      // crude heuristic: ___ is the first non-space token, OR follows a sentence-ender,
      // OR is the last non-space token, OR sits right before a sentence-ender.
      if (
        /(^\s*___)|((?:^|\.\s+|\!\s+|\?\s+)___)|(___\s*$)|(___\s*[.!?])/.test(item.passage)
      ) {
        warnings.push(
          "Avoid placing ___ at the very start or end of a sentence — first/last word should be visible."
        );
      }
    }

    return { errors, warnings };
  }

  function emit(state, onChange) {
    onChange(clone(state));
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  function renderAnswerInputs(item, blanks, index) {
    const rows = [];
    for (let i = 0; i < blanks; i += 1) {
      const value = (item.answers && item.answers[i]) || "";
      rows.push(`
        <label class="field" data-blank-index="${i}">
          <span>Blank ${i + 1}</span>
          <input class="js-answer" type="text" value="${escapeHtml(value)}"
            placeholder="Correct word for blank ${i + 1}" />
        </label>
      `);
    }
    return rows.join("");
  }

  function renderWordBankChips(item) {
    const bank = item.word_bank || [];
    if (!bank.length) return "";
    return bank
      .map(
        (w, i) => `
        <span class="sf-chip" data-chip-index="${i}">
          ${escapeHtml(w)}
          <button class="js-remove-chip icon-btn" type="button" title="Remove">×</button>
        </span>`
      )
      .join("");
  }

  function renderExplanations(item, blanks, expanded) {
    if (!expanded) return "";
    const expls = Array.isArray(item.explanations) ? item.explanations : new Array(blanks).fill(null);
    const rows = [];
    for (let i = 0; i < blanks; i += 1) {
      const v = expls[i] || "";
      rows.push(`
        <label class="field" data-explanation-index="${i}">
          <span>Why blank ${i + 1} is the right word (revealed on lock)</span>
          <textarea class="js-explanation" rows="2" placeholder="Optional — shown after the blank locks">${escapeHtml(v)}</textarea>
        </label>
      `);
    }
    return rows.join("");
  }

  function renderValidation(item, context) {
    const { errors, warnings } = validateItem(item, context);
    if (!errors.length && !warnings.length) return "";
    const errEl = errors.length
      ? `<ul class="sf-validation sf-validation-error">${errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul>`
      : "";
    const warnEl = warnings.length
      ? `<ul class="sf-validation sf-validation-warning">${warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul>`
      : "";
    return errEl + warnEl;
  }

  function render(container, data, onChange, context) {
    const ctx = context && typeof context === "object" ? { ...defaultContext(), ...context } : defaultContext();
    const state = normalize(data, ctx);
    // Track per-item UI flags (collapse/expand groups).
    const ui = state.map(() => ({ explanationsOpen: false, metaOpen: false }));

    function repaint() {
      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header compact-header">
              <div>
                <p class="eyebrow">Sentence Fill</p>
                <h3>${state.length} cloze passage${state.length === 1 ? "" : "s"}</h3>
              </div>
              <button class="btn btn-primary js-add-item" type="button">Add cloze passage</button>
            </div>
            <p class="muted-text">
              Cloze passages with multi-blank fill. Use <code>___</code> (3 underscores) for each blank.
              Mode default: ${defaultModeForGrade(ctx.grade) === "word_bank" ? "Word Bank" : "Free Recall"} (Grade ${ctx.grade}).
            </p>
          </section>

          ${
            state.length
              ? state
                  .map((item, index) => {
                    const blanks = detectBlanks(item.passage);
                    const recommendedMode = defaultModeForGrade(ctx.grade);
                    const showWordBank = item.mode === "word_bank";
                    const showApplyAll = index === 0 && state.length > 1;
                    const isPremium = item.tier === "premium";
                    return `
                      <section class="editor-card nested-card sf-item" data-index="${index}">
                        <div class="editor-header compact-header">
                          <div>
                            <p class="eyebrow">Cloze ${index + 1}</p>
                            <h3>${escapeHtml(item.id || `sf-${index + 1}`)}</h3>
                          </div>
                          <button class="btn btn-danger js-remove-item" type="button">Remove</button>
                        </div>

                        <div class="editor-grid">
                          <label class="field">
                            <span>Mode</span>
                            <select class="js-field" data-key="mode">
                              <option value="word_bank" ${item.mode === "word_bank" ? "selected" : ""}>Word Bank</option>
                              <option value="free_recall" ${item.mode === "free_recall" ? "selected" : ""}>Free Recall</option>
                            </select>
                            ${
                              item.mode !== recommendedMode
                                ? `<small class="sf-hint sf-hint-warning">Recommended for Grade ${ctx.grade}: ${recommendedMode === "word_bank" ? "Word Bank" : "Free Recall"}</small>`
                                : ""
                            }
                          </label>
                          ${
                            showApplyAll
                              ? `<button class="btn btn-ghost js-apply-mode-all" type="button">Apply mode to all SF items</button>`
                              : ""
                          }
                        </div>

                        <div class="editor-grid">
                          <label class="field full-span">
                            <span>Passage</span>
                            <textarea class="js-field" data-key="passage" rows="4"
                              placeholder="Type your passage. Use ___ for blanks.">${escapeHtml(item.passage)}</textarea>
                            <small class="sf-hint">${blanks} blank${blanks === 1 ? "" : "s"} detected</small>
                          </label>
                        </div>

                        ${
                          blanks > 0
                            ? `<div class="editor-grid sf-answers">
                                ${renderAnswerInputs(item, blanks, index)}
                              </div>`
                            : ""
                        }

                        ${
                          showWordBank
                            ? `<div class="editor-card nested-card sf-word-bank">
                                <div class="editor-header compact-header">
                                  <div>
                                    <p class="eyebrow">Word bank</p>
                                    <h3>${(item.word_bank || []).length} word${(item.word_bank || []).length === 1 ? "" : "s"}</h3>
                                  </div>
                                  <button class="btn btn-ghost js-pull-answers" type="button" title="Pre-populate with current answers">Pull answers</button>
                                </div>
                                <div class="sf-chip-row">
                                  ${renderWordBankChips(item)}
                                </div>
                                <label class="field">
                                  <span>Add distractor (Enter or comma to add)</span>
                                  <input class="js-add-chip" type="text" placeholder="distractor word" />
                                </label>
                              </div>`
                            : ""
                        }

                        <div class="editor-card nested-card sf-explanations">
                          <div class="editor-header compact-header">
                            <div>
                              <p class="eyebrow">Per-blank explanations (optional)</p>
                              <h3>${ui[index].explanationsOpen ? "Editing" : "Collapsed"}</h3>
                            </div>
                            <button class="btn btn-ghost js-toggle-explanations" type="button">
                              ${ui[index].explanationsOpen ? "Hide" : "Show"}
                            </button>
                          </div>
                          ${ui[index].explanationsOpen ? `<div class="editor-list">${renderExplanations(item, blanks, true)}</div>` : ""}
                        </div>

                        <div class="editor-card nested-card sf-meta">
                          <div class="editor-header compact-header">
                            <div>
                              <p class="eyebrow">Optional metadata</p>
                              <h3>${ui[index].metaOpen ? "Editing" : "Collapsed"}</h3>
                            </div>
                            <button class="btn btn-ghost js-toggle-meta" type="button">
                              ${ui[index].metaOpen ? "Hide" : "Show"}
                            </button>
                          </div>
                          ${
                            ui[index].metaOpen
                              ? `<div class="editor-grid">
                                  <label class="field">
                                    <span>PISA level</span>
                                    <select class="js-field" data-key="pisa_level">
                                      <option value="" ${!item.pisa_level ? "selected" : ""}>—</option>
                                      ${["L1", "L2", "L3", "L4", "L5"]
                                        .map((l) => `<option value="${l}" ${item.pisa_level === l ? "selected" : ""}>${l}</option>`)
                                        .join("")}
                                    </select>
                                  </label>
                                  <label class="field">
                                    <span>Subject hint</span>
                                    <input class="js-field" data-key="subject_hint" type="text" value="${escapeHtml(item.subject_hint)}" placeholder="math, language, science…" />
                                  </label>
                                  <label class="field">
                                    <span>Tags</span>
                                    <input class="js-field" data-key="tags" type="text" value="${escapeHtml(item.tags)}" placeholder="[Bloom: L2 | PISA: L1]" />
                                  </label>
                                  <label class="field">
                                    <span>Difficulty</span>
                                    <select class="js-field" data-key="difficulty">
                                      <option value="" ${!item.difficulty ? "selected" : ""}>—</option>
                                      <option value="easy" ${item.difficulty === "easy" ? "selected" : ""}>Easy</option>
                                      <option value="medium" ${item.difficulty === "medium" ? "selected" : ""}>Medium</option>
                                      <option value="hard" ${item.difficulty === "hard" ? "selected" : ""}>Hard</option>
                                    </select>
                                  </label>
                                  <label class="field">
                                    <span>Tier</span>
                                    <select class="js-field" data-key="tier">
                                      <option value="basic" ${item.tier === "basic" ? "selected" : ""}>Basic</option>
                                      <option value="premium" ${item.tier === "premium" ? "selected" : ""}>Premium</option>
                                    </select>
                                  </label>
                                  ${
                                    isPremium
                                      ? `<label class="field full-span">
                                          <span>Color hints (premium) — JSON: { "word": "color" }</span>
                                          <textarea class="js-color-hints" rows="2" placeholder='{ "kvadrat": "blue" }'>${escapeHtml(item.color_hints ? JSON.stringify(item.color_hints) : "")}</textarea>
                                        </label>
                                        <label class="field full-span">
                                          <span>Blank icons (premium) — comma-separated, one per blank (use "" for none)</span>
                                          <input class="js-blank-icons" type="text" value="${escapeHtml((item.blank_icons || []).map((b) => b || "").join(", "))}" placeholder="lightbulb, , star" />
                                        </label>`
                                      : ""
                                  }
                                </div>`
                              : ""
                          }
                        </div>

                        ${renderValidation(item, ctx)}
                      </section>
                    `;
                  })
                  .join("")
              : `<div class="empty-state glass-card inline-empty">
                  <div class="empty-orb" aria-hidden="true">📝</div>
                  <h3>No cloze passages</h3>
                  <p>Add a Sentence Fill passage with multi-blank fill.</p>
                  <button class="btn btn-primary js-add-item" type="button">Add first passage</button>
                </div>`
          }
        </div>
      `;
    }

    function syncAnswersAndExpls(item) {
      // Whenever passage blanks count changes, resize answers / explanations / blank_icons.
      const blanks = detectBlanks(item.passage);
      const oldAnswers = item.answers || [];
      const newAnswers = oldAnswers.slice(0, blanks);
      while (newAnswers.length < blanks) newAnswers.push("");
      item.answers = newAnswers;

      if (Array.isArray(item.explanations)) {
        const e = item.explanations.slice(0, blanks);
        while (e.length < blanks) e.push(null);
        item.explanations = e;
      }
      if (Array.isArray(item.blank_icons)) {
        const b = item.blank_icons.slice(0, blanks);
        while (b.length < blanks) b.push(null);
        item.blank_icons = b;
      }
    }

    container.oninput = (event) => {
      const itemEl = event.target.closest("[data-index]");
      if (!itemEl) return;
      const index = Number(itemEl.dataset.index);
      const item = state[index];
      if (!item) return;

      const field = event.target.closest(".js-field");
      if (field) {
        const key = field.dataset.key;
        if (key === "mode") {
          const newMode = field.value === "free_recall" ? "free_recall" : "word_bank";
          const previousMode = item.mode;
          item.mode = newMode;
          if (newMode === "word_bank" && !Array.isArray(item.word_bank)) item.word_bank = [];
          if (newMode === "free_recall") item.word_bank = null;
          if (previousMode !== newMode) {
            emit(state, onChange);
            repaint();
            return;
          }
        } else if (key === "tier") {
          item.tier = field.value === "premium" ? "premium" : "basic";
          emit(state, onChange);
          repaint();
          return;
        } else if (key === "passage") {
          item.passage = field.value;
          syncAnswersAndExpls(item);
          emit(state, onChange);
          repaint();
          return;
        } else if (["pisa_level", "difficulty", "subject_hint", "tags"].includes(key)) {
          item[key] = field.value;
        }
        emit(state, onChange);
        return;
      }

      const answer = event.target.closest(".js-answer");
      if (answer) {
        const blankIdx = Number(answer.closest("[data-blank-index]")?.dataset.blankIndex);
        if (Number.isFinite(blankIdx)) {
          if (!Array.isArray(item.answers)) item.answers = [];
          item.answers[blankIdx] = answer.value;
          // Auto-pre-populate word_bank with answers (additive — don't drop distractors).
          if (item.mode === "word_bank") {
            const bank = Array.isArray(item.word_bank) ? item.word_bank : [];
            const lower = bank.map((w) => w.trim().toLowerCase());
            const v = (answer.value || "").trim();
            if (v && !lower.includes(v.toLowerCase())) bank.push(v);
            item.word_bank = bank;
          }
          emit(state, onChange);
        }
        return;
      }

      const expl = event.target.closest(".js-explanation");
      if (expl) {
        const explIdx = Number(expl.closest("[data-explanation-index]")?.dataset.explanationIndex);
        if (Number.isFinite(explIdx)) {
          if (!Array.isArray(item.explanations)) {
            const blanks = detectBlanks(item.passage);
            item.explanations = new Array(blanks).fill(null);
          }
          item.explanations[explIdx] = expl.value || null;
          emit(state, onChange);
        }
        return;
      }

      const colorHints = event.target.closest(".js-color-hints");
      if (colorHints) {
        try {
          const parsed = colorHints.value.trim() ? JSON.parse(colorHints.value) : null;
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            item.color_hints = parsed;
          } else {
            item.color_hints = null;
          }
        } catch (_e) {
          // leave color_hints unchanged on parse failure — user will see warning when saving
        }
        emit(state, onChange);
        return;
      }

      const blankIcons = event.target.closest(".js-blank-icons");
      if (blankIcons) {
        const arr = blankIcons.value.split(",").map((s) => s.trim()).map((s) => (s ? s : null));
        item.blank_icons = arr.length ? arr : null;
        emit(state, onChange);
        return;
      }
    };

    container.onkeydown = (event) => {
      if (event.key !== "Enter" && event.key !== ",") return;
      const addChip = event.target.closest(".js-add-chip");
      if (!addChip) return;
      event.preventDefault();
      const itemEl = event.target.closest("[data-index]");
      if (!itemEl) return;
      const index = Number(itemEl.dataset.index);
      const item = state[index];
      if (!item || item.mode !== "word_bank") return;
      const value = addChip.value.trim();
      if (!value) return;
      const bank = Array.isArray(item.word_bank) ? item.word_bank : [];
      const lower = bank.map((w) => w.trim().toLowerCase());
      // Split on commas in case user pasted "a, b, c"
      value.split(",").map((s) => s.trim()).filter(Boolean).forEach((v) => {
        if (!lower.includes(v.toLowerCase())) {
          bank.push(v);
          lower.push(v.toLowerCase());
        }
      });
      item.word_bank = bank;
      addChip.value = "";
      emit(state, onChange);
      repaint();
    };

    container.onclick = (event) => {
      if (event.target.closest(".js-add-item")) {
        const newItem = makeItem(ctx);
        state.push(newItem);
        ui.push({ explanationsOpen: false, metaOpen: false });
        emit(state, onChange);
        repaint();
        return;
      }

      const itemEl = event.target.closest("[data-index]");
      if (!itemEl) return;
      const index = Number(itemEl.dataset.index);
      const item = state[index];
      if (!item) return;

      if (event.target.closest(".js-remove-item")) {
        state.splice(index, 1);
        ui.splice(index, 1);
        emit(state, onChange);
        repaint();
        return;
      }

      if (event.target.closest(".js-apply-mode-all")) {
        for (const it of state) it.mode = item.mode;
        for (const it of state) {
          if (it.mode === "word_bank" && !Array.isArray(it.word_bank)) it.word_bank = [];
          if (it.mode === "free_recall") it.word_bank = null;
        }
        emit(state, onChange);
        repaint();
        return;
      }

      if (event.target.closest(".js-toggle-explanations")) {
        ui[index].explanationsOpen = !ui[index].explanationsOpen;
        // Ensure explanations array exists at the right length when opened.
        if (ui[index].explanationsOpen) {
          const blanks = detectBlanks(item.passage);
          if (!Array.isArray(item.explanations)) item.explanations = new Array(blanks).fill(null);
          while (item.explanations.length < blanks) item.explanations.push(null);
          item.explanations = item.explanations.slice(0, blanks);
        }
        repaint();
        return;
      }

      if (event.target.closest(".js-toggle-meta")) {
        ui[index].metaOpen = !ui[index].metaOpen;
        repaint();
        return;
      }

      if (event.target.closest(".js-pull-answers")) {
        const filledAnswers = (item.answers || []).filter((a) => a && a.trim().length > 0);
        const bank = Array.isArray(item.word_bank) ? [...item.word_bank] : [];
        const lower = bank.map((w) => w.trim().toLowerCase());
        for (const a of filledAnswers) {
          if (!lower.includes(a.trim().toLowerCase())) {
            bank.push(a);
            lower.push(a.trim().toLowerCase());
          }
        }
        item.word_bank = bank;
        emit(state, onChange);
        repaint();
        return;
      }

      const removeChip = event.target.closest(".js-remove-chip");
      if (removeChip) {
        const chipIdx = Number(removeChip.closest("[data-chip-index]")?.dataset.chipIndex);
        if (Number.isFinite(chipIdx) && Array.isArray(item.word_bank)) {
          item.word_bank.splice(chipIdx, 1);
          emit(state, onChange);
          repaint();
        }
        return;
      }
    };

    repaint();
    if (window.EditorUtils) {
      window.EditorUtils.bindPasteNormalizer(container);
    }
  }

  window.GameBreakEditors.sentenceFill = { render };
})();
