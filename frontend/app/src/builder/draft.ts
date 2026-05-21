// Draft factory + (content_json ⇄ BuilderDraft) converters.
//
// `toContentJson(draft)` produces the persisted v2 content_json (answers
// INCLUDED — correct: the runtime redactor strips them on delivery).
// `fromContentJson(raw)` coerces an UNREDACTED authoring read back into the
// strict draft so an existing v2 homework can be edited. Both are total: a
// missing/partial blob yields a sane empty draft so the editors never crash.

import type {
  AuthoredAnswerSpec,
  BuilderDraft,
  CheckpointKind,
  DraftCheckpoint,
  DraftFlashcard,
  DraftMemoryCheckItem,
  DraftBossQuestion,
  DraftAdaptiveQuizItem,
  DraftMemoryPalace,
  DraftMemoryPalaceConcept,
  DraftMemoryPalaceLocation,
  DraftMysteryBoxItem,
  DraftPuzzleLockItem,
  DraftRLCConceptChip,
  DraftRLCDecisionOption,
  DraftRLCStep,
  DraftSentenceFillItem,
  DraftTileMatchPair,
  DraftTttItem,
  MemoryCheckItemType,
  OptionIndexAnswerSpec,
  RLCExpertRole,
  RLCStepKind,
} from "./types";

const CHECKPOINT_KINDS: CheckpointKind[] = ["identify", "decide", "justify"];

export function optionIndexSpec(
  expected: number,
  optionCount: number
): OptionIndexAnswerSpec {
  return { type: "option_index", expected, option_count: optionCount };
}

function emptyCheckpoint(kind: CheckpointKind): DraftCheckpoint {
  return {
    kind,
    question: "",
    options: ["", "", "", ""],
    answer_spec: optionIndexSpec(0, 4),
    learning_block: "",
  };
}

/** A fresh, valid v2 draft: 3 checkpoints, an empty deck, a starter boss. */
export function emptyDraft(): BuilderDraft {
  return {
    flow_version: "v2",
    meta: {},
    case_based_preview: {
      title: "",
      case_setup: { story: "", role: "", task: "" },
      checkpoints: CHECKPOINT_KINDS.map(emptyCheckpoint),
      final_simulation: { correct_path: "", wrong_path: "" },
      feedback_summary: {
        student_understood: "",
        mistake_appeared: "",
        what_to_review: "",
      },
    },
    flashcards: [],
    memory_check: { pass_threshold_pct: 60, items: [] },
    practice_arc: { games: ["tile_match"] },
    boss_meta: { name: "", starting_hp_override: 100 },
    boss_questions: [],
    // Practice Arc game slices — safe empties so every editor renders without
    // crashing. Empty arrays/objects are OMITTED by toContentJson (see below).
    gb_tile_match: [],
    gb_sentence_fill: [],
    gb_mystery_box: [],
    gb_puzzle_lock: [],
    gb_adaptive_quiz: [],
    gb_ttt: [],
    gb_ttt_config: {},
    gb_memory_palace: { palaces: [], concepts: [] },
    gb_memory_palace_config: {},
    real_life_challenge: null,
    reflection: {},
  };
}

export function emptyFlashcard(): DraftFlashcard {
  return { term: "", def: "", hint: "", example: "" };
}

function flashcardRef(card: DraftFlashcard | undefined, index: number): string {
  const authored = card?.id?.trim();
  if (authored) return authored;
  return `fc_${index + 1}`;
}

export function emptyMemoryItem(
  type: MemoryCheckItemType = "mcq"
): DraftMemoryCheckItem {
  if (type === "fill_blank") {
    return {
      type,
      prompt: "",
      options: [],
      answer_spec: { type: "text_fuzzy", expected: "", allow_ai_fallback: true },
    };
  }
  const options = type === "true_false" ? ["True", "False"] : ["", "", "", ""];
  return {
    type,
    prompt: "",
    options,
    answer_spec: optionIndexSpec(0, options.length),
  };
}

