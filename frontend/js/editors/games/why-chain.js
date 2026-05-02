// frontend/js/editors/games/why-chain.js
// Why Chain editor for production game break.
// (Originally mislabeled "Sentence Fill" in the UI; renamed 2026-05-02 when
// the real Sentence Fill cloze game shipped under its own data key
// (content_json.gb_sentence_fill). This editor remains the production editor
// for the Why Chain game; data shape is unchanged.)
//
// Contract storage maps this game to content_json.gb_why_chain:
// { q, inv, reprompts[], expects[] }

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
          q: item?.q || "",
          inv: item?.inv || "",
          reprompts: Array.isArray(item?.reprompts) && item.reprompts.length ? item.reprompts : [""],
          // Wave 2 fix (per-level expect): optional per-level expected keyword. When
          // empty, runtime falls back to invariant. Backwards compatible.
          expects: Array.isArray(item?.expects) ? item.expects.map((e) => String(e ?? "")) : [],
        }))
      : [];
  }

  function makeItem() {
    return {
      q: "",
      inv: "",
      reprompts: [""],
      expects: [],
    };
  }

  function emit(state, onChange) {
    state.forEach((item) => {
      if (!Array.isArray(item.reprompts) || !item.reprompts.length) item.reprompts = [""];
      if (!Array.isArray(item.expects)) item.expects = [];
    });
    onChange(clone(state));
  }

  function renderReprompts(item) {
    return item.reprompts
      .map(
        (reprompt, repromptIndex) => {
          const expectVal = (item.expects && item.expects[repromptIndex]) || "";
          return `
          <div class="option-row" data-reprompt-index="${repromptIndex}" style="flex-direction:column; align-items:stretch; gap:6px;">
            <div style="display:flex; gap:8px; align-items:center;">
              <input class="js-reprompt" type="text" value="${escapeHtml(reprompt)}" placeholder="Hint / reprompt ${repromptIndex + 1}" style="flex:1;" />
              <button class="icon-btn js-remove-reprompt" type="button" title="Remove reprompt">×</button>
            </div>
            <input class="js-expect" type="text" value="${escapeHtml(expectVal)}" placeholder="Expected keyword(s) for level ${repromptIndex + 1} (optional — falls back to invariant)" style="flex:1; font-size:0.92em; opacity:0.9;" />
          </div>
        `;
        }
      )
      .join("");
  }

  function render(container, data, onChange) {
    const state = normalize(data);

    function repaint() {
      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header compact-header">
              <div>
                <p class="eyebrow">Sentence Fill</p>
                <h3>${state.length} cloze prompt${state.length === 1 ? "" : "s"}</h3>
              </div>
              <button class="btn btn-primary js-add-item" type="button">Add cloze prompt</button>
            </div>
            <p class="muted-text">
              Use a blank in the prompt, for example <strong>43 × 20 = 43 × ___ × 10</strong>. The expected answer goes in <strong>inv</strong>.
            </p>
          </section>

          ${
            state.length
              ? state
                  .map(
                    (item, index) => `
                      <section class="editor-card nested-card" data-index="${index}">
                        <div class="editor-header compact-header">
                          <div>
                            <p class="eyebrow">Cloze ${index + 1}</p>
                            <h3>${escapeHtml(stripHtml(item.q) || "Untitled cloze prompt")}</h3>
                          </div>
                          <button class="btn btn-danger js-remove-item" type="button">Remove</button>
                        </div>

                        <div class="editor-grid">
                          <div class="field full-span">
                            <span>Prompt with blank</span>
                            <div class="js-rich-host" data-key="q" data-index="${index}"></div>
                          </div>

                          <label class="field full-span">
                            <span>Correct answer / invariant</span>
                            <input class="js-field" data-key="inv" type="text" value="${escapeHtml(item.inv)}" placeholder="20 = 2 × 10" />
                          </label>
                        </div>

                        <div class="editor-card nested-card">
                          <div class="editor-header compact-header">
                            <div>
                              <p class="eyebrow">Reprompts</p>
                              <h3>${item.reprompts.length} hint${item.reprompts.length === 1 ? "" : "s"}</h3>
                            </div>
                            <button class="btn btn-ghost js-add-reprompt" type="button">Add reprompt</button>
                          </div>
                          <div class="editor-list">
                            ${renderReprompts(item)}
                          </div>
                        </div>
                      </section>
                    `
                  )
                  .join("")
              : `<div class="empty-state glass-card inline-empty">
                  <div class="empty-orb" aria-hidden="true">🧩</div>
                  <h3>No cloze prompts</h3>
                  <p>Add sentence-fill prompts for contextual recall.</p>
                  <button class="btn btn-primary js-add-item" type="button">Add first cloze prompt</button>
                </div>`
          }
        </div>
      `;

      // Mount RichField editors for `q` (cloze prompt).
      if (window.RichField) {
        container.querySelectorAll(".js-rich-host").forEach((host) => {
          const index = Number(host.dataset.index);
          const key = host.dataset.key;
          if (!Number.isFinite(index) || !key) return;
          const initial = state[index] ? state[index][key] : "";
          const mini = window.RichField.create({
            value: initial || "",
            placeholder: "Bo'shliqni to'ldiring: 43 × 20 = 43 × ___ × 10",
            compact: true,
            onChange: (html) => {
              if (!state[index]) return;
              state[index][key] = html;
              emit(state, onChange);
            },
          });
          host.appendChild(mini);
        });
      }
    }

    container.oninput = (event) => {
      const field = event.target.closest(".js-field");
      const reprompt = event.target.closest(".js-reprompt");
      const expect = event.target.closest(".js-expect");

      if (field) {
        const index = Number(field.closest("[data-index]")?.dataset.index);
        state[index][field.dataset.key] = field.value;
        emit(state, onChange);
        return;
      }

      if (reprompt) {
        const itemIndex = Number(reprompt.closest("[data-index]")?.dataset.index);
        const repromptIndex = Number(reprompt.closest("[data-reprompt-index]")?.dataset.repromptIndex);
        state[itemIndex].reprompts[repromptIndex] = reprompt.value;
        emit(state, onChange);
        return;
      }

      if (expect) {
        const itemIndex = Number(expect.closest("[data-index]")?.dataset.index);
        const repromptIndex = Number(expect.closest("[data-reprompt-index]")?.dataset.repromptIndex);
        if (!Array.isArray(state[itemIndex].expects)) state[itemIndex].expects = [];
        state[itemIndex].expects[repromptIndex] = expect.value;
        emit(state, onChange);
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
        state.splice(index, 1);
        emit(state, onChange);
        repaint();
        return;
      }

      if (event.target.closest(".js-add-reprompt")) {
        const index = Number(event.target.closest("[data-index]")?.dataset.index);
        state[index].reprompts.push("");
        if (Array.isArray(state[index].expects)) state[index].expects.push("");
        emit(state, onChange);
        repaint();
        return;
      }

      if (event.target.closest(".js-remove-reprompt")) {
        const itemIndex = Number(event.target.closest("[data-index]")?.dataset.index);
        const repromptIndex = Number(event.target.closest("[data-reprompt-index]")?.dataset.repromptIndex);
        state[itemIndex].reprompts.splice(repromptIndex, 1);
        if (Array.isArray(state[itemIndex].expects) && state[itemIndex].expects.length > repromptIndex) {
          state[itemIndex].expects.splice(repromptIndex, 1);
        }
        if (!state[itemIndex].reprompts.length) state[itemIndex].reprompts.push("");
        emit(state, onChange);
        repaint();
      }
    };

    repaint();
    if (window.EditorUtils) {
      window.EditorUtils.bindPasteNormalizer(container);
      window.EditorUtils.bindStrictPasteNormalizer(
        container,
        'input.js-field[data-key="inv"], input.js-expect'
      );
    }
  }

  window.GameBreakEditors.whyChain = { render };
})();
