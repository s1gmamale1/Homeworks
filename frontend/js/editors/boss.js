// frontend/js/editors/boss.js
// Boss editor: edits content_json.boss_questions PLUS the sibling
// content_json.boss_meta (BossMeta wrapper added in Chunk A).
//
// Mounting:
//   render(container, data, onChange, context = {})
//     where context = { grade, subject, tier } (defaults below if omitted).
//     Reads: context.grade (grade-band default), context.tier (premium gates).
//
// `data` continues to be the boss_questions array (builder.js dispatches the
// array directly via applyPhaseChange("final_challenge", ...)). The sibling
// `boss_meta` block is read/written via
// `window.BUILDER_STATE.homework.content_json.boss_meta` — autosave's
// `getContent()` already serializes the full content_json, so mutations there
// land in the next PUT after we trigger a `markDirty` via the array's
// onChange callback (FINAL_BOSS_BACKEND_PLAN.md §4a — "thread it through").

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

  // ---------------------------------------------------------------------------
  // Boss-meta + per-question metadata helpers
  // (mirrors `_boss-helpers.js` so the editor still works if the helpers file
  // didn't load first; that file remains the canonical source for tests.)
  // ---------------------------------------------------------------------------

  const BOSS_TYPES = ["sub", "big", "mythical"];
  const GRADE_BANDS = ["g1_4", "g5", "g6_8", "g9_11"];
  const PISA_LEVELS = ["L1", "L2", "L3", "L4", "L5", "L6"];
  const BLOOM_LEVELS = ["apply", "analyze", "evaluate", "create"];

  function bossTypeOptions(tier) {
    return tier === "premium" ? ["sub", "big", "mythical"] : ["sub"];
  }

  function gradeBandFromGrade(grade) {
    const g = Number(grade) || 8;
    if (g <= 4) return "g1_4";
    if (g === 5) return "g5";
    if (g <= 8) return "g6_8";
    return "g9_11";
  }

  function defaultHpForGradeBand(band) {
    return { g1_4: 50, g5: 100, g6_8: 100, g9_11: 150 }[band] || 100;
  }

  function defaultHintCostForGradeBand(band) {
    return { g1_4: 5, g5: 10, g6_8: 10, g9_11: 15 }[band] || 10;
  }

  function defaultAttemptsForBossType(bossType, tier) {
    if (bossType === "big") return 1;
    if (bossType === "mythical") return 1;
    return tier === "premium" ? null : 2;
  }

  function defaultContext() {
    return { grade: 8, subject: "general", tier: "basic" };
  }

  function defaultBossMeta(ctx) {
    const band = gradeBandFromGrade(ctx.grade);
    return {
      boss_type: "sub",
      grade_band: band,
      attempts_max: defaultAttemptsForBossType("sub", ctx.tier),
      starting_hp_override: null,
      anti_cheat: null,
    };
  }

  function readBossMetaFromState() {
    try {
      const cj = window.BUILDER_STATE?.homework?.content_json;
      if (cj && typeof cj === "object" && cj.boss_meta && typeof cj.boss_meta === "object") {
        return cj.boss_meta;
      }
    } catch (_e) {
      // BUILDER_STATE may not exist outside the builder shell.
    }
    return null;
  }

  function writeBossMetaToState(meta) {
    try {
      const homework = window.BUILDER_STATE?.homework;
      if (!homework) return;
      homework.content_json = homework.content_json || {};
      // Strip falsy meta back to null so the PUT body matches the BossMeta
      // schema exactly (Chunk A's BossMeta validates extras=allow but None
      // is the canonical "absent" marker on Pydantic).
      homework.content_json.boss_meta = meta || null;
    } catch (_e) {
      /* best-effort */
    }
  }

  // Sanitize meta on emit per the premium-gate contract (mirrors TM/RLC):
  //   - tier=basic → boss_type collapses to "sub"; anti_cheat dropped
  //   - mythical without 1-or-null attempts → coerce to 1 (Pydantic enforces)
  function sanitizeMetaForEmit(meta, tier) {
    if (!meta || typeof meta !== "object") return null;
    const out = {
      boss_type: BOSS_TYPES.includes(meta.boss_type) ? meta.boss_type : "sub",
      grade_band: GRADE_BANDS.includes(meta.grade_band) ? meta.grade_band : null,
      attempts_max: meta.attempts_max == null
        ? null
        : (Number.isFinite(Number(meta.attempts_max)) ? Number(meta.attempts_max) : null),
      starting_hp_override: meta.starting_hp_override == null
        ? null
        : (Number.isFinite(Number(meta.starting_hp_override)) ? Number(meta.starting_hp_override) : null),
      anti_cheat: meta.anti_cheat && typeof meta.anti_cheat === "object"
        ? {
            paste_detect: Boolean(meta.anti_cheat.paste_detect),
            response_time_floor_ms: Number.isFinite(Number(meta.anti_cheat.response_time_floor_ms))
              ? Number(meta.anti_cheat.response_time_floor_ms)
              : 0,
          }
        : null,
    };
    // Premium gates — basic tier collapses elevated fields.
    if (tier !== "premium") {
      if (out.boss_type !== "sub") out.boss_type = "sub";
      out.anti_cheat = null;
    }
    // Mythical fix-up: attempts_max ∈ {None, 1} per spec §3.
    if (out.boss_type === "mythical" && out.attempts_max != null && out.attempts_max !== 1) {
      out.attempts_max = 1;
    }
    return out;
  }

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

  function defaultAnswerSpec() {
    return {
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
  }

  function normalizeQuestion(question) {
    const dmg = DAMAGE_VALUES.includes(Number(question?.dmg)) ? Number(question.dmg) : 10;

    // Merge default spec/rubric with whatever the question provides.
    // Replacing the whole default with question.answer_spec dropped rubric
    // keys when fixtures supplied answer_spec without a rubric, and the
    // editor crashed on spec.rubric.correct.
    const defaults = defaultAnswerSpec();
    const provided = question?.answer_spec || {};
    const providedRubric = provided.rubric || {};
    const spec = {
      ...defaults,
      ...provided,
      rubric: {
        ...defaults.rubric,
        ...providedRubric
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
      answer_spec: spec,
      // New explicit per-question metadata (Chunk A schema additions —
      // FINAL_BOSS_BACKEND_PLAN.md §1a). Empty string = "use default" so the
      // editor can render an empty-option state without dropping the field.
      pisa_level: PISA_LEVELS.includes(question?.pisa_level) ? question.pisa_level : "",
      bloom_level: BLOOM_LEVELS.includes(question?.bloom_level) ? question.bloom_level : "",
      hint_cost_per_use: Number.isFinite(Number(question?.hint_cost_per_use))
        ? Number(question.hint_cost_per_use)
        : null,
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

  function render(container, data, onChange, context = {}) {
    const ctx = {
      ...defaultContext(),
      grade: context && context.grade != null ? context.grade : defaultContext().grade,
      subject: context && context.subject != null ? context.subject : defaultContext().subject,
      tier: context && context.tier != null ? context.tier : defaultContext().tier,
    };
    const state = normalize(data);

    // Boss-meta lives next to boss_questions on content_json. Builder.js
    // dispatches the array directly, so we round-trip the meta object via
    // window.BUILDER_STATE — autosave's getContent() reads the full
    // content_json and our writes flow through to the next PUT.
    const existingMeta = readBossMetaFromState();
    const meta = existingMeta && typeof existingMeta === "object"
      ? {
          boss_type: BOSS_TYPES.includes(existingMeta.boss_type) ? existingMeta.boss_type : "sub",
          grade_band: GRADE_BANDS.includes(existingMeta.grade_band)
            ? existingMeta.grade_band
            : gradeBandFromGrade(ctx.grade),
          attempts_max: existingMeta.attempts_max == null ? null : Number(existingMeta.attempts_max),
          starting_hp_override: existingMeta.starting_hp_override == null
            ? null
            : Number(existingMeta.starting_hp_override),
          anti_cheat: existingMeta.anti_cheat && typeof existingMeta.anti_cheat === "object"
            ? {
                paste_detect: Boolean(existingMeta.anti_cheat.paste_detect),
                response_time_floor_ms: Number(existingMeta.anti_cheat.response_time_floor_ms) || 0,
              }
            : null,
        }
      : defaultBossMeta(ctx);

    // UI flag — boss-meta block collapsed by default per plan §4b.
    const ui = { metaOpen: false };

    function persistMeta() {
      writeBossMetaToState(sanitizeMetaForEmit(meta, ctx.tier));
    }

    function repaint() {
      const typeOptions = bossTypeOptions(ctx.tier);
      const isPremium = ctx.tier === "premium";
      const bandHpHint = defaultHpForGradeBand(meta.grade_band || gradeBandFromGrade(ctx.grade));
      const bandHintCostHint = defaultHintCostForGradeBand(meta.grade_band || gradeBandFromGrade(ctx.grade));
      const attemptsPlaceholder = meta.attempts_max == null
        ? (defaultAttemptsForBossType(meta.boss_type, ctx.tier) == null
            ? "Unlimited (premium sub default)"
            : String(defaultAttemptsForBossType(meta.boss_type, ctx.tier)))
        : "";
      const ac = meta.anti_cheat || { paste_detect: false, response_time_floor_ms: 0 };

      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card boss-meta-card">
            <div class="editor-header compact-header">
              <div>
                <p class="eyebrow">Boss meta</p>
                <h3>${ui.metaOpen ? "Editing meta" : "Boss configuration (collapsed)"}</h3>
              </div>
              <button class="btn btn-ghost js-toggle-meta" type="button">
                ${ui.metaOpen ? "Hide" : "Show"}
              </button>
            </div>
            ${
              ui.metaOpen
                ? `
                <div class="editor-grid">
                  <label class="field">
                    <span>Boss type</span>
                    <select class="js-meta-field" data-key="boss_type">
                      ${BOSS_TYPES.map((t) => {
                        const allowed = typeOptions.includes(t);
                        return `<option value="${t}" ${meta.boss_type === t ? "selected" : ""} ${allowed ? "" : "disabled"}>${t}${allowed ? "" : " (premium)"}</option>`;
                      }).join("")}
                    </select>
                    ${!isPremium ? `<small class="sf-hint">Big and Mythical require Premium tier.</small>` : ""}
                  </label>
                  <label class="field">
                    <span>Grade band</span>
                    <select class="js-meta-field" data-key="grade_band">
                      ${GRADE_BANDS.map(
                        (b) => `<option value="${b}" ${meta.grade_band === b ? "selected" : ""}>${b}</option>`
                      ).join("")}
                    </select>
                  </label>
                  <label class="field">
                    <span>Attempts max</span>
                    <input class="js-meta-field" data-key="attempts_max" type="number" min="1" step="1"
                      value="${meta.attempts_max == null ? "" : escapeHtml(meta.attempts_max)}"
                      placeholder="${escapeHtml(attemptsPlaceholder)}" />
                    <small class="sf-hint">Leave blank for unlimited (Premium Sub default).</small>
                  </label>
                  <label class="field">
                    <span>Starting HP override</span>
                    <input class="js-meta-field" data-key="starting_hp_override" type="number" min="10" step="1"
                      value="${meta.starting_hp_override == null ? "" : escapeHtml(meta.starting_hp_override)}"
                      placeholder="${escapeHtml(bandHpHint)} (band default)" />
                  </label>
                  <fieldset class="field full-span boss-anticheat" ${isPremium ? "" : "disabled"}>
                    <legend>Anti-cheat policy ${isPremium ? "" : "(Premium only)"}</legend>
                    <div class="editor-grid">
                      <label class="field">
                        <input class="js-meta-anticheat" data-key="paste_detect" type="checkbox"
                          ${ac.paste_detect ? "checked" : ""} ${isPremium ? "" : "disabled"} />
                        <span>Paste detection</span>
                      </label>
                      <label class="field">
                        <span>Response time floor (ms)</span>
                        <input class="js-meta-anticheat" data-key="response_time_floor_ms" type="number" min="0" step="100"
                          value="${escapeHtml(ac.response_time_floor_ms || 0)}" ${isPremium ? "" : "disabled"} />
                      </label>
                    </div>
                  </fieldset>
                </div>
                `
                : `<p class="muted-text">Type: <strong>${escapeHtml(meta.boss_type)}</strong> · Band: <strong>${escapeHtml(meta.grade_band || gradeBandFromGrade(ctx.grade))}</strong> · Attempts: <strong>${meta.attempts_max == null ? "∞" : escapeHtml(meta.attempts_max)}</strong></p>`
            }
          </section>
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
              Hint cost defaults to <strong>+${escapeHtml(bandHintCostHint)} HP</strong> for grade band ${escapeHtml(meta.grade_band || gradeBandFromGrade(ctx.grade))}.
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
                          <div class="field full-span">
                            <span>Question</span>
                            <div class="js-rich-host" data-key="q" data-index="${index}"></div>
                          </div>

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

                          <div class="field full-span">
                            <span>Hint</span>
                            <div class="js-rich-host" data-key="hint" data-index="${index}"></div>
                          </div>

                          <label class="field">
                            <span>PISA level (advisory)</span>
                            <select class="js-field" data-key="pisa_level">
                              <option value="" ${!question.pisa_level ? "selected" : ""}>—</option>
                              ${PISA_LEVELS.map(
                                (l) => `<option value="${l}" ${question.pisa_level === l ? "selected" : ""}>${l}</option>`
                              ).join("")}
                            </select>
                          </label>
                          <label class="field">
                            <span>Bloom level (advisory)</span>
                            <select class="js-field" data-key="bloom_level">
                              <option value="" ${!question.bloom_level ? "selected" : ""}>—</option>
                              ${BLOOM_LEVELS.map(
                                (b) => `<option value="${b}" ${question.bloom_level === b ? "selected" : ""}>${b}</option>`
                              ).join("")}
                            </select>
                          </label>
                          <label class="field">
                            <span>Hint cost per use (HP)</span>
                            <input class="js-field" data-key="hint_cost_per_use" type="number" min="0" step="1"
                              value="${question.hint_cost_per_use == null ? "" : escapeHtml(question.hint_cost_per_use)}"
                              placeholder="${escapeHtml(defaultHintCostForGradeBand(meta.grade_band || gradeBandFromGrade(ctx.grade)))} (band default)" />
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
      // Persist boss_meta to BUILDER_STATE so the next autosave PUT carries it.
      // (This MUST run alongside any onChange so markDirty fires too.)
      persistMeta();
      emit(state, onChange);
    }

    // Apply the spec §11 mythical-zero-hints side effect to the live state +
    // the existing singular `hint` field (the schema's actual storage). The
    // helper's `clearHintsForMythical` scrubs `hints[]` arrays — we do both
    // here so we cover the legacy + future per-q hint shapes.
    function applyMythicalHintClear() {
      let changed = 0;
      state.forEach((q) => {
        if (q.hint && stripHtml(q.hint)) {
          q.hint = "";
          changed += 1;
        }
        if (Array.isArray(q.hints) && q.hints.length) {
          q.hints = [];
          changed += 1;
        }
      });
      return changed;
    }

    function handleBossTypeChange(nextType) {
      // Premium gate enforcement — basic tier can only pick "sub".
      if (ctx.tier !== "premium" && nextType !== "sub") {
        meta.boss_type = "sub";
        return;
      }
      // Mythical: zero-hint enforcement per spec §11.
      if (nextType === "mythical") {
        const hasAnyHints = state.some(
          (q) => (q.hint && stripHtml(q.hint)) || (Array.isArray(q.hints) && q.hints.length)
        );
        if (hasAnyHints) {
          const ok = (typeof window !== "undefined" && typeof window.confirm === "function")
            ? window.confirm("Mythical boss must have zero hints (spec §11). Clear all hints?")
            : true;
          if (!ok) {
            // Revert the type change.
            meta.boss_type = meta.boss_type || "sub";
            return;
          }
          applyMythicalHintClear();
        }
      }
      meta.boss_type = nextType;
      // Auto-fill attempts_max per spec §3 if author hadn't customized.
      const expectedDefault = defaultAttemptsForBossType(nextType, ctx.tier);
      meta.attempts_max = expectedDefault;
    }

    container.oninput = (event) => {
      const target = event.target;

      // Boss-meta inputs live OUTSIDE [data-index]; handle them first.
      if (target.classList.contains("js-meta-field")) {
        const key = target.dataset.key;
        if (key === "attempts_max" || key === "starting_hp_override") {
          const raw = target.value.trim();
          meta[key] = raw === "" ? null : Number(raw);
        } else {
          meta[key] = target.value;
        }
        syncAndEmit();
        return;
      }
      if (target.classList.contains("js-meta-anticheat")) {
        meta.anti_cheat = meta.anti_cheat || { paste_detect: false, response_time_floor_ms: 0 };
        const key = target.dataset.key;
        if (key === "paste_detect") {
          meta.anti_cheat.paste_detect = Boolean(target.checked);
        } else if (key === "response_time_floor_ms") {
          const raw = target.value.trim();
          meta.anti_cheat.response_time_floor_ms = raw === "" ? 0 : Number(raw) || 0;
        }
        syncAndEmit();
        return;
      }

      const index = Number(target.closest("[data-index]")?.dataset.index);
      if (!Number.isFinite(index)) return;

      if (target.classList.contains("js-field")) {
        const key = target.dataset.key;
        if (key === "hint_cost_per_use") {
          const raw = target.value.trim();
          state[index][key] = raw === "" ? null : Number(raw);
        } else {
          state[index][key] = target.value;
        }
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

      // Boss-type / grade-band dropdowns live outside per-question scope.
      if (target.classList.contains("js-meta-field")) {
        const key = target.dataset.key;
        if (key === "boss_type") {
          handleBossTypeChange(target.value);
          syncAndEmit();
          repaint();
          return;
        }
        if (key === "grade_band") {
          meta.grade_band = GRADE_BANDS.includes(target.value) ? target.value : meta.grade_band;
          syncAndEmit();
          repaint();
          return;
        }
        // Other text/number meta fields handled in oninput.
        return;
      }

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
      } else if (target.classList.contains("js-field") && target.dataset.key === "pisa_level") {
        state[index].pisa_level = PISA_LEVELS.includes(target.value) ? target.value : "";
        syncAndEmit();
      } else if (target.classList.contains("js-field") && target.dataset.key === "bloom_level") {
        state[index].bloom_level = BLOOM_LEVELS.includes(target.value) ? target.value : "";
        syncAndEmit();
      }
    };

    container.onclick = (event) => {
      if (event.target.closest(".js-toggle-meta")) {
        ui.metaOpen = !ui.metaOpen;
        repaint();
        return;
      }

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

    // NOTE: do NOT persist meta on first render — that would silently
    // overwrite content_json.boss_meta on every editor mount. The user's
    // first interaction (any field) flows through syncAndEmit → persistMeta,
    // which is the right "consent" point. Existing rows w/ meta untouched
    // until user edits.

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
