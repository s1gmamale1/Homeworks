// frontend/js/editors/listening.js
// Listening editor (GRADED): audio URL + gated transcript + checkpoint questions.
// Mirrors the Reading editor. The runtime keeps the transcript hidden until the
// student has played the audio (the "one rule"). Audio is URL-only for v1 —
// file upload + media migration are deferred.

(function () {
  "use strict";

  window.Editors = window.Editors || {};

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

  function getByPath(obj, path) {
    const parts = String(path || "").split(".");
    let cur = obj;
    for (const p of parts) {
      if (cur == null) return undefined;
      const idx = /^\d+$/.test(p) ? Number(p) : p;
      cur = cur[idx];
    }
    return cur;
  }

  function setByPath(obj, path, value) {
    const parts = String(path || "").split(".");
    let cur = obj;
    for (let i = 0; i < parts.length - 1; i++) {
      const key = /^\d+$/.test(parts[i]) ? Number(parts[i]) : parts[i];
      if (cur[key] == null || typeof cur[key] !== "object") {
        cur[key] = {};
      }
      cur = cur[key];
    }
    const lastKey = /^\d+$/.test(parts[parts.length - 1]) ? Number(parts[parts.length - 1]) : parts[parts.length - 1];
    cur[lastKey] = value;
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value ?? null));
  }

  function normalizeCheckpoint(checkpoint) {
    // `ans` may arrive as a list (segment-aware fixtures); collapse to a string
    // for the single-answer input. The injector re-expands string → ans/acceptable.
    const ans = Array.isArray(checkpoint?.ans) ? (checkpoint.ans[0] || "") : (checkpoint?.ans || "");
    return {
      prompt: checkpoint?.prompt || checkpoint?.q || "",
      ans,
      fb: checkpoint?.fb || "",
    };
  }

  function normalize(data) {
    const safe = data && typeof data === "object" ? data : {};

    return {
      title: safe.title || "",
      audio_url: safe.audio_url || "",
      transcript: safe.transcript || "",
      checkpoints: Array.isArray(safe.checkpoints) ? safe.checkpoints.map(normalizeCheckpoint) : [],
    };
  }

  function makeCheckpoint() {
    return {
      prompt: "",
      ans: "",
      fb: "",
    };
  }

  function emit(state, onChange) {
    onChange(clone(state));
  }

  function renderCheckpoints(state) {
    if (!state.checkpoints.length) {
      return `
        <div class="empty-state glass-card inline-empty">
          <div class="empty-orb" aria-hidden="true">🎧</div>
          <h3>No listening checkpoints yet</h3>
          <p>Add comprehension questions about the audio.</p>
          <button class="btn btn-primary js-add-checkpoint" type="button">Add first checkpoint</button>
        </div>
      `;
    }

    return state.checkpoints
      .map(
        (checkpoint, index) => `
          <section class="editor-card" data-index="${index}">
            <div class="editor-header">
              <div>
                <p class="eyebrow">Checkpoint ${index + 1}</p>
                <h3>${escapeHtml(stripHtml(checkpoint.prompt) || "Untitled checkpoint")}</h3>
              </div>
              <button class="btn btn-danger js-remove-checkpoint" type="button">Remove</button>
            </div>

            <div class="editor-grid">
              <div class="field full-span">
                <span>Prompt</span>
                <div class="js-rich-host" data-path="checkpoints.${index}.prompt"></div>
              </div>

              <label class="field full-span">
                <span>Accepted answer</span>
                <input class="js-checkpoint-field" data-key="ans" type="text" value="${escapeHtml(checkpoint.ans)}" placeholder="Expected answer" />
              </label>

              <div class="field full-span">
                <span>Feedback</span>
                <div class="js-rich-host" data-path="checkpoints.${index}.fb"></div>
              </div>
            </div>
          </section>
        `
      )
      .join("");
  }

  function repaint(container, state) {
    container.innerHTML = `
      <div class="editor-list">
        <section class="editor-card">
          <div class="editor-header">
            <div>
              <p class="eyebrow">Listening</p>
              <h3>Audio, transcript and checkpoints</h3>
            </div>
            <button class="btn btn-primary js-add-checkpoint" type="button">Add checkpoint</button>
          </div>

          <p class="muted-text">
            Graded phase. The transcript stays hidden until the student plays the audio.
            Paste an audio URL (upload is not supported yet).
          </p>

          <div class="editor-grid">
            <label class="field full-span">
              <span>Listening title</span>
              <input class="js-root-field" data-key="title" type="text" value="${escapeHtml(state.title)}" placeholder="Listening title" />
            </label>

            <label class="field full-span">
              <span>Audio URL</span>
              <input class="js-root-field" data-key="audio_url" type="url" value="${escapeHtml(state.audio_url)}" placeholder="https://…/audio.mp3" />
            </label>

            <div class="field full-span">
              <span>Transcript (revealed after audio plays)</span>
              <div class="js-rich-host" data-path="transcript"></div>
            </div>
          </div>
        </section>

        ${renderCheckpoints(state)}
      </div>
    `;
  }

  function render(container, data, onChange) {
    const state = normalize(data);

    function sync() {
      emit(state, onChange);
    }

    function refresh() {
      repaint(container, state);
      if (window.RichField) {
        container.querySelectorAll(".js-rich-host").forEach((host) => {
          const path = host.dataset.path;
          if (!path) return;
          const initial = getByPath(state, path);
          const isTranscript = path === "transcript";
          const isFeedback = path.endsWith(".fb");
          let placeholder = "Question about the audio...";
          if (isTranscript) placeholder = "Paste or write the transcript...";
          else if (isFeedback) placeholder = "Feedback after response...";
          const mini = window.RichField.create({
            value: initial || "",
            placeholder,
            compact: !isTranscript,
            onChange: (html) => {
              setByPath(state, path, html);
              sync();
            },
          });
          host.appendChild(mini);
        });
      }
    }

    container.oninput = (event) => {
      const rootField = event.target.closest(".js-root-field");
      const checkpointField = event.target.closest(".js-checkpoint-field");

      if (rootField) {
        state[rootField.dataset.key] = rootField.value;
        sync();
        return;
      }

      if (checkpointField) {
        const index = Number(checkpointField.closest("[data-index]")?.dataset.index);
        state.checkpoints[index][checkpointField.dataset.key] = checkpointField.value;
        sync();
      }
    };

    container.onclick = (event) => {
      if (event.target.closest(".js-add-checkpoint")) {
        state.checkpoints.push(makeCheckpoint());
        sync();
        refresh();
        return;
      }

      if (event.target.closest(".js-remove-checkpoint")) {
        const index = Number(event.target.closest("[data-index]")?.dataset.index);
        state.checkpoints.splice(index, 1);
        sync();
        refresh();
      }
    };

    refresh();
    if (window.EditorUtils) {
      window.EditorUtils.bindPasteNormalizer(container);
      window.EditorUtils.bindStrictPasteNormalizer(
        container,
        '.js-checkpoint-field[data-key="ans"]'
      );
    }
  }

  window.Editors.listening = { render };
})();
