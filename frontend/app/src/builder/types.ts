// Builder (authoring) draft types. These are the v2 net-new authoring shapes —
// the MIRROR of the runtime's StudentSafe* types but WITH the answer fields the
// author needs to set. Redaction lives strictly at the API boundary
// (runtime_redactor server-side); the BUILDER draft intentionally CARRIES the
// answers (option_index expected, text_fuzzy expected) because those are what
// get persisted to the DB. Do NOT add leak guards here — the builder needs
// them.

// ---- answer_spec (authored) ------------------------------------------------
//
// Two shapes the builder authors, per server/schemas/content.py AnswerSpec
// (which is permissive — extra keys propagate):
//   - option_index : {type:"option_index", expected:<idx>, option_count:<n>}
//   - text_fuzzy   : {type:"text_fuzzy",   expected:"<text>", allow_ai_fallback?}

export interface OptionIndexAnswerSpec {
  type: "option_index";
  expected: number; // 0-based index of the correct option
  option_count: number; // how many options exist (validity hint)
}

export interface TextFuzzyAnswerSpec {
  type: "text_fuzzy";
  expected: string;
  allow_ai_fallback?: boolean;
}

export type AuthoredAnswerSpec = OptionIndexAnswerSpec | TextFuzzyAnswerSpec;

// ---- Case-Based Preview (authored) -----------------------------------------

export type CheckpointKind = "identify" | "decide" | "justify";

export interface DraftCaseSetup {
  story: string;
  role: string;
  task: string;
}

export interface DraftCheckpoint {
  kind: CheckpointKind;
  question: string;
  options: string[];
  // option_index answer_spec — author taps the correct option.
  answer_spec: OptionIndexAnswerSpec;
  learning_block: string;
}

export interface DraftFinalSimulation {
  correct_path: string; // redacted server-side; authored here
  wrong_path: string;
}

export interface DraftFeedbackSummary {
  student_understood: string;
  mistake_appeared: string;
  what_to_review: string;
}

export interface DraftCaseBasedPreview {
  title: string;
  case_setup: DraftCaseSetup;
  checkpoints: DraftCheckpoint[]; // exactly 3
  final_simulation: DraftFinalSimulation;
  feedback_summary: DraftFeedbackSummary;
}

// ---- Flashcards + Memory Check (authored) ----------------------------------

export interface DraftFlashcard {
  id?: string;
  term: string;
  def: string;
  hint?: string;
  example?: string;
}

export type MemoryCheckItemType =
  | "mcq"
  | "true_false"
  | "choose_explanation"
  | "fill_blank";

export interface DraftMemoryCheckItem {
  type: MemoryCheckItemType;
  prompt: string;
  flashcard_ref?: string;
  // Present for option types (mcq / true_false / choose_explanation); empty
  // for fill_blank.
  options: string[];
  answer_spec: AuthoredAnswerSpec;
}

export interface DraftMemoryCheck {
  pass_threshold_pct: number;
  items: DraftMemoryCheckItem[];
}

// ---- Boss + Practice Arc (authored) ----------------------------------------

export interface DraftBossMeta {
  name: string;
  starting_hp_override: number; // the runtime + backend max-HP source
}

export interface DraftBossQuestion {
  id?: string;
  q: string;
  ans: string[]; // accepted answers (author-visible)
  dmg: number;
  answer_spec: TextFuzzyAnswerSpec;
}

export interface DraftPracticeArc {
  games: string[]; // ordered game keys; Boss is always appended last at save
}

// ---------------------------------------------------------------------------
// Practice Arc game slices (authored). Each mirrors the authoritative server
// shape in server/schemas/content.py — WITH the answer fields the author sets
// (is_correct / correct / answers / a / ans). Redaction lives strictly at the
// API boundary; the BUILDER draft intentionally carries the answers because
// those are what get persisted to the DB. Field shapes reuse the runtime
// ContentJson conventions (shared/types.ts) so editors + preview agree.
//
// Wave-0 NOTE: these draft slices are the FINAL contract Wave-1 fills. Each
// stub editor below owns exactly one slice (its `value` type). Do not rename
// these keys — they map 1:1 onto content_json gb_* keys.
// ---------------------------------------------------------------------------

