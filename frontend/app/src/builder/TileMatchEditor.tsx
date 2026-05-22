import { useMemo } from "react";
import type { ReactNode } from "react";
import type {
  DraftTileMatchPair,
  TileMatchEditorProps,
  TileMatchTier,
} from "./types";
import {
  EditorCard,
  Field,
  TextInput,
  TextArea,
  Select,
  SmallButton,
} from "./fields";
import s from "./TileMatchEditor.module.css";

// Authors gb_tile_match: a list of left/right concept pairs (0–8). Mirrors
// server/schemas/content.py TileMatchPair (~321). The author sees BOTH sides —
// answers live in the draft and are redacted server-side (the injector splits
// each pair into side-disjoint HMAC tokens before delivery). This editor only
// surfaces the schema rules as soft inline warnings; it never hard-blocks
// typing, so a half-edited board stays editable.
//
// Schema rules enforced/surfaced here:
//   • 0–8 pairs
//   • unique `id` (auto-generated stable tm_NNN — never user-edited)
//   • non-empty `left` + `right`, each ≤300 chars
//   • unique `left` strings, unique `right` strings (distractor rule)
//   • at most one `is_palace_tile=true`
//   • palace tiles are premium-only (tier must be "premium")

const MAX_PAIRS = 8;
const MAX_SIDE_CHARS = 300;

const TIER_OPTIONS: { value: TileMatchTier; label: string }[] = [
  { value: "basic", label: "Basic" },
  { value: "premium", label: "Premium" },
];

