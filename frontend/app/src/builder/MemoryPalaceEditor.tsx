import type {
  DraftMemoryPalace,
  DraftMemoryPalaceConcept,
  DraftMemoryPalaceLocation,
  MemoryPalaceEditorProps,
  MemoryPalaceTier,
} from "./types";
import {
  EditorCard,
  Field,
  TextInput,
  TextArea,
  NumberInput,
  Select,
  SmallButton,
} from "./fields";
import e from "./editors.module.css";
import s from "./MemoryPalaceEditor.module.css";

// ---------------------------------------------------------------------------
// Memory Palace editor — owns content_json.gb_memory_palace
// (DraftMemoryPalaceGame = {palaces, concepts}) + gb_memory_palace_config
// (DraftMemoryPalaceConfig). The persisted split is kept: the game slice and
// the config slice are mutated through their OWN callbacks (onChange /
// onConfigChange) — they are never merged here. The injector folds the config
// into the wire shape at serve time.
//
// Per server/schemas/content.py:
//   - MemoryPalace (~618): each palace needs a UNIQUE `key` and 3–7 locations.
//   - MemoryPalaceLocation (~601): {name, sensory_cue?, icon?} stations.
//   - MemoryPalaceConcept (~609): {id?, term, description?, image_cue?}; the
//     id auto-fills "mp-c{n}" server-side when blank, but ids must be unique.
//   - MemoryPalaceConfig (~672): all optional; blank = server default.
//
// The method-of-loci structure the runtime walks (runtime/games/MemoryPalace):
//   palace → ordered locations (stations) ← a concept is placed at each one.
// The author writes the route (palaces + their stations) and the concept pool;
// the STUDENT chooses the concept→station mapping at play time, so there is no
// author-set "correct placement" key to redact. Hence: two independent lists.
// ---------------------------------------------------------------------------

// Schema bounds: a palace route is 3–7 stations (3 for low grades, 5 default,
// 7 for premium high grades). Enforced server-side; surfaced as a soft warning.
const MIN_LOCATIONS = 3;
const MAX_LOCATIONS = 7;

const SUBJECT_FAMILY_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "— Auto (universal) —" },
  { value: "universal", label: "Universal" },
  { value: "bio", label: "Biology" },
  { value: "chem", label: "Chemistry" },
  { value: "phys", label: "Physics" },
  { value: "math", label: "Mathematics" },
  { value: "history", label: "History" },
  { value: "lang", label: "Language" },
  { value: "art", label: "Art" },
];

const TIER_OPTIONS: { value: MemoryPalaceTier; label: string }[] = [
  { value: "basic", label: "Basic" },
  { value: "premium", label: "Premium" },
];

// ---- factories -------------------------------------------------------------

/** A fresh station with the bare-minimum shape. */
function emptyLocation(): DraftMemoryPalaceLocation {
  return { name: "" };
}

/** A new palace seeded with the minimum-valid 3 stations + a unique key. */
function emptyPalace(key: string): DraftMemoryPalace {
  return {
    key,
    name: "",
    tier: "basic",
    locations: [emptyLocation(), emptyLocation(), emptyLocation()],
  };
}

/** A new concept with a stable id that won't collide with the existing pool. */
function emptyConcept(id: string): DraftMemoryPalaceConcept {
  return { id, term: "" };
}

/** Next free "palace-N" key (never reuses an in-use key → uniqueness holds). */
function nextPalaceKey(palaces: DraftMemoryPalace[]): string {
  const used = new Set(palaces.map((p) => p.key));
  let n = palaces.length + 1;
  while (used.has(`palace-${n}`)) n += 1;
  return `palace-${n}`;
}