export function emptyBossQuestion(): DraftBossQuestion {
  return {
    q: "",
    ans: [""],
    dmg: 25,
    answer_spec: { type: "text_fuzzy", expected: "", allow_ai_fallback: true },
  };
}

// --------------------------------------------------------------------------- //
// draft → content_json (persist).
// --------------------------------------------------------------------------- //

/** Drop undefined/empty-string optional keys so omitted fields don't clutter. */
function compact<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v === undefined || v === null) continue;
    if (typeof v === "string" && v === "") continue;
    if (Array.isArray(v) && v.length === 0) continue;
    out[k] = v;
  }
  return out;
}

/** Serialize the draft to the persisted content_json (answers included). */
export function toContentJson(draft: BuilderDraft): Record<string, unknown> {
  const cbp = draft.case_based_preview;
  // Boss is ALWAYS the last node of the arc (mastery peak); guarantee it.
  const games = draft.practice_arc.games.filter((g) => g !== "boss");
  games.push("boss");

  const base: Record<string, unknown> = {
    flow_version: "v2",
    case_based_preview: {
      title: cbp.title,
      case_setup: { ...cbp.case_setup },
      checkpoints: cbp.checkpoints.map((ck) => ({
        kind: ck.kind,
        question: ck.question,
        options: [...ck.options],
        answer_spec: { ...ck.answer_spec, option_count: ck.options.length },
        learning_block: ck.learning_block,
      })),
      final_simulation: { ...cbp.final_simulation },
      feedback_summary: { ...cbp.feedback_summary },
    },
    flashcards: draft.flashcards.map((c, i) => ({
      id: flashcardRef(c, i),
      term: c.term,
      def: c.def,
      ...(c.hint ? { hint: c.hint } : {}),
      ...(c.example ? { example: c.example } : {}),
    })),
    memory_check: {
      pass_threshold_pct: draft.memory_check.pass_threshold_pct,
      items: draft.memory_check.items.map((it) =>
        it.type === "fill_blank"
          ? {
              type: it.type,
              prompt: it.prompt,
              ...(it.flashcard_ref ? { flashcard_ref: it.flashcard_ref } : {}),
              answer_spec: { ...it.answer_spec },
            }
          : {
              type: it.type,
              prompt: it.prompt,
              ...(it.flashcard_ref ? { flashcard_ref: it.flashcard_ref } : {}),
              options: [...it.options],
              answer_spec: {
                ...it.answer_spec,
                ...(it.answer_spec.type === "option_index"
                  ? { option_count: it.options.length }
                  : {}),
              },
            }
      ),
    },
    practice_arc: { games },
    boss_meta: {
      name: draft.boss_meta.name,
      starting_hp_override: draft.boss_meta.starting_hp_override,
    },
    boss_questions: draft.boss_questions.map((bq, i) => ({
      id: bq.id || `bq_${i}`,
      q: bq.q,
      ans: bq.ans.filter((a) => a.trim() !== ""),
      dmg: bq.dmg,
      answer_spec: { ...bq.answer_spec },
    })),
  };

  // ---- meta (display + editable difficulty/mode) ----
  // OMIT entirely when nothing authored, so we never write an empty meta block.
  const meta = compact({ ...draft.meta });
  if (Object.keys(meta).length > 0) base.meta = meta;

  // ---- Practice Arc game slices ----
  // Each gb_* key is OMITTED when its array/object is empty so content_json
  // never carries empty game keys. The author's answers are persisted (the
  // server redactor strips them on the student delivery path).
  if (draft.gb_tile_match.length > 0) {
    base.gb_tile_match = draft.gb_tile_match.map((p) =>
      compact({
        id: p.id,
        left: p.left,
        right: p.right,
        tier: p.tier,
        concept_family: p.concept_family,
        subject_family: p.subject_family,
        pisa_level: p.pisa_level,
        difficulty: p.difficulty,
        is_palace_tile: p.is_palace_tile ? true : undefined,
        explanation: p.explanation,
      })
    );
  }

  if (draft.gb_sentence_fill.length > 0) {
    base.gb_sentence_fill = draft.gb_sentence_fill.map((it) =>
      compact({
        id: it.id,
        mode: it.mode,
        passage: it.passage,
        answers: [...it.answers],
        word_bank: it.word_bank ? [...it.word_bank] : undefined,
        explanations: it.explanations ? [...it.explanations] : undefined,
        tags: it.tags,
        pisa_level: it.pisa_level,
        difficulty: it.difficulty,
        subject_hint: it.subject_hint,
        tier: it.tier,
      })
    );
  }

  if (draft.gb_mystery_box.length > 0) {
    base.gb_mystery_box = draft.gb_mystery_box.map((it) =>
      compact({ category: it.category, q: it.q, a: it.a })
    );
  }

  if (draft.gb_puzzle_lock.length > 0) {
    base.gb_puzzle_lock = draft.gb_puzzle_lock.map((it) =>
      compact({ content: it.content, q: it.q, a: it.a })
    );
  }

  if (draft.gb_adaptive_quiz.length > 0) {
    base.gb_adaptive_quiz = draft.gb_adaptive_quiz.map((it) =>
      compact({
        q: it.q,
        options: it.options ? [...it.options] : undefined,
        ans: it.ans.filter((a) => a.trim() !== ""),
        tier: it.tier,
        tags: it.tags,
        answer_spec: { ...it.answer_spec },
      })
    );
  }

  if (draft.gb_ttt.length > 0) {
    base.gb_ttt = draft.gb_ttt.map((it, i) =>
      compact({
        id: it.id || `ttt-${i + 1}`,
        q: it.q,
        correct: it.correct,
        distractors: [...it.distractors],
      })
    );
    const tttConfig = compact({ ...draft.gb_ttt_config });
    if (Object.keys(tttConfig).length > 0) base.gb_ttt_config = tttConfig;
  }

  const palaces = draft.gb_memory_palace.palaces;
  const concepts = draft.gb_memory_palace.concepts;
  if (palaces.length > 0 || concepts.length > 0) {
    base.gb_memory_palace = {
      palaces: palaces.map((p) =>
        compact({
          key: p.key,
          name: p.name,
          icon: p.icon,
          description: p.description,
          subject_family: p.subject_family,
          tier: p.tier,
          locations: p.locations.map((l) =>
            compact({ name: l.name, sensory_cue: l.sensory_cue, icon: l.icon })
          ),
        })
      ),
      concepts: concepts.map((c) =>
        compact({
          id: c.id,
          term: c.term,
          description: c.description,
          image_cue: c.image_cue,
        })
      ),
    };
    const mpConfig = compact({ ...draft.gb_memory_palace_config });
    if (Object.keys(mpConfig).length > 0) base.gb_memory_palace_config = mpConfig;
  }

  if (draft.real_life_challenge) {
    const rlc = draft.real_life_challenge;
    base.real_life_challenge = compact({
      id: rlc.id,
      expert_role: rlc.expert_role,
      title: rlc.title,
      intro: rlc.intro,
      pisa_level: rlc.pisa_level,
      tier: rlc.tier,
      grade_band: rlc.grade_band,
      variant: rlc.variant,
      steps: rlc.steps.map((st) =>
        compact({
          id: st.id,
          kind: st.kind,
          title: st.title,
          prompt: st.prompt,
          options: st.options
            ? st.options.map((o) =>
                compact({
                  id: o.id,
                  label: o.label,
                  is_correct: o.is_correct ? true : undefined,
                  consequence: o.consequence,
                })
              )
            : undefined,
          concept_chips: st.concept_chips
            ? st.concept_chips.map((c) =>
                compact({
                  id: c.id,
                  label: c.label,
                  is_correct: c.is_correct ? true : undefined,
                })
              )
            : undefined,
          placeholder: st.placeholder,
          min_chars: st.min_chars,
          acceptable_keywords: st.acceptable_keywords
            ? [...st.acceptable_keywords]
            : undefined,
        })
      ),
    });
  }

  const reflection = compact({ ...draft.reflection });
  if (Object.keys(reflection).length > 0) base.reflection = reflection;

  return base;
}