// ---- gb_tile_match (TileMatchPair[]) ----
// server: TileMatchPair (content.py ~321). Rules: 0–8 pairs, unique
// id/left/right, ≤1 is_palace_tile (premium-only).
export type TileMatchTier = "basic" | "premium";

export interface DraftTileMatchPair {
  id: string; // stable per-pair id, e.g. "tm_001"
  left: string; // concept side (≤300 chars, non-empty)
  right: string; // definition side (≤300 chars, non-empty)
  tier?: TileMatchTier;
  concept_family?: string;
  subject_family?: string;
  pisa_level?: string; // "L1".."L6"
  difficulty?: "easy" | "medium" | "hard";
  is_palace_tile?: boolean; // premium-only; ≤1 per board
  explanation?: string;
}

// ---- gb_sentence_fill (SentenceFillItem[]) ----
// server: SentenceFillItem (content.py ~357). passage has 1–6 "___" blanks;
// answers.length === blank count. word_bank mode needs ≥1 distractor.
export type SentenceFillMode = "word_bank" | "free_recall";

export interface DraftSentenceFillItem {
  id: string;
  mode: SentenceFillMode;
  passage: string; // contains 1–6 "___" markers
  answers: string[]; // one per blank
  word_bank?: string[]; // required + superset of answers when mode==="word_bank"
  explanations?: (string | null)[];
  tags?: string;
  pisa_level?: string; // "L1".."L5"
  difficulty?: "easy" | "medium" | "hard";
  subject_hint?: string;
  tier?: TileMatchTier;
}

// ---- gb_mystery_box (MysteryBoxItem[]) ----
// server: MysteryBoxItem (content.py ~272). {category, q, a}. `a` is the
// authored answer (stripped server-side before delivery).
export interface DraftMysteryBoxItem {
  category?: string;
  q: string;
  a: string; // authored answer
}

// ---- gb_puzzle_lock (PuzzleLockItem[]) ----
// server: PuzzleLockItem (content.py ~259). Canonical {content, q, a}; the
// builder authors the canonical triple (legacy {text, question, answer}
// aliases are coerced in on load).
export interface DraftPuzzleLockItem {
  content?: string; // tile/clue text
  q: string; // question prompt
  a: string; // authored answer
}

// ---- gb_adaptive_quiz (AdaptiveQuizItem[]) ----
// server: AdaptiveQuizItem (content.py ~236). Same answer_spec contract as
// boss questions. The runtime renders `options` when present (MC), else a text
// input. The author sets `ans` (accepted answers) + an answer_spec.
export interface DraftAdaptiveQuizItem {
  q: string; // display text (server also accepts `prompt`)
  options?: string[]; // optional MC options
  ans: string[]; // accepted answers (author-visible)
  tier?: string; // "EASY" | "MEDIUM" | "HARD"
  tags?: string;
  answer_spec: AuthoredAnswerSpec;
}

// ---- gb_ttt (TttItem[]) + gb_ttt_config (TttConfig) ----
// server: TttItem (content.py ~280) {id, q, correct, distractors[3]};
// TttConfig (content.py ~294). The injector strips correct+distractors before
// the wire format. The author writes correct + exactly 3 distractors.
export interface DraftTttItem {
  id?: string; // auto-assigned "ttt-1"… by injector if absent
  q: string;
  correct: string; // authored correct answer
  distractors: string[]; // 3 distractors
}

export interface DraftTttConfig {
  session_games?: number; // default 3 server-side
  xp_correct?: number;
  xp_draw?: number;
  xp_win?: number;
  xp_strong_session?: number;
  xp_mercy?: number;
  mercy_chance?: number;
}

// ---- gb_memory_palace (MemoryPalaceGame) + gb_memory_palace_config ----
// server: MemoryPalaceGame (content.py ~630) {palaces[], concepts[]};
// MemoryPalaceConfig (content.py ~672). Each palace has 3–7 locations + a
// unique key; concept ids are unique (auto-filled server-side when blank).
export type MemoryPalaceTier = "basic" | "premium";