const DIFFICULTY_OPTIONS: { value: NonNullable<DraftTileMatchPair["difficulty"]>; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

/** Next stable id of the form tm_NNN that doesn't collide with existing ids. */
function nextPairId(pairs: DraftTileMatchPair[]): string {
  const taken = new Set(pairs.map((p) => p.id));
  let n = pairs.length + 1;
  let id = `tm_${String(n).padStart(3, "0")}`;
  while (taken.has(id)) {
    n += 1;
    id = `tm_${String(n).padStart(3, "0")}`;
  }
  return id;
}

function emptyPair(pairs: DraftTileMatchPair[]): DraftTileMatchPair {
  return { id: nextPairId(pairs), left: "", right: "", tier: "basic" };
}

/** Indexes of rows whose trimmed value collides with another row's value. */
function dupeIndexes(values: string[]): Set<number> {
  const seen = new Map<string, number[]>();
  values.forEach((raw, i) => {
    const key = raw.trim().toLowerCase();
    if (!key) return; // empty handled by the non-empty rule, not the dupe rule
    const list = seen.get(key) ?? [];
    list.push(i);
    seen.set(key, list);
  });
  const out = new Set<number>();
  for (const list of seen.values()) {
    if (list.length > 1) list.forEach((i) => out.add(i));
  }
  return out;
}

interface PairIssues {
  leftEmpty: boolean;
  rightEmpty: boolean;
  leftLong: boolean;
  rightLong: boolean;
  leftDupe: boolean;
  rightDupe: boolean;
  palaceNotPremium: boolean;
  extraPalace: boolean;
}

export function TileMatchEditor({ value, onChange }: TileMatchEditorProps) {
  const validation = useMemo(() => {
    const leftDupes = dupeIndexes(value.map((p) => p.left));
    const rightDupes = dupeIndexes(value.map((p) => p.right));
    const palaceIndexes = value
      .map((p, i) => (p.is_palace_tile ? i : -1))
      .filter((i) => i >= 0);

    const issues: PairIssues[] = value.map((p, i) => ({
      leftEmpty: p.left.trim() === "",
      rightEmpty: p.right.trim() === "",
      leftLong: p.left.length > MAX_SIDE_CHARS,
      rightLong: p.right.length > MAX_SIDE_CHARS,
      leftDupe: leftDupes.has(i),
      rightDupe: rightDupes.has(i),
      palaceNotPremium: !!p.is_palace_tile && p.tier !== "premium",
      // every palace tile after the first is "extra"
      extraPalace: !!p.is_palace_tile && palaceIndexes[0] !== i,
    }));

    return {
      issues,
      tooMany: value.length > MAX_PAIRS,
      multiplePalace: palaceIndexes.length > 1,
    };
  }, [value]);

  const patchPair = (i: number, p: Partial<DraftTileMatchPair>) => {
    onChange(value.map((pair, idx) => (idx === i ? { ...pair, ...p } : pair)));
  };

  const addPair = () => {
    if (value.length >= MAX_PAIRS) return;
    onChange([...value, emptyPair(value)]);
  };

  const removePair = (i: number) => {
    onChange(value.filter((_, idx) => idx !== i));
  };

  const movePair = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= value.length) return;
    const next = [...value];
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  };

  const atCap = value.length >= MAX_PAIRS;

  return (
    <div className={s.editor}>
      <p className={s.help}>
        Match a concept on the <strong>left</strong> with its meaning on the{" "}
        <strong>right</strong>. The student taps a left tile, then its match —
        so every <strong>left</strong> and every <strong>right</strong> must be
        distinct (duplicates would make a tap ambiguous). Up to {MAX_PAIRS}{" "}
        pairs. Answers are hidden from students automatically.
      </p>

      {value.length === 0 ? (
        <EditorCard
          title="Tile Match"
          actions={
            <SmallButton tone="primary" onClick={addPair}>
              + Add pair
            </SmallButton>
          }
        >
          <p className={s.empty}>
            No pairs yet. Add at least one concept↔meaning pair, or leave this
            game empty to skip it.
          </p>
        </EditorCard>
      ) : (
        value.map((pair, i) => {
          const issue = validation.issues[i];
          const left = pair.left;
          const right = pair.right;
          const palaceDisabled = pair.tier !== "premium";
          return (
            <EditorCard
              key={pair.id}
              title={`Pair ${i + 1}`}
              actions={
                <div className={s.rowActions}>
                  <span className={s.idTag} title="Auto-generated stable id">
                    {pair.id}
                  </span>
                  <SmallButton
                    onClick={() => movePair(i, -1)}
                    disabled={i === 0}
                  >
                    ↑
                  </SmallButton>
                  <SmallButton
                    onClick={() => movePair(i, 1)}
                    disabled={i === value.length - 1}
                  >
                    ↓
                  </SmallButton>
                  <SmallButton tone="danger" onClick={() => removePair(i)}>
                    ✕ Remove
                  </SmallButton>
                </div>
              }
            >
              <div className={s.pairGrid}>
                <Field
                  label="Left — concept"
                  hint="Formula, term, or symbol"
                >
                  <TextInput
                    value={left}
                    onChange={(v) => patchPair(i, { left: v })}
                    placeholder="e.g. Photosynthesis"
                  />
                  {issue.leftEmpty && (
                    <Warn>Left side can’t be empty.</Warn>
                  )}
                  {issue.leftLong && (
                    <Warn>
                      Left is {left.length}/{MAX_SIDE_CHARS} chars — trim it.
                    </Warn>
                  )}
                  {issue.leftDupe && (
                    <Warn>
                      Another pair uses this same left text. Each left must be
                      unique.
                    </Warn>
                  )}
                </Field>

                <Field
                  label="Right — meaning"
                  hint="Definition or example"
                >
                  <TextArea
                    value={right}
                    rows={2}
                    onChange={(v) => patchPair(i, { right: v })}
                    placeholder="e.g. How plants convert light into energy"
                  />
                  {issue.rightEmpty && (
                    <Warn>Right side can’t be empty.</Warn>
                  )}
                  {issue.rightLong && (
                    <Warn>
                      Right is {right.length}/{MAX_SIDE_CHARS} chars — trim it.
                    </Warn>
                  )}
                  {issue.rightDupe && (
                    <Warn>
                      Another pair uses this same right text. Each right must be
                      unique.
                    </Warn>
                  )}
                </Field>
              </div>

              <div className={s.metaGrid}>
                <Field label="Tier">
                  <Select<TileMatchTier>
                    value={pair.tier ?? "basic"}
                    options={TIER_OPTIONS}
                    onChange={(tier) =>
                      patchPair(i, {
                        tier,
                        // Demoting to basic clears the premium-only palace flag.
                        ...(tier !== "premium" && pair.is_palace_tile
                          ? { is_palace_tile: false }
                          : {}),
                      })
                    }
                  />
                </Field>

                <Field label="Difficulty" hint="Optional">
                  <Select<NonNullable<DraftTileMatchPair["difficulty"]> | "">
                    value={pair.difficulty ?? ""}
                    options={[
                      { value: "", label: "—" },
                      ...DIFFICULTY_OPTIONS,
                    ]}
                    onChange={(d) =>
                      patchPair(i, {
                        difficulty: d === "" ? undefined : d,
                      })
                    }
                  />
                </Field>
              </div>

              <label className={s.palaceRow}>
                <input
                  type="checkbox"
                  className={s.checkbox}
                  checked={!!pair.is_palace_tile}
                  disabled={palaceDisabled}
                  onChange={(e) =>
                    patchPair(i, { is_palace_tile: e.target.checked })
                  }
                />
                <span className={s.palaceLabel}>
                  Memory Palace tile
                  <span className={s.palaceHint}>
                    {palaceDisabled
                      ? "Premium-only — set tier to Premium to enable"
                      : "At most one tile per board can be a palace tile"}
                  </span>
                </span>
              </label>
              {issue.palaceNotPremium && (
                <Warn>
                  Palace tiles must be Premium tier. Switch the tier or clear
                  this flag.
                </Warn>
              )}
              {issue.extraPalace && (
                <Warn>
                  Only one palace tile is allowed per board — this is an extra
                  one.
                </Warn>
              )}

              {(pair.tier === "premium" || pair.explanation) && (
                <Field
                  label="Explanation"
                  hint="Optional — premium “why this pairs” note"
                >
                  <TextArea
                    value={pair.explanation ?? ""}
                    rows={2}
                    onChange={(v) =>
                      patchPair(i, { explanation: v === "" ? undefined : v })
                    }
                    placeholder="A short note shown after a correct match…"
                  />
                </Field>
              )}
            </EditorCard>
          );
        })
      )}

      {value.length > 0 && (
        <div className={s.footer}>
          <SmallButton tone="primary" onClick={addPair} disabled={atCap}>
            + Add pair
          </SmallButton>
          <span className={s.count} data-at-cap={atCap || undefined}>
            {value.length}/{MAX_PAIRS} pair{value.length === 1 ? "" : "s"}
          </span>
        </div>
      )}

      {validation.tooMany && (
        <Warn block>
          Tile Match allows at most {MAX_PAIRS} pairs — remove{" "}
          {value.length - MAX_PAIRS} to stay within the limit.
        </Warn>
      )}
      {validation.multiplePalace && (
        <Warn block>
          Only one tile per board can be flagged as a Memory Palace tile.
        </Warn>
      )}
    </div>
  );
}

/** Inline soft-warning chip. `block` variant spans the board (board-wide rules). */
function Warn({
  children,
  block,
}: {
  children: ReactNode;
  block?: boolean;
}) {
  return (
    <p className={`${s.warn} ${block ? s.warnBlock : ""}`.trim()} role="status">
      <span className={s.warnDot} aria-hidden="true">
        !
      </span>
      <span>{children}</span>
    </p>
  );
}
