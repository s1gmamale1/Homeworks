// frontend/js/editors/games/adaptive-quiz.js
// Adaptive Quiz editor тАФ card-styled like flashcards.
// Data: { q, tags, tier, ans[], answer_spec, capture, hint?, media? }

(function () {
  "use strict";

  window.GameBreakEditors = window.GameBreakEditors || {};

  const TIERS = ["EASY", "MEDIUM", "HARD"];
  const ANSWER_TYPES = [
    { value: "numeric", label: "Numeric" },
    { value: "set_match", label: "Equation roots / set" },
    { value: "text_exact", label: "Text (exact)" },
    { value: "text_fuzzy", label: "Text (fuzzy)" },
    { value: "semantic", label: "Free-form (AI only)" }
  ];

  const TIER_COLORS = {
    EASY:   { bg: "rgba(52, 199, 89, 0.14)",  fg: "#1f7a3b" },
    MEDIUM: { bg: "rgba(255, 149, 0, 0.14)",  fg: "#a85400" },
    HARD:   { bg: "rgba(255, 59, 48, 0.14)",  fg: "#a8281f" },
  };

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

  function normalizeMedia(m) {
    if (!m || typeof m !== "object") return null;
    if (m.type === "image" && (m.src || "").trim()) {
      return { type: "image", src: String(m.src), alt: String(m.alt || "") };
    }
    if (m.type === "svg" && (m.html || "").trim()) {
      return { type: "svg", html: String(m.html) };
    }
    return null;
  }

  function normalizeItem(item) {
    const spec = item?.answer_spec || {
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
    
    // Backward compat
    if (!spec.canonical_display && item?.ans && item.ans.length) {
      spec.canonical_display = item.ans[0];
      spec.expected = item.ans[0];
    }

    return {
      q: item?.q || "",
      tags: item?.tags || "[Bloom: L1 | PISA: L1]",
      tier: TIERS.includes(item?.tier) ? item.tier : "EASY",
      ans: Array.isArray(item?.ans) && item.ans.length ? item.ans : [spec.canonical_display || ""],
      answer_spec: spec,
      capture: Boolean(item?.capture),
      hint: item?.hint || "",
      media: normalizeMedia(item?.media),
    };
  }

  function normalize(items) {
    return Array.isArray(items) ? items.map(normalizeItem) : [];
  }

  function makeItem() {
    return normalizeItem({});
  }

  function emit(state, onChange) {
    state.forEach((item) => {
      if (!TIERS.includes(item.tier)) item.tier = "EASY";
      // Sync old ans array
      item.ans = [item.answer_spec.canonical_display || ""];
    });
    onChange(clone(state));
  }

  function renderTierOptions(active) {
    return TIERS.map(
      (t) => `<option value="${t}" ${t === active ? "selected" : ""}>${t}</option>`,
    ).join("");
  }

  function renderAnswerSpecForm(item, index) {
    const spec = item.answer_spec;
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
          <span>Tolerance (┬▒)</span>
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
          <input type="text" class="js-spec-field" data-key="canonical_display" value="${escapeHtml(spec.canonical_display)}" placeholder="Model answer" />
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
          <span>Allow AI Fallback</span>
        </label>

        <details class="full-span">
          <summary>Grading Rubric</summary>
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
          <p class="eyebrow">Accepted Examples</p>
          <div class="preview-content js-preview-content">Loading preview...</div>
        </div>
      </div>
    `;
  }

  function renderMediaPreview(media) {
    if (!media) {
      return `<div class="fc-media-empty">No media attached тАФ click <strong>Image</strong> or <strong>SVG</strong> to add one.</div>`;
    }
    if (media.type === "image") {
      return `<img class="fc-media-preview-img" src="${escapeHtml(media.src)}" alt="${escapeHtml(media.alt || "")}" />`;
    }
    if (media.type === "svg") {
      return `<div class="fc-media-preview-svg">${media.html}</div>`;
    }
    return "";
  }

  function render(container, data, onChange) {
    const state = normalize(data);

    function repaint() {
      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header">
              <div>
                <p class="eyebrow">Adaptive Quiz</p>
                <h3>${state.length} question${state.length === 1 ? "" : "s"}</h3>
              </div>
              <button class="btn btn-primary js-add-item" type="button">Add question</button>
            </div>
          </section>

          ${
            state.length
              ? state
                  .map((item, index) => {
                    const tier = item.tier;
                    const colors = TIER_COLORS[tier] || TIER_COLORS.EASY;
                    const qSummary = stripHtml(item.q) || "Untitled adaptive question";
                    return `
                      <section class="flashcard-builder-card" data-index="${index}" style="--fc-strip:${colors.fg};">
                        <div class="flashcard-builder-strip" style="background:${colors.fg};"></div>
                        <div class="flashcard-builder-header">
                          <div class="flashcard-builder-title">
                            <span class="eyebrow">Question ${index + 1}</span>
                            <h3>${escapeHtml(qSummary).slice(0, 80)}</h3>
                          </div>
                          <div class="flashcard-builder-actions">
                            <span class="status-pill" style="background:${colors.bg};color:${colors.fg};">${tier}</span>
                            <button class="btn btn-danger js-remove-item" type="button">Remove</button>
                          </div>
                        </div>

                        <div class="fc-media-zone">
                          <div class="fc-media-head">
                            <span class="fc-face-label">Media (optional)</span>
                            <div class="fc-media-tools">
                              <button class="btn btn-ghost js-card-img" type="button">тЬФ Image</button>
                              <button class="btn btn-ghost js-card-svg" type="button">тЧЖ SVG</button>
                              ${item.media ? `<button class="btn btn-ghost js-card-clear-media" type="button">Clear</button>` : ""}
                            </div>
                          </div>
                          <div class="fc-media-body">
                            ${renderMediaPreview(item.media)}
                          </div>
                        </div>

                        <div class="fc-face">
                          <div class="fc-face-label">Question</div>
                          <div class="js-rich-host" data-key="q" data-index="${index}"></div>
                        </div>

                        <div class="fc-divider"><span>тЖУ answer grading below тЖУ</span></div>

                        <div class="fc-face">
                          ${renderAnswerSpecForm(item, index)}
                        </div>

                        <div class="fc-meta-row">
                          <div class="field">
                            <span>Tier</span>
                            <select class="js-field" data-key="tier">
                              ${renderTierOptions(tier)}
                            </select>
                          </div>
                          <div class="field">
                            <span>Capture</span>
                            <select class="js-capture">
                              <option value="false" ${!item.capture ? "selected" : ""}>Off</option>
                              <option value="true" ${item.capture ? "selected" : ""}>Require notebook</option>
                            </select>
                          </div>
                          <div class="field full-span">
                            <span>Tags</span>
                            <input class="js-field" data-key="tags" type="text" value="${escapeHtml(item.tags)}" placeholder="[Bloom: L1 | PISA: L1]" />
                          </div>
                          <div class="field full-span">
                            <span>ЁЯжа Hint (optional)</span>
                            <textarea class="js-field" data-key="hint" rows="2" placeholder="A gentle nudge...">${escapeHtml(item.hint)}</textarea>
                          </div>
                        </div>
                      </section>
                    `;
                  })
                  .join("")
              : `<div class="empty-state glass-card inline-empty">
                  <div class="empty-orb" aria-hidden="true">🎯</div>
                  <h3>No adaptive questions</h3>
                  <button class="btn btn-primary js-add-item" type="button">Add first question</button>
                </div>`
          }
        </div>
      `;

      if (window.RichField && window.RichField.create) {
        container.querySelectorAll(".js-rich-host").forEach((host) => {
          const index = Number(host.dataset.index);
          const key = host.dataset.key;
          if (!Number.isFinite(index) || !key) return;
          const initial = state[index]?.[key] || "";
          const mini = window.RichField.create({
            value: initial,
            placeholder: "Type the question here...",
            compact: false,
            onChange: (html) => {
              if (!state[index]) return;
              state[index][key] = html;
              emit(state, onChange);
            },
          });
          host.appendChild(mini);
        });
      }
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

    container.oninput = (event) => {
      const target = event.target;
      const wrap = target.closest("[data-index]");
      if (!wrap) return;
      const index = Number(wrap.dataset.index);
      if (!Number.isFinite(index)) return;

      if (target.classList.contains("js-field")) {
        state[index][target.dataset.key] = target.value;
        emit(state, onChange);
      } else if (target.classList.contains("js-spec-field")) {
        const key = target.dataset.key;
        let val = target.value;
        if (key === "expected" && state[index].answer_spec.type === "set_match") {
          val = val.split(",").map(s => s.trim()).filter(Boolean);
        }
        state[index].answer_spec[key] = val;
        emit(state, onChange);
        updatePreview(index);
      } else if (target.classList.contains("js-rubric-field")) {
        state[index].answer_spec.rubric[target.dataset.key] = target.value;
        emit(state, onChange);
      }
    };

    container.onchange = (event) => {
      const target = event.target;
      const index = Number(target.closest("[data-index]")?.dataset.index);
      if (!Number.isFinite(index)) return;

      if (target.classList.contains("js-capture")) {
        state[index].capture = target.value === "true";
        emit(state, onChange);
      } else if (target.dataset.key === "tier") {
        state[index].tier = target.value;
        emit(state, onChange);
        repaint();
      } else if (target.classList.contains("js-spec-type")) {
        state[index].answer_spec.type = target.value;
        emit(state, onChange);
        repaint();
      } else if (target.classList.contains("js-spec-ai")) {
        state[index].answer_spec.allow_ai_fallback = target.checked;
        emit(state, onChange);
      }
    };

    container.onclick = (event) => {
      const target = event.target;
      if (target.closest(".js-add-item")) {
        state.push(makeItem());
        emit(state, onChange);
        repaint();
      } else if (target.closest(".js-remove-item")) {
        const index = Number(target.closest("[data-index]")?.dataset.index);
        state.splice(index, 1);
        emit(state, onChange);
        repaint();
      } else if (target.closest(".js-card-img")) {
        const index = Number(target.closest("[data-index]")?.dataset.index);
        if (window.RichField?.openImageModal) {
          window.RichField.openImageModal((src, alt) => {
            if (!src) return;
            state[index].media = { type: "image", src, alt: alt || "" };
            emit(state, onChange);
            repaint();
          });
        }
      } else if (target.closest(".js-card-svg")) {
        const index = Number(target.closest("[data-index]")?.dataset.index);
        if (window.RichField?.openSvgModal) {
          window.RichField.openSvgModal((svgHtml) => {
            if (!svgHtml) return;
            state[index].media = { type: "svg", html: svgHtml };
            emit(state, onChange);
            repaint();
          });
        }
      } else if (target.closest(".js-card-clear-media")) {
        const index = Number(target.closest("[data-index]")?.dataset.index);
        state[index].media = null;
        emit(state, onChange);
        repaint();
      }
    };

    repaint();
  }

  window.GameBreakEditors.adaptiveQuiz = { render };
})();
