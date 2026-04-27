// frontend/js/editors/boss.js
// Boss editor: edits content_json.boss_questions.

(function () {
  "use strict";

  window.Editors = window.Editors || {};

  const DAMAGE_VALUES = [10, 20, 30];
  const ANSWER_TYPES = [
    { value: "numeric", label: "Numeric" },
    { value: "set_match", label: "Equation roots / set" },
    { value: "text_exact", label: "Text (exact)" },
    { value: "text_fuzzy", label: "Text (fuzzy)" },
    { value: "semantic", label: "Free-form (AI only)" }
  ];

  function parseTags(raw) {
    const stripped = String(raw || "")
      .trim()
      .replace(/^\[/, "")
      .replace(/\]$/, "");

    const parts = stripped.split("|").map((segment) => segment.trim()).filter(Boolean);

    const result = { bloom: "", pisa: "", damage: "" };
    for (const part of parts) {
      const [keyRaw, ...valueParts] = part.split(":");
      const key = String(keyRaw || "").trim().toLowerCase();
      const value = valueParts.join(":").trim();

      if (key === "bloom") result.bloom = value;
      else if (key === "pisa") result.pisa = value;
      else if (key === "damage") result.damage = value;
    }
    return result;
  }

  function buildTags(bloom, pisa, dmg) {
    const bloomLabel = bloom || "L2";
    const pisaLabel = pisa || "L2";
    return `[Bloom: ${bloomLabel} | PISA: ${pisaLabel} | Damage: -${dmg} HP]`;
  }

  function updateDamageInTags(existingTags, dmg) {
    const parsed = parseTags(existingTags);
    return buildTags(parsed.bloom, parsed.pisa, dmg);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function stripHtml(value) {
    return String(value ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value ?? []));
  }

  function normalizeQuestion(question) {
    const dmg = DAMAGE_VALUES.includes(Number(question?.dmg)) ? Number(question.dmg) : 10;
    
    // Structured answer_spec
    const spec = question?.answer_spec || {
      type: "text_fuzzy",
      expected: "",
      canonical_display: "",
      allow_ai_fallback: true,
      rubric: {
        correct: "To'g'ri javob!",
        partial: "Qisman to'g'ri.",
        incorrect: "Notog'ri javob."
      }
    };
    
    // Backward compat: if old ans exists and spec is empty, try to migrate
    if (!spec.canonical_display && question?.ans && question.ans.length) {
      spec.canonical_display = question.ans[0];
      spec.expected = question.ans[0];
    }

    return {
      q: question?.q || "",
      tags: question?.tags || `[Bloom: L2 | PISA: L2 | Damage: -${dmg} HP]`,
      ans: Array.isArray(question?.ans) && question.ans.length ? question.ans : [spec.canonical_display || ""],
      hint: question?.hint || "",
      dmg,
      answer_spec: spec
    };
  }

  function normalize(data) {
    return Array.isArray(data) ? data.map(normalizeQuestion) : [];
  }

  function makeQuestion() {
    return normalizeQuestion({});
  }

  function emit(state, onChange) {
    onChange(clone(state));
  }

  function renderDamageOptions(active) {
    return DAMAGE_VALUES.map(
      (value) => `<option value="${value}" ${value === Number(active) ? "selected" : ""}>${value} HP</option>`
    ).join("");
  }

  function renderAnswerSpecForm(question, index) {
    const spec = question.answer_spec;
    const typeOptions = ANSWER_TYPES.map(
      t => `<option value="${t.value}" ${t.value === spec.type ? "selected" : ""}>${t.label}</option>`
    ).join("");

    let typeSpecificFields = "";
    if (spec.type === "numeric") {
      typeSpecificFields = `
        <label class="field">
          <span>Expected Number</span>
          <input type="number" step="any" class="js-spec-field" data-key="expected" value="${escapeHtml(spec.expected)}" />
        </label>
        <label class="field">
          <span>Tolerance (±)</span>
          <input type="number" step="any" class="js-spec-field" data-key="tolerance" value="${escapeHtml(spec.tolerance || 0)}" />
        </label>
      `;
    } else if (spec.type === "set_match") {
      typeSpecificFields = `
        <label class="field full-span">
          <span>Expected Set (comma-separated, e.g. "9, -9")</span>
          <input type="text" class="js-spec-field" data-key="expected" value="${escapeHtml(Array.isArray(spec.expected) ? spec.expected.join(", ") : spec.expected)}" />
        </label>
      `;
    }

    return `
      <div class="editor-grid">
        <label class="field">
          <span>Canonical Display Answer</span>
          <input type="text" class="js-spec-field" data-key="canonical_display" value="${escapeHtml(spec.canonical_display)}" placeholder="Model answer shown to students" />
        </label>
        <label class="field">
          <span>Answer Type</span>
          <select class="js-spec-type">
            ${typeOptions}
          </select>
        </label>

        ${typeSpecificFields}

        <label class="field full-span">
          <input type="checkbox" class="js-spec-ai" ${spec.allow_ai_fallback ? "checked" : ""} />
          <span>Allow AI Fallback for messy/semantic answers</span>
        </label>

        <details class="full-span">
          <summary>Grading Rubric (AI usage)</summary>
          <div class="editor-grid" style="margin-top: 10px;">
            <label class="field full-span">
              <span>Correct</span>
              <textarea class="js-rubric-field" data-key="correct" rows="2">${escapeHtml(spec.rubric.correct)}</textarea>
            </label>
            <label class="field full-span">
              <span>Partial</span>
              <textarea class="js-rubric-field" data-key="partial" rows="2">${escapeHtml(spec.rubric.partial)}</textarea>
            </label>
            <label class="field full-span">
              <span>Incorrect</span>
              <textarea class="js-rubric-field" data-key="incorrect" rows="2">${escapeHtml(spec.rubric.incorrect)}</textarea>
            </label>
          </div>
        </details>

        <div class="full-span preview-pane js-preview-pane" id="preview-${index}">
          <p class="eyebrow">Accepted Examples (AI/Deterministic)</p>
          <div class="preview-content js-preview-content">Loading preview...</div>
        </div>
      </div>
    `;
  }

  function render(container, data, onChange) {
    const state = normalize(data);

    function repaint() {
      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header">
              <div>
                <p class="eyebrow">Final Challenge</p>
                <h3>${state.length} boss question${state.length === 1 ? "" : "s"}</h3>
              </div>
              <button class="btn btn-primary js-add-question" type="button">Add boss question</button>
            </div>
            <p class="muted-text">
              Boss questions map to <strong>BOSS_QUESTIONS</strong>. Damage should usually be 10, 20, or 30 HP.
            </p>
          </section>

          ${
            state.length
              ? state
                  .map(
                    (question, index) => `
                      <section class="editor-card" data-index="${index}">
                        <div class="editor-header">
                          <div>
                            <p class="eyebrow">Boss ${index + 1}</p>
                            <h3>${escapeHtml(stripHtml(question.q) || "Untitled boss question")}</h3>
                          </div>
                          <button class="btn btn-danger js-remove-question" type="button">Remove</button>
                        </div>

                        <div class="editor-grid">
                          <label class="field full-span">
                            <span>Question</span>
                            <div class="js-rich-host" data-key="q" data-index="${index}"></div>
                          </label>

                          <label class="field">
                            <span>Damage</span>
                            <select class="js-dmg">
                              ${renderDamageOptions(question.dmg)}
                            </select>
                          </label>

                          <label class="field">
                            <span>Tags</span>
                            <input class="js-field" data-key="tags" type="text" value="${escapeHtml(question.tags)}" />
                          </label>

                          <label class="field full-span">
                            <span>Hint</span>
                            <div class="js-rich-host" data-key="hint" data-index="${index}"></div>
                          </label>
                        </div>

                        <div class="editor-card nested-card">
                          <div class="editor-header compact-header">
                            <div>
                              <p class="eyebrow">Answer Grading</p>
                              <h3>Hybrid (Deterministic + AI)</h3>
                            </div>
                          </div>
                          ${renderAnswerSpecForm(question, index)}
                        </div>
                      </section>
                    `
                  )
                  .join("")
              : `<div class="empty-state glass-card inline-empty">
                  <div class="empty-orb" aria-hidden="true">👾</div>
                  <h3>No boss questions yet</h3>
                  <p>Add final challenge questions for the homework battle.</p>
                  <button class="btn btn-primary js-add-question" type="button">Add first boss question</button>
                </div>`
          }
        </div>
      `;

      // Mount RichField editors
      if (window.RichField) {
        container.querySelectorAll(".js-rich-host").forEach((host) => {
          const index = Number(host.dataset.index);
          const key = host.dataset.key;
          if (!Number.isFinite(index) || !key) return;
          const initial = state[index] ? state[index][key] : "";
          const placeholder = key === "hint" ? "Hint for student..." : "Boss question...";
          const mini = window.RichField.create({
            value: initial || "",
            placeholder,
            compact: true,
            onChange: (html) => {
              if (!state[index]) return;
              state[index][key] = html;
              syncAndEmit();
            },
          });
          host.appendChild(mini);
        });
      }
      
      // Update previews
      state.forEach((_, i) => updatePreview(i));
    }

    async function updatePreview(index) {
      const q = state[index];
      const previewEl = container.querySelector(`#preview-${index} .js-preview-content`);
      if (!previewEl) return;
      
      try {
        const resp = await fetch("/api/ai/answer-spec/preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answer_spec: q.answer_spec })
        });
        if (!resp.ok) throw new Error("Preview failed");
        const data = await resp.json();
        previewEl.innerHTML = (data.examples || []).map(ex => `<code class="preview-tag">${escapeHtml(ex)}</code>`).join(" ");
      } catch (err) {
        previewEl.innerText = "Error loading preview.";
      }
    }

    function syncAndEmit() {
      state.forEach((question) => {
        // Shadow populate old ans array for backward compat
        question.ans = [question.answer_spec.canonical_display || ""];
      });
      emit(state, onChange);
    }

    container.oninput = (event) => {
      const target = event.target;
      const index = Number(target.closest("[data-index]")?.dataset.index);
      if (!Number.isFinite(index)) return;

      if (target.classList.contains("js-field")) {
        state[index][target.dataset.key] = target.value;
        syncAndEmit();
      } else if (target.classList.contains("js-spec-field")) {
        const key = target.dataset.key;
        let val = target.value;
        if (key === "expected" && state[index].answer_spec.type === "set_match") {
          val = val.split(",").map(s => s.trim()).filter(Boolean);
        }
        state[index].answer_spec[key] = val;
        syncAndEmit();
        updatePreview(index);
      } else if (target.classList.contains("js-rubric-field")) {
        state[index].answer_spec.rubric[target.dataset.key] = target.value;
        syncAndEmit();
      }
    };

    container.onchange = (event) => {
      const target = event.target;
      const index = Number(target.closest("[data-index]")?.dataset.index);
      if (!Number.isFinite(index)) return;

      if (target.classList.contains("js-dmg")) {
        state[index].dmg = Number(target.value);
        state[index].tags = updateDamageInTags(state[index].tags, state[index].dmg);
        syncAndEmit();
        repaint();
      } else if (target.classList.contains("js-spec-type")) {
        state[index].answer_spec.type = target.value;
        syncAndEmit();
        repaint();
      } else if (target.classList.contains("js-spec-ai")) {
        state[index].answer_spec.allow_ai_fallback = target.checked;
        syncAndEmit();
      }
    };

    container.onclick = (event) => {
      if (event.target.closest(".js-add-question")) {
        state.push(makeQuestion());
        syncAndEmit();
        repaint();
        return;
      }

      if (event.target.closest(".js-remove-question")) {
        const index = Number(event.target.closest("[data-index]")?.dataset.index);
        state.splice(index, 1);
        syncAndEmit();
        repaint();
        return;
      }
    };

    repaint();
    if (window.EditorUtils) {
      window.EditorUtils.bindPasteNormalizer(container);
      window.EditorUtils.bindStrictPasteNormalizer(
        container,
        'input[data-key="tags"], .js-spec-field'
      );
    }
  }

  window.Editors.boss = { render };
})();
