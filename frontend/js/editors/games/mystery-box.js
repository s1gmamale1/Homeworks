// frontend/js/editors/games/mystery-box.js
// Mystery Box editor — interleaved category recognition.
// Contract storage: content_json.gb_mystery_box: [{ category, q, a }]
//   - category: the true problem-type label (e.g. "Algebra", "Geometry", "Reading")
//   - q: the problem shown after the box opens (HTML, supports formulas + images)
//   - a: accepted answer (case-insensitive, whitespace-trimmed)
// Runtime derives the picker labels from the union of all items' categories,
// so authoring 3 boxes with categories ["Algebra","Geometry","Reading"] gives
// a 3-option ID picker. If only one unique category exists, the ID step is
// effectively a confirmation. Recommended count: 3-5 boxes per session.

(function () {
  "use strict";

  window.GameBreakEditors = window.GameBreakEditors || {};

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

  function normalize(items) {
    return Array.isArray(items)
      ? items.map((item) => ({
          category: typeof item?.category === "string" ? item.category : "",
          q: typeof item?.q === "string" ? item.q : "",
          a: typeof item?.a === "string" ? item.a : "",
        }))
      : [];
  }

  function makeItem() {
    return { category: "", q: "", a: "" };
  }

  function emit(state, onChange) {
    onChange(clone(state));
  }

  function summary(value) {
    const stripped = stripHtml(value);
    return stripped || "—";
  }

  function categoriesHint(state) {
    const labels = state
      .map((item) => (item.category || "").trim())
      .filter(Boolean);
    const unique = Array.from(new Set(labels));
    if (!state.length) return "Add 3-5 boxes for the interleaving effect";
    if (!unique.length) return "⚠ No categories set — student picker will be empty";
    if (unique.length === 1) return `Only "${unique[0]}" — ID step will be a confirmation, not a real choice`;
    return `${unique.length} categories: ${unique.join(", ")}`;
  }

  function render(container, data, onChange) {
    const state = normalize(data);

    function repaint() {
      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header compact-header">
              <div>
                <p class="eyebrow">Mystery Box</p>
                <h3>${state.length} box${state.length === 1 ? "" : "es"}</h3>
              </div>
              <button class="btn btn-primary js-add-item" type="button">Add box</button>
            </div>
            <p class="muted-text">
              Interleaved category recognition. Each box contains a problem from a different category. Student first identifies the category, then solves. Authoring tip: vary categories across boxes — that's the whole point of the mechanic.
            </p>
            <p class="muted-text" style="font-style:italic;">${escapeHtml(categoriesHint(state))}</p>
          </section>

          ${
            state.length
              ? state
                  .map(
                    (item, index) => `
                      <section class="editor-card nested-card" data-index="${index}">
                        <div class="editor-header compact-header">
                          <div>
                            <p class="eyebrow">Box ${index + 1}</p>
                            <h3>${escapeHtml(item.category || "Untitled category")} — ${escapeHtml(summary(item.q))}</h3>
                          </div>
                          <button class="btn btn-danger js-remove-item" type="button">Remove</button>
                        </div>

                        <div class="editor-grid">
                          <div class="field full-span">
                            <span>Category label (the true problem type)</span>
                            <input class="js-field" data-key="category" type="text" value="${escapeHtml(item.category)}" placeholder="Algebra / Geometry / Reading / …" />
                          </div>

                          <div class="field full-span">
                            <span>Problem (shown after the box opens)</span>
                            <div class="js-rich-host" data-key="q" data-index="${index}"></div>
                          </div>

                          <div class="field full-span">
                            <span>Accepted answer</span>
                            <input class="js-field" data-key="a" type="text" value="${escapeHtml(item.a)}" placeholder="Numeric or short text answer" />
                          </div>
                        </div>
                      </section>
                    `,
                  )
                  .join("")
              : `<div class="empty-state glass-card inline-empty">
                  <div class="empty-orb" aria-hidden="true">📦</div>
                  <h3>No mystery boxes</h3>
                  <p>Add boxes — each one a problem from a different category. The student must first identify which category, then solve.</p>
                  <button class="btn btn-primary js-add-item" type="button">Add first box</button>
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
          const editor = window.RichField.create({
            value: initial,
            placeholder: "Problem statement (text, formula, image)…",
            compact: true,
            onChange: (html) => {
              if (!state[index]) return;
              state[index][key] = html;
              emit(state, onChange);
            },
          });
          host.appendChild(editor);
        });
      }
    }

    container.oninput = (event) => {
      const field = event.target.closest(".js-field");
      if (!field) return;
      const wrap = field.closest("[data-index]");
      if (!wrap) return;
      const index = Number(wrap.dataset.index);
      const key = field.dataset.key;
      if (!Number.isFinite(index) || !key) return;
      state[index][key] = field.value;
      emit(state, onChange);
      // Live-update the categories hint when category changes.
      if (key === "category") {
        const hint = container.querySelector(".editor-card .muted-text[style*='italic']");
        if (hint) hint.textContent = categoriesHint(state);
      }
    };

    container.onclick = (event) => {
      if (event.target.closest(".js-add-item")) {
        state.push(makeItem());
        emit(state, onChange);
        repaint();
        return;
      }
      if (event.target.closest(".js-remove-item")) {
        const index = Number(event.target.closest("[data-index]")?.dataset.index);
        if (!Number.isFinite(index)) return;
        state.splice(index, 1);
        emit(state, onChange);
        repaint();
      }
    };

    repaint();
    if (window.EditorUtils) {
      window.EditorUtils.bindPasteNormalizer(container);
    }
  }

  window.GameBreakEditors.mysteryBox = { render };
})();