/** Next free "mp-c{N}" concept id matching the server's auto-fill scheme. */
function nextConceptId(concepts: DraftMemoryPalaceConcept[]): string {
  const used = new Set(concepts.map((c) => c.id).filter(Boolean) as string[]);
  let n = concepts.length + 1;
  while (used.has(`mp-c${n}`)) n += 1;
  return `mp-c${n}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function MemoryPalaceEditor({
  value,
  config,
  onChange,
  onConfigChange,
}: MemoryPalaceEditorProps) {
  const { palaces, concepts } = value;

  // ---- palace mutations (game slice via onChange) -------------------------
  const patchPalace = (i: number, p: Partial<DraftMemoryPalace>) => {
    onChange({
      ...value,
      palaces: palaces.map((pl, idx) => (idx === i ? { ...pl, ...p } : pl)),
    });
  };

  const addPalace = () => {
    onChange({ ...value, palaces: [...palaces, emptyPalace(nextPalaceKey(palaces))] });
  };

  const removePalace = (i: number) => {
    onChange({ ...value, palaces: palaces.filter((_, idx) => idx !== i) });
  };

  // ---- location (station) mutations ---------------------------------------
  const patchLocation = (
    pi: number,
    li: number,
    p: Partial<DraftMemoryPalaceLocation>,
  ) => {
    const locations = palaces[pi].locations.map((l, idx) =>
      idx === li ? { ...l, ...p } : l,
    );
    patchPalace(pi, { locations });
  };

  const addLocation = (pi: number) => {
    if (palaces[pi].locations.length >= MAX_LOCATIONS) return;
    patchPalace(pi, { locations: [...palaces[pi].locations, emptyLocation()] });
  };

  const removeLocation = (pi: number, li: number) => {
    if (palaces[pi].locations.length <= MIN_LOCATIONS) return;
    patchPalace(pi, {
      locations: palaces[pi].locations.filter((_, idx) => idx !== li),
    });
  };

  // ---- concept mutations (game slice via onChange) ------------------------
  const patchConcept = (i: number, p: Partial<DraftMemoryPalaceConcept>) => {
    onChange({
      ...value,
      concepts: concepts.map((c, idx) => (idx === i ? { ...c, ...p } : c)),
    });
  };

  const addConcept = () => {
    onChange({ ...value, concepts: [...concepts, emptyConcept(nextConceptId(concepts))] });
  };

  const removeConcept = (i: number) => {
    onChange({ ...value, concepts: concepts.filter((_, idx) => idx !== i) });
  };

  // ---- config mutations (config slice via onConfigChange) -----------------
  const patchConfigNumber = (key: "concept_count" | "min_palace_options", raw: number) => {
    // A non-finite / blanked value clears the override so the injector default
    // re-applies. NumberInput emits 0 for empty; we treat <=0 as "cleared".
    if (!Number.isFinite(raw) || raw <= 0) {
      const next = { ...config };
      delete next[key];
      onConfigChange(next);
      return;
    }
    onConfigChange({ ...config, [key]: raw });
  };

  const patchReverseRecall = (on: boolean) => {
    if (!on) {
      // Default is False server-side — drop the key entirely when off.
      const next = { ...config };
      delete next.enable_reverse_recall;
      onConfigChange(next);
      return;
    }
    onConfigChange({ ...config, enable_reverse_recall: true });
  };

  const patchGradeOverride = (band: "low" | "high", raw: number) => {
    const overrides: Record<string, number> = {
      ...(config.concept_count_grade_overrides ?? {}),
    };
    if (!Number.isFinite(raw) || raw <= 0) {
      delete overrides[band];
    } else {
      overrides[band] = raw;
    }
    const next = { ...config };
    if (Object.keys(overrides).length > 0) {
      next.concept_count_grade_overrides = overrides;
    } else {
      delete next.concept_count_grade_overrides;
    }
    onConfigChange(next);
  };

  // ---- duplicate-key detection (mirrors the server validator) -------------
  const keyCounts = palaces.reduce<Record<string, number>>((acc, p) => {
    const k = p.key.trim();
    if (k) acc[k] = (acc[k] ?? 0) + 1;
    return acc;
  }, {});

  const overrides = config.concept_count_grade_overrides ?? {};

  return (
    <div className={e.editor}>
      {/* ===================== Section 1 · Palaces ===================== */}
      <EditorCard
        title="Palaces & stations"
        actions={
          <SmallButton tone="primary" onClick={addPalace}>
            + Add palace
          </SmallButton>
        }
      >
        <p className={e.help}>
          A palace is a familiar route the student walks in their mind. Each{" "}
          <strong>station</strong> is one stop on that route; a concept gets
          mentally placed at each stop. Give every palace a <strong>unique
          key</strong> and <strong>{MIN_LOCATIONS}–{MAX_LOCATIONS} stations</strong>{" "}
          (the first palace is the one students walk).
        </p>

        {palaces.length === 0 && (
          <p className={e.empty}>
            No palaces yet. Add one to lay out the route students will memorize.
          </p>
        )}

        {palaces.map((palace, pi) => {
          const stationCount = palace.locations.length;
          const dupKey = palace.key.trim() !== "" && keyCounts[palace.key.trim()] > 1;
          const tooFew = stationCount < MIN_LOCATIONS;
          const tooMany = stationCount > MAX_LOCATIONS;

          return (
            <div key={pi} className={e.subItem}>
              <div className={e.subItemHead}>
                <span className={e.subItemLabel}>
                  Palace {pi + 1}
                  {pi === 0 && <span className={s.tagPrimary}>Played first</span>}
                </span>
                <SmallButton tone="danger" onClick={() => removePalace(pi)}>
                  Remove
                </SmallButton>
              </div>

              <div className={s.fieldGrid}>
                <Field label="Key" hint="Unique per palace — no spaces">
                  <TextInput
                    value={palace.key}
                    onChange={(key) => patchPalace(pi, { key })}
                    placeholder="e.g. palace-1"
                  />
                </Field>
                <Field label="Name">
                  <TextInput
                    value={palace.name}
                    onChange={(name) => patchPalace(pi, { name })}
                    placeholder="e.g. My childhood home"
                  />
                </Field>
                <Field label="Icon" hint="Optional emoji">
                  <TextInput
                    value={palace.icon ?? ""}
                    onChange={(icon) => patchPalace(pi, { icon: icon || undefined })}
                    placeholder="e.g. 🏠"
                  />
                </Field>
                <Field label="Subject family" hint="Themes the visuals">
                  <Select<string>
                    value={palace.subject_family ?? ""}
                    options={SUBJECT_FAMILY_OPTIONS}
                    onChange={(v) =>
                      patchPalace(pi, { subject_family: v || undefined })
                    }
                  />
                </Field>
                <Field label="Tier">
                  <Select<MemoryPalaceTier>
                    value={palace.tier ?? "basic"}
                    options={TIER_OPTIONS}
                    onChange={(tier) => patchPalace(pi, { tier })}
                  />
                </Field>
              </div>

              <Field label="Description" hint="What the route feels like">
                <TextArea
                  value={palace.description ?? ""}
                  rows={2}
                  onChange={(v) =>
                    patchPalace(pi, { description: v || undefined })
                  }
                  placeholder="A short walkthrough of the place…"
                />
              </Field>

              {dupKey && (
                <p className={s.warn} role="status">
                  This key is used by another palace — keys must be unique.
                </p>
              )}

              {/* ---- stations (locations) for this palace ---- */}
              <div className={s.stationBlock}>
                <div className={s.stationHead}>
                  <span className={s.stationHeading}>
                    Stations
                    <span className={e.help} style={{ margin: 0 }}>
                      In walk order
                    </span>
                  </span>
                  <span
                    className={[
                      s.stationCount,
                      (tooFew || tooMany) && s.stationCountBad,
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    {stationCount} / {MIN_LOCATIONS}–{MAX_LOCATIONS}
                  </span>
                </div>

                {palace.locations.map((loc, li) => (
                  <div key={li} className={s.station}>
                    <span className={s.stationIndex} aria-hidden="true">
                      {li + 1}
                    </span>
                    <div className={s.stationFields}>
                      <Field label="Station name">
                        <TextInput
                          value={loc.name}
                          onChange={(name) => patchLocation(pi, li, { name })}
                          placeholder="e.g. The front door"
                        />
                      </Field>
                      <Field label="Sensory cue" hint="A vivid detail">
                        <TextInput
                          value={loc.sensory_cue ?? ""}
                          onChange={(v) =>
                            patchLocation(pi, li, {
                              sensory_cue: v || undefined,
                            })
                          }
                          placeholder="e.g. The smell of fresh paint"
                        />
                      </Field>
                      <Field label="Icon" hint="Optional emoji">
                        <TextInput
                          value={loc.icon ?? ""}
                          onChange={(v) =>
                            patchLocation(pi, li, { icon: v || undefined })
                          }
                          placeholder="e.g. 🚪"
                        />
                      </Field>
                    </div>
                    <SmallButton
                      tone="danger"
                      onClick={() => removeLocation(pi, li)}
                      disabled={stationCount <= MIN_LOCATIONS}
                    >
                      ✕
                    </SmallButton>
                  </div>
                ))}

                <SmallButton
                  onClick={() => addLocation(pi)}
                  disabled={stationCount >= MAX_LOCATIONS}
                >
                  + Add station
                </SmallButton>

                {tooFew && (
                  <p className={s.warn} role="status">
                    Add {MIN_LOCATIONS - stationCount} more station
                    {MIN_LOCATIONS - stationCount === 1 ? "" : "s"} — a palace
                    needs at least {MIN_LOCATIONS}.
                  </p>
                )}
                {tooMany && (
                  <p className={s.warn} role="status">
                    Remove {stationCount - MAX_LOCATIONS} station
                    {stationCount - MAX_LOCATIONS === 1 ? "" : "s"} — the limit
                    is {MAX_LOCATIONS}.
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </EditorCard>

      {/* ===================== Section 2 · Concepts ===================== */}
      <EditorCard
        title="Concepts to place"
        actions={
          <SmallButton tone="primary" onClick={addConcept}>
            + Add concept
          </SmallButton>
        }
      >
        <p className={e.help}>
          The pool of ideas the student encodes along the route. Each concept
          gets its own <strong>vivid image</strong> so it sticks. Students decide
          which station each concept lives at — so there's no fixed answer key
          here, just the things worth remembering.
        </p>

        {concepts.length === 0 && (
          <p className={e.empty}>
            No concepts yet. Add the terms students should walk into memory.
          </p>
        )}

        {concepts.map((concept, ci) => {
          const missingTerm = concept.term.trim() === "";
          return (
            <div key={ci} className={e.subItem}>
              <div className={e.subItemHead}>
                <span className={e.subItemLabel}>
                  Concept {ci + 1}
                  <span className={s.idTag}>
                    {concept.id?.trim() || `mp-c${ci + 1}`}
                  </span>
                </span>
                <SmallButton tone="danger" onClick={() => removeConcept(ci)}>
                  Remove
                </SmallButton>
              </div>

              <Field label="Term" hint="The thing to remember">
                <TextInput
                  value={concept.term}
                  onChange={(term) => patchConcept(ci, { term })}
                  placeholder="e.g. Mitochondria"
                />
              </Field>
              <Field label="Description" hint="A plain-language reminder">
                <TextArea
                  value={concept.description ?? ""}
                  rows={2}
                  onChange={(v) =>
                    patchConcept(ci, { description: v || undefined })
                  }
                  placeholder="e.g. The powerhouse of the cell…"
                />
              </Field>
              <Field
                label="Image cue"
                hint="An exaggerated picture that makes it stick"
              >
                <TextArea
                  value={concept.image_cue ?? ""}
                  rows={2}
                  onChange={(v) =>
                    patchConcept(ci, { image_cue: v || undefined })
                  }
                  placeholder="e.g. A glowing battery roaring like an engine"
                />
              </Field>

              {missingTerm && (
                <p className={s.warn} role="status">
                  Add a term — an empty concept can't be placed.
                </p>
              )}
            </div>
          );
        })}
      </EditorCard>

      {/* ===================== Section 3 · Settings ===================== */}
      <EditorCard title="Game settings">
        <p className={e.help}>
          Optional tuning for the round. Leave a field blank to use the built-in
          default. These live in their own config slice, separate from the
          palaces above.
        </p>

        <div className={s.configGrid}>
          <Field
            label="Concepts per round"
            hint="How many to walk — default 5"
          >
            <NumberInput
              value={config.concept_count ?? NaN}
              min={1}
              onChange={(n) => patchConfigNumber("concept_count", n)}
            />
          </Field>
          <Field
            label="Minimum palace options"
            hint="Recall choices shown — default 4"
          >
            <NumberInput
              value={config.min_palace_options ?? NaN}
              min={2}
              onChange={(n) => patchConfigNumber("min_palace_options", n)}
            />
          </Field>
        </div>

        <div className={s.gradeBlock}>
          <span className={s.stationHeading}>
            Concept count by grade band
            <span className={e.help} style={{ margin: 0 }}>
              Optional overrides
            </span>
          </span>
          <div className={s.configGrid}>
            <Field label="Low grades" hint="e.g. grades 1–4 — try 3">
              <NumberInput
                value={overrides.low ?? NaN}
                min={1}
                onChange={(n) => patchGradeOverride("low", n)}
              />
            </Field>
            <Field label="High grades" hint="e.g. grades 8–11 — try 7">
              <NumberInput
                value={overrides.high ?? NaN}
                min={1}
                onChange={(n) => patchGradeOverride("high", n)}
              />
            </Field>
          </div>
        </div>

        <label className={s.toggleRow}>
          <input
            type="checkbox"
            className={s.checkbox}
            checked={config.enable_reverse_recall ?? false}
            onChange={(ev) => patchReverseRecall(ev.target.checked)}
          />
          <span className={s.toggleText}>
            <span className={s.toggleLabel}>Enable reverse recall</span>
            <span className={s.toggleHint}>
              Ask students for the station given the concept (reserved for a
              future mode).
            </span>
          </span>
        </label>
      </EditorCard>
    </div>
  );
}