// --------------------------------------------------------------------------- //
// content_json → draft (load for editing). Total + defensive.
// --------------------------------------------------------------------------- //

function asStr(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}
function asNum(v: unknown, fallback: number): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}
function asArr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function asObj(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}
/** Optional-string coerce: returns the trimmed-nonempty string, else undefined. */
function optStr(v: unknown): string | undefined {
  return typeof v === "string" && v !== "" ? v : undefined;
}
/** Optional-number coerce: returns the finite number, else undefined. */
function optNum(v: unknown): number | undefined {
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

function coerceAnswerSpec(
  raw: unknown,
  options: string[]
): AuthoredAnswerSpec {
  const a = asObj(raw);
  const type = asStr(a.type);
  if (type === "text_fuzzy" || (!type && options.length === 0)) {
    return {
      type: "text_fuzzy",
      expected: asStr(a.expected),
      allow_ai_fallback: a.allow_ai_fallback !== false,
    };
  }
  // option_index: prefer `expected`, fall back to legacy `option_index`.
  const idx =
    typeof a.expected === "number"
      ? a.expected
      : typeof a.option_index === "number"
      ? a.option_index
      : 0;
  return optionIndexSpec(idx, options.length || asNum(a.option_count, 0));
}

/** Coerce an unredacted authoring read into a strict, editable draft. */
export function fromContentJson(raw: unknown): BuilderDraft {
  const base = emptyDraft();
  const c = asObj(raw);

  // ---- Case-Based Preview ----
  const cbp = asObj(c.case_based_preview);
  const setup = asObj(cbp.case_setup);
  base.case_based_preview.title = asStr(cbp.title);
  base.case_based_preview.case_setup = {
    story: asStr(setup.story),
    role: asStr(setup.role),
    task: asStr(setup.task),
  };
  const rawCheckpoints = asArr(cbp.checkpoints);
  if (rawCheckpoints.length > 0) {
    base.case_based_preview.checkpoints = rawCheckpoints
      .slice(0, 3)
      .map((rck, i) => {
        const ck = asObj(rck);
        const options = asArr(ck.options).map((o) => asStr(o));
        const opts = options.length ? options : ["", "", "", ""];
        const spec = coerceAnswerSpec(ck.answer_spec, opts);
        return {
          kind: (CHECKPOINT_KINDS.includes(asStr(ck.kind) as CheckpointKind)
            ? asStr(ck.kind)
            : CHECKPOINT_KINDS[i % 3]) as CheckpointKind,
          question: asStr(ck.question),
          options: opts,
          answer_spec:
            spec.type === "option_index"
              ? spec
              : optionIndexSpec(0, opts.length),
          learning_block: asStr(ck.learning_block),
        };
      });
    // Pad to exactly 3 so the editor invariant holds.
    while (base.case_based_preview.checkpoints.length < 3) {
      base.case_based_preview.checkpoints.push(
        emptyCheckpoint(CHECKPOINT_KINDS[base.case_based_preview.checkpoints.length])
      );
    }
  }
  const sim = asObj(cbp.final_simulation);
  base.case_based_preview.final_simulation = {
    correct_path: asStr(sim.correct_path),
    wrong_path: asStr(sim.wrong_path),
  };
  const fs = asObj(cbp.feedback_summary);
  base.case_based_preview.feedback_summary = {
    student_understood: asStr(fs.student_understood),
    mistake_appeared: asStr(fs.mistake_appeared),
    what_to_review: asStr(fs.what_to_review),
  };

  // ---- Flashcards ----
  base.flashcards = asArr(c.flashcards).map((rc, i) => {
    const card = asObj(rc);
    return {
      id: asStr(card.id) || `fc_${i + 1}`,
      term: asStr(card.term, asStr(card.front)),
      def: asStr(card.def, asStr(card.definition, asStr(card.back))),
      hint: asStr(card.hint) || undefined,
      example: asStr(card.example) || undefined,
    };
  });

  // ---- Memory Check ----
  const mc = asObj(c.memory_check);
  base.memory_check.pass_threshold_pct = asNum(mc.pass_threshold_pct, 60);
  base.memory_check.items = asArr(mc.items).map((ri) => {
    const item = asObj(ri);
    const type = (
      ["mcq", "true_false", "choose_explanation", "fill_blank"].includes(
        asStr(item.type)
      )
        ? asStr(item.type)
        : "mcq"
    ) as MemoryCheckItemType;
    const options =
      type === "fill_blank" ? [] : asArr(item.options).map((o) => asStr(o));
      return {
        type,
        prompt: asStr(item.prompt),
        flashcard_ref: asStr(item.flashcard_ref) || undefined,
        options,
        answer_spec: coerceAnswerSpec(item.answer_spec, options),
      };
  });

  // ---- Practice Arc ----
  const arc = asObj(c.practice_arc);
  const games = asArr(arc.games)
    .map((g) => asStr(g))
    .filter((g) => g && g !== "boss");
  base.practice_arc.games = games.length ? games : ["tile_match"];

  // ---- Boss ----
  const meta = asObj(c.boss_meta);
  base.boss_meta = {
    name: asStr(meta.name, asStr(c.boss_name)),
    starting_hp_override: asNum(meta.starting_hp_override, 100),
  };
  base.boss_questions = asArr(c.boss_questions).map((rq, i) => {
    const q = asObj(rq);
    const ansList = asArr(q.ans).map((a) => asStr(a));
    const spec = coerceAnswerSpec(q.answer_spec, []);
    return {
      id: asStr(q.id) || `bq_${i}`,
      q: asStr(q.q, asStr(q.prompt)),
      ans: ansList.length ? ansList : [""],
      dmg: asNum(q.dmg, 25),
      answer_spec:
        spec.type === "text_fuzzy"
          ? spec
          : {
              type: "text_fuzzy",
              expected: ansList[0] ?? "",
              allow_ai_fallback: true,
            },
    };
  });

  // ---- meta ----
  const rawMeta = asObj(c.meta);
  base.meta = {
    ...(optStr(rawMeta.title) !== undefined ? { title: optStr(rawMeta.title) } : {}),
    ...(optStr(rawMeta.subject_display) !== undefined
      ? { subject_display: optStr(rawMeta.subject_display) }
      : {}),
    ...(optStr(rawMeta.section) !== undefined ? { section: optStr(rawMeta.section) } : {}),
    ...(optStr(rawMeta.topic) !== undefined ? { topic: optStr(rawMeta.topic) } : {}),
    ...(optStr(rawMeta.cefr_level) !== undefined
      ? { cefr_level: optStr(rawMeta.cefr_level) }
      : {}),
    ...(optStr(rawMeta.difficulty) !== undefined
      ? { difficulty: optStr(rawMeta.difficulty) }
      : {}),
    ...(optStr(c.mode) !== undefined ? { mode: optStr(c.mode) } : {}),
  };

  // ---- gb_tile_match ----
  base.gb_tile_match = asArr(c.gb_tile_match).map((rp, i): DraftTileMatchPair => {
    const p = asObj(rp);
    return {
      id: asStr(p.id) || `tm_${i + 1}`,
      left: asStr(p.left),
      right: asStr(p.right),
      ...(optStr(p.tier) !== undefined ? { tier: optStr(p.tier) as "basic" | "premium" } : {}),
      ...(optStr(p.concept_family) !== undefined
        ? { concept_family: optStr(p.concept_family) }
        : {}),
      ...(optStr(p.subject_family) !== undefined
        ? { subject_family: optStr(p.subject_family) }
        : {}),
      ...(optStr(p.pisa_level) !== undefined ? { pisa_level: optStr(p.pisa_level) } : {}),
      ...(optStr(p.difficulty) !== undefined
        ? { difficulty: optStr(p.difficulty) as "easy" | "medium" | "hard" }
        : {}),
      ...(p.is_palace_tile === true ? { is_palace_tile: true } : {}),
      ...(optStr(p.explanation) !== undefined ? { explanation: optStr(p.explanation) } : {}),
    };
  });

  // ---- gb_sentence_fill ----
  base.gb_sentence_fill = asArr(c.gb_sentence_fill).map(
    (ri, i): DraftSentenceFillItem => {
      const it = asObj(ri);
      const mode: DraftSentenceFillItem["mode"] =
        asStr(it.mode) === "free_recall" ? "free_recall" : "word_bank";
      return {
        id: asStr(it.id) || `sf_${i + 1}`,
        mode,
        passage: asStr(it.passage),
        answers: asArr(it.answers).map((a) => asStr(a)),
        ...(Array.isArray(it.word_bank)
          ? { word_bank: it.word_bank.map((w) => asStr(w)) }
          : {}),
        ...(Array.isArray(it.explanations)
          ? {
              explanations: it.explanations.map((e) =>
                e === null ? null : asStr(e)
              ),
            }
          : {}),
        ...(optStr(it.tags) !== undefined ? { tags: optStr(it.tags) } : {}),
        ...(optStr(it.pisa_level) !== undefined
          ? { pisa_level: optStr(it.pisa_level) }
          : {}),
        ...(optStr(it.difficulty) !== undefined
          ? { difficulty: optStr(it.difficulty) as "easy" | "medium" | "hard" }
          : {}),
        ...(optStr(it.subject_hint) !== undefined
          ? { subject_hint: optStr(it.subject_hint) }
          : {}),
        ...(optStr(it.tier) !== undefined
          ? { tier: optStr(it.tier) as "basic" | "premium" }
          : {}),
      };
    }
  );

  // ---- gb_mystery_box ----
  base.gb_mystery_box = asArr(c.gb_mystery_box).map((ri): DraftMysteryBoxItem => {
    const it = asObj(ri);
    return {
      ...(optStr(it.category) !== undefined ? { category: optStr(it.category) } : {}),
      q: asStr(it.q),
      a: asStr(it.a),
    };
  });

  // ---- gb_puzzle_lock (coerce legacy {text, question, answer} aliases) ----
  base.gb_puzzle_lock = asArr(c.gb_puzzle_lock).map((ri): DraftPuzzleLockItem => {
    const it = asObj(ri);
    const content = asStr(it.content, asStr(it.text));
    return {
      ...(content ? { content } : {}),
      q: asStr(it.q, asStr(it.question)),
      a: asStr(it.a, asStr(it.answer)),
    };
  });

  // ---- gb_adaptive_quiz ----
  base.gb_adaptive_quiz = asArr(c.gb_adaptive_quiz).map(
    (ri): DraftAdaptiveQuizItem => {
      const it = asObj(ri);
      const options = Array.isArray(it.options)
        ? it.options.map((o) => asStr(o))
        : undefined;
      const ans = asArr(it.ans).map((a) => asStr(a));
      const spec = coerceAnswerSpec(it.answer_spec, options ?? []);
      return {
        q: asStr(it.q, asStr(it.prompt)),
        ...(options ? { options } : {}),
        ans: ans.length ? ans : [""],
        ...(optStr(it.tier) !== undefined ? { tier: optStr(it.tier) } : {}),
        ...(optStr(it.tags) !== undefined ? { tags: optStr(it.tags) } : {}),
        answer_spec: spec,
      };
    }
  );

  // ---- gb_ttt (+ gb_ttt_config) ----
  base.gb_ttt = asArr(c.gb_ttt).map((ri, i): DraftTttItem => {
    const it = asObj(ri);
    return {
      ...(optStr(it.id) !== undefined ? { id: optStr(it.id) } : { id: `ttt-${i + 1}` }),
      q: asStr(it.q),
      correct: asStr(it.correct),
      distractors: asArr(it.distractors).map((d) => asStr(d)),
    };
  });
  const rawTttConfig = asObj(c.gb_ttt_config);
  base.gb_ttt_config = {
    ...(optNum(rawTttConfig.session_games) !== undefined
      ? { session_games: optNum(rawTttConfig.session_games) }
      : {}),
    ...(optNum(rawTttConfig.xp_correct) !== undefined
      ? { xp_correct: optNum(rawTttConfig.xp_correct) }
      : {}),
    ...(optNum(rawTttConfig.xp_draw) !== undefined
      ? { xp_draw: optNum(rawTttConfig.xp_draw) }
      : {}),
    ...(optNum(rawTttConfig.xp_win) !== undefined
      ? { xp_win: optNum(rawTttConfig.xp_win) }
      : {}),
    ...(optNum(rawTttConfig.xp_strong_session) !== undefined
      ? { xp_strong_session: optNum(rawTttConfig.xp_strong_session) }
      : {}),
    ...(optNum(rawTttConfig.xp_mercy) !== undefined
      ? { xp_mercy: optNum(rawTttConfig.xp_mercy) }
      : {}),
    ...(optNum(rawTttConfig.mercy_chance) !== undefined
      ? { mercy_chance: optNum(rawTttConfig.mercy_chance) }
      : {}),
  };

  // ---- gb_memory_palace (+ gb_memory_palace_config) ----
  const rawMp = asObj(c.gb_memory_palace);
  base.gb_memory_palace = {
    palaces: asArr(rawMp.palaces).map((rpl): DraftMemoryPalace => {
      const pl = asObj(rpl);
      return {
        key: asStr(pl.key),
        name: asStr(pl.name),
        ...(optStr(pl.icon) !== undefined ? { icon: optStr(pl.icon) } : {}),
        ...(optStr(pl.description) !== undefined
          ? { description: optStr(pl.description) }
          : {}),
        ...(optStr(pl.subject_family) !== undefined
          ? { subject_family: optStr(pl.subject_family) }
          : {}),
        ...(optStr(pl.tier) !== undefined
          ? { tier: optStr(pl.tier) as "basic" | "premium" }
          : {}),
        locations: asArr(pl.locations).map((rl): DraftMemoryPalaceLocation => {
          const l = asObj(rl);
          return {
            name: asStr(l.name),
            ...(optStr(l.sensory_cue) !== undefined
              ? { sensory_cue: optStr(l.sensory_cue) }
              : {}),
            ...(optStr(l.icon) !== undefined ? { icon: optStr(l.icon) } : {}),
          };
        }),
      };
    }),
    concepts: asArr(rawMp.concepts).map((rc): DraftMemoryPalaceConcept => {
      const co = asObj(rc);
      return {
        ...(optStr(co.id) !== undefined ? { id: optStr(co.id) } : {}),
        term: asStr(co.term),
        ...(optStr(co.description) !== undefined
          ? { description: optStr(co.description) }
          : {}),
        ...(optStr(co.image_cue) !== undefined ? { image_cue: optStr(co.image_cue) } : {}),
      };
    }),
  };
  const rawMpConfig = asObj(c.gb_memory_palace_config);
  base.gb_memory_palace_config = {
    ...(optNum(rawMpConfig.concept_count) !== undefined
      ? { concept_count: optNum(rawMpConfig.concept_count) }
      : {}),
    ...(optNum(rawMpConfig.min_palace_options) !== undefined
      ? { min_palace_options: optNum(rawMpConfig.min_palace_options) }
      : {}),
    ...(typeof rawMpConfig.enable_reverse_recall === "boolean"
      ? { enable_reverse_recall: rawMpConfig.enable_reverse_recall }
      : {}),
  };

  // ---- real_life_challenge ----
  const rawRlc = asObj(c.real_life_challenge);
  if (Object.keys(rawRlc).length > 0 && Array.isArray(rawRlc.steps)) {
    base.real_life_challenge = {
      id: asStr(rawRlc.id) || "rlc_001",
      expert_role: (asStr(rawRlc.expert_role) || "general") as RLCExpertRole,
      title: asStr(rawRlc.title),
      intro: asStr(rawRlc.intro),
      ...(optStr(rawRlc.pisa_level) !== undefined
        ? { pisa_level: optStr(rawRlc.pisa_level) }
        : {}),
      ...(optStr(rawRlc.tier) !== undefined
        ? { tier: optStr(rawRlc.tier) as "basic" | "premium" }
        : {}),
      ...(optStr(rawRlc.grade_band) !== undefined
        ? {
            grade_band: optStr(rawRlc.grade_band) as
              | "g1_3"
              | "g4_6"
              | "g7_9"
              | "g10_11",
          }
        : {}),
      ...(optStr(rawRlc.variant) !== undefined
        ? { variant: optStr(rawRlc.variant) as "standard" | "creative_thinking" }
        : {}),
      steps: asArr(rawRlc.steps).map((rs): DraftRLCStep => {
        const st = asObj(rs);
        return {
          id: asStr(st.id),
          kind: (asStr(st.kind) || "decision") as RLCStepKind,
          title: asStr(st.title),
          prompt: asStr(st.prompt),
          ...(Array.isArray(st.options)
            ? {
                options: st.options.map((ro): DraftRLCDecisionOption => {
                  const o = asObj(ro);
                  return {
                    id: asStr(o.id),
                    label: asStr(o.label),
                    ...(o.is_correct === true ? { is_correct: true } : {}),
                    ...(optStr(o.consequence) !== undefined
                      ? { consequence: optStr(o.consequence) }
                      : {}),
                  };
                }),
              }
            : {}),
          ...(Array.isArray(st.concept_chips)
            ? {
                concept_chips: st.concept_chips.map((rc): DraftRLCConceptChip => {
                  const ch = asObj(rc);
                  return {
                    id: asStr(ch.id),
                    label: asStr(ch.label),
                    ...(ch.is_correct === true ? { is_correct: true } : {}),
                  };
                }),
              }
            : {}),
          ...(optStr(st.placeholder) !== undefined
            ? { placeholder: optStr(st.placeholder) }
            : {}),
          ...(optNum(st.min_chars) !== undefined ? { min_chars: optNum(st.min_chars) } : {}),
          ...(Array.isArray(st.acceptable_keywords)
            ? { acceptable_keywords: st.acceptable_keywords.map((k) => asStr(k)) }
            : {}),
        };
      }),
    };
  } else {
    base.real_life_challenge = null;
  }

  // ---- reflection ----
  const rawRefl = asObj(c.reflection);
  base.reflection = {
    ...(optStr(rawRefl.summary) !== undefined ? { summary: optStr(rawRefl.summary) } : {}),
    ...(optStr(rawRefl.question) !== undefined ? { question: optStr(rawRefl.question) } : {}),
    ...(optStr(rawRefl.spaced_rep) !== undefined
      ? { spaced_rep: optStr(rawRefl.spaced_rep) }
      : {}),
    ...(optStr(rawRefl.closing) !== undefined ? { closing: optStr(rawRefl.closing) } : {}),
    ...(Array.isArray(rawRefl.prompts)
      ? { prompts: rawRefl.prompts.map((p) => asStr(p)).filter((p) => p !== "") }
      : {}),
  };

  return base;
}