export interface DraftMemoryPalaceLocation {
  name: string;
  sensory_cue?: string;
  icon?: string;
}

export interface DraftMemoryPalace {
  key: string; // unique per palace
  name: string;
  icon?: string;
  description?: string;
  subject_family?: string; // "bio"|"chem"|"phys"|"math"|"history"|"lang"|"art"|"universal"
  tier?: MemoryPalaceTier;
  locations: DraftMemoryPalaceLocation[]; // 3–7 when present
}

export interface DraftMemoryPalaceConcept {
  id?: string; // auto-filled "mp-c{n}" server-side when blank
  term: string;
  description?: string;
  image_cue?: string;
}

export interface DraftMemoryPalaceGame {
  palaces: DraftMemoryPalace[];
  concepts: DraftMemoryPalaceConcept[];
}

export interface DraftMemoryPalaceConfig {
  concept_count?: number; // default 5 server-side
  min_palace_options?: number; // default 4 server-side
  enable_reverse_recall?: boolean;
  concept_count_grade_overrides?: Record<string, number>;
}

// ---- real_life_challenge (RealLifeChallengeCase) ----
// server: RealLifeChallengeCase (content.py ~507). EXACTLY 5 steps in fixed
// order [decision, info_request, final_decision, concept_select, reasoning].
// is_correct / consequence / acceptable_keywords are author-set + stripped
// server-side. The builder authors the full case (answers included).
export type RLCExpertRole =
  | "fire_inspector"
  | "structural_engineer"
  | "business_consultant"
  | "medical_diagnostician"
  | "agronomist"
  | "teacher"
  | "lawyer"
  | "city_planner"
  | "epidemiologist"
  | "ethicist"
  | "historian"
  | "general";

export type RLCStepKind =
  | "decision"
  | "info_request"
  | "final_decision"
  | "concept_select"
  | "reasoning";

export interface DraftRLCDecisionOption {
  id: string; // "a" | "b" | "c" …
  label: string; // ≤200 chars
  is_correct?: boolean; // exactly 1 correct per decision step
  consequence?: string; // shown after submit
}

export interface DraftRLCConceptChip {
  id: string;
  label: string;
  is_correct?: boolean; // exactly 1 correct chip
}

export interface DraftRLCStep {
  id: string; // "step1".."step5"
  kind: RLCStepKind;
  title: string;
  prompt: string;
  options?: DraftRLCDecisionOption[]; // decision/info_request/final_decision
  concept_chips?: DraftRLCConceptChip[]; // concept_select
  placeholder?: string; // reasoning
  min_chars?: number; // reasoning (default 80)
  acceptable_keywords?: string[]; // reasoning grading anchor (server-only)
}

export interface DraftRealLifeChallenge {
  id: string; // stable case id, e.g. "rlc_001"
  expert_role: RLCExpertRole;
  title: string;
  intro: string;
  pisa_level?: string; // "L1".."L6", default "L4"
  tier?: "basic" | "premium";
  grade_band?: "g1_3" | "g4_6" | "g7_9" | "g10_11";
  variant?: "standard" | "creative_thinking";
  steps: DraftRLCStep[]; // length 5 in the fixed order
}

// ---- reflection (ReflectionPhase) ----
// server: ReflectionPhase (content.py ~403). Free-text closing copy + optional
// author-overridden reflection prompts (store reads content_json.reflection.
// prompts[]).
export interface DraftReflection {
  summary?: string;
  question?: string;
  spaced_rep?: string;
  closing?: string;
  prompts?: string[]; // optional override of the default 2 reflection prompts
}

// ---- meta (Meta) ----
// server: Meta (content.py ~431). Display metadata + editable difficulty/mode.
// `difficulty` and `mode` are builder-editable; the server normalizes mode for
// always-hard subjects.
export interface DraftMeta {
  title?: string;
  subject_display?: string;
  section?: string;
  topic?: string;
  cefr_level?: string;
  difficulty?: string; // "easy" | "medium" | "hard" (free-text tolerated)
  mode?: string; // "easy" | "hard"
}

// ---- Full draft ------------------------------------------------------------

export interface BuilderDraft {
  flow_version: "v2";
  meta: DraftMeta;
  case_based_preview: DraftCaseBasedPreview;
  flashcards: DraftFlashcard[];
  memory_check: DraftMemoryCheck;
  practice_arc: DraftPracticeArc;
  boss_meta: DraftBossMeta;
  boss_questions: DraftBossQuestion[];
  // Practice Arc game slices (each owned by one Wave-1 editor).
  gb_tile_match: DraftTileMatchPair[];
  gb_sentence_fill: DraftSentenceFillItem[];
  gb_mystery_box: DraftMysteryBoxItem[];
  gb_puzzle_lock: DraftPuzzleLockItem[];
  gb_adaptive_quiz: DraftAdaptiveQuizItem[];
  gb_ttt: DraftTttItem[];
  gb_ttt_config: DraftTttConfig;
  gb_memory_palace: DraftMemoryPalaceGame;
  gb_memory_palace_config: DraftMemoryPalaceConfig;
  real_life_challenge: DraftRealLifeChallenge | null;
  reflection: DraftReflection;
}

// ---------------------------------------------------------------------------
// Editor prop contracts (the Wave-0 → Wave-1 handoff).
//
// Every Practice Arc / Reflection / Metadata editor follows the SAME shape: a
// `value` typed to its draft slice + an `onChange(next)` callback. BuilderApp
// wires `value={draft.<slice>}` and `onChange={(next) => updateDraft({...draft,
// <slice>: next})}`. Wave-1 agents implement the bodies WITHOUT changing these
// interfaces. The Ttt + Memory Palace editors also receive their config slice
// (the runtime + injector pair the items with the config).
// ---------------------------------------------------------------------------

export interface TileMatchEditorProps {
  value: DraftTileMatchPair[];
  onChange: (next: DraftTileMatchPair[]) => void;
}

export interface SentenceFillEditorProps {
  value: DraftSentenceFillItem[];
  onChange: (next: DraftSentenceFillItem[]) => void;
}

export interface MysteryBoxEditorProps {
  value: DraftMysteryBoxItem[];
  onChange: (next: DraftMysteryBoxItem[]) => void;
}

export interface PuzzleLockEditorProps {
  value: DraftPuzzleLockItem[];
  onChange: (next: DraftPuzzleLockItem[]) => void;
}

export interface AdaptiveQuizEditorProps {
  value: DraftAdaptiveQuizItem[];
  onChange: (next: DraftAdaptiveQuizItem[]) => void;
}

export interface TttEditorProps {
  value: DraftTttItem[];
  config: DraftTttConfig;
  onChange: (next: DraftTttItem[]) => void;
  onConfigChange: (next: DraftTttConfig) => void;
}

export interface MemoryPalaceEditorProps {
  value: DraftMemoryPalaceGame;
  config: DraftMemoryPalaceConfig;
  onChange: (next: DraftMemoryPalaceGame) => void;
  onConfigChange: (next: DraftMemoryPalaceConfig) => void;
}

export interface RealLifeChallengeEditorProps {
  value: DraftRealLifeChallenge | null;
  onChange: (next: DraftRealLifeChallenge | null) => void;
}

export interface ReflectionEditorProps {
  value: DraftReflection;
  onChange: (next: DraftReflection) => void;
}

export interface MetadataEditorProps {
  value: DraftMeta;
  onChange: (next: DraftMeta) => void;
}

// ---- Homework summary (list/create response slice) -------------------------

export interface HomeworkRow {
  id: string;
  title: string;
  subject: string | null;
  grade: number | string | null;
  mode?: string | null;
  // Surfaced by the list API: "v2" for the React-builder flow, null/absent for
  // legacy v1 homeworks. The dashboard routes on this (v2 → React, v1 → legacy).
  flow_version?: string | null;
  content_json?: Record<string, unknown> | null;
}
