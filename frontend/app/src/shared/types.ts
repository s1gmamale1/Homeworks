// Runtime API types. The redacted hydration payload NEVER carries answer
// fields — `StudentSafeCheckpoint` is a type-level leak guard so a regression
// can't smuggle `answer_spec` / `correct` into the client model.

export interface HydratePayload {
  id: string;
  title: string;
  subject: string | null;
  grade: string | number | null;
  lang: string | null;
  flow_version: string;
  content_json: ContentJson;
}

export interface ContentJson {
  flow_version?: string;
  case_based_preview?: CaseBasedPreview;
  flashcards?: Flashcard[];
  memory_check?: MemoryCheck;
  // F4 — Practice Arc spine. `practice_arc.games[]` is an optional ordered
  // list of game keys ("tile_match", "boss", …); when absent the arc derives
  // its order from whichever gb_* arrays exist + boss last.
  practice_arc?: PracticeArc;
  // Opaque per-side tile-match payload — the server replaces the leaky
  // `[{id,left,right}]` pair list with independently-shuffled token columns so
  // the DOM can't recover the pairing. See TileMatchPayload.
  gb_tile_match?: TileMatchPayload;
  boss_questions?: BossQuestion[];
  boss_meta?: BossMeta;
  // Other gb_* arrays land as the remaining 8 games ship — kept open.
  [key: string]: unknown;
}

export type CheckpointKind = "identify" | "decide" | "justify";

/**
 * Type-level answer-leak guard. The redacted hydration payload may only carry
 * display fields. `answer_spec`, `correct`, `expected` etc. are typed as
 * `never` so any attempt to read them is a compile error — the client model
 * literally cannot hold an answer.
 */
export interface StudentSafeCheckpoint {
  kind: CheckpointKind;
  question: string;
  options: string[];
  // Explicit leak guards — these must never be present client-side.
  answer_spec?: never;
  correct?: never;
  expected?: never;
  ans?: never;
  accepted_answers?: never;
  learning_block?: never; // arrives via the submit response, not hydration.
}

export type Checkpoint = StudentSafeCheckpoint;

export interface CaseSetup {
  story?: string;
  role?: string;
  task?: string;
}

export interface FinalSimulation {
  wrong_path?: string;
  visual_description_or_svg?: string;
  // correct_path is redacted server-side — surfaced only via submit feedback.
  correct_path?: never;
}

export interface FeedbackSummary {
  student_understood?: string;
  mistake_appeared?: string;
  what_to_review?: string;
  [key: string]: unknown;
}

export interface CaseBasedPreview {
  title?: string;
  metadata?: Record<string, unknown>;
  source_extraction?: Record<string, unknown>;
  case_setup?: CaseSetup;
  checkpoints?: Checkpoint[];
  final_simulation?: FinalSimulation;
  feedback_summary?: FeedbackSummary;
  // Optional open-ended "Decision Process Explanation" step. Only the student-
  // safe fields survive hydration (the keyword buckets / rubric / pass_score are
  // stripped server-side). When absent, the runtime skips the reasoning step.
  decision_process_explanation?: DecisionProcessExplanation;
}

/** Student-safe view of the reasoning step — prompt + min length only. */
export interface DecisionProcessExplanation {
  prompt?: string;
  min_chars?: number;
}

// ---- Flashcards (Tile B study deck — display-only, no answer fields) ----

/**
 * A single flashcard from the redacted hydration payload. `front`/`back` are
 * the two faces; the optional fields are coaching hints. There are NO answer
 * fields here — flashcards are study material, graded recall happens in the
 * Memory Check below. The leak guards mirror StudentSafeCheckpoint.
 */
export interface Flashcard {
  id?: string;
  // Canonical frozen content shape uses {term, def}; front/back are accepted
  // as aliases. The renderer reads term→front, def→back with fallback.
  term?: string;
  def?: string;
  definition?: string;
  front?: string;
  back?: string;
  hint?: string;
  example?: string;
  type?: string;
  // Explicit leak guards — flashcards are never graded, so no answer fields.
  answer_spec?: never;
  correct?: never;
  expected?: never;
}

export type MemoryCheckItemType =
  | "mcq"
  | "true_false"
  | "choose_explanation"
  | "fill_blank";

/**
 * A Memory Check item. Option-bearing types (`mcq` / `true_false` /
 * `choose_explanation`) carry `options`; `fill_blank` omits them and expects a
 * typed answer. `answer_spec` is redacted server-side — correctness is ALWAYS
 * read from the /check-answer response, never derived here.
 */
export interface MemoryCheckItem {
  type: MemoryCheckItemType;
  prompt: string;
  options?: string[];
  // Explicit leak guard — the redactor strips this subtree before delivery.
  answer_spec?: never;
}

export interface MemoryCheck {
  pass_threshold_pct?: number;
  items: MemoryCheckItem[];
}

// ---- Gate state (server-authoritative; the client renders, never decides) ----

export interface CbpGate {
  passed: boolean;
  checkpoints_correct: number;
  checkpoints_total: number;
  threshold?: number;
}

export interface McGate {
  passed: boolean;
  score_pct: number;
  correct?: number;
  total?: number;
  threshold_pct: number;
}

export interface GateState {
  cbp: CbpGate;
  mc: McGate;
  practice_arc_unlocked: boolean;
}

// ---- Per-interaction submit ----

export interface CheckAnswerResult {
  correct: boolean;
  feedback: string;
  learning_block: string | null;
}

/**
 * Result of grading the open-ended "Decision Process Explanation" step.
 * The student types their reasoning (which concept applies, why this method,
 * what mistake to avoid); the backend grades it server-side and returns a
 * pass/fail verdict, a `score` (integer 0..100, a blend of AI judgment +
 * deterministic keyword coverage), and coaching feedback. Correctness is ALWAYS
 * read from the server — the client never self-grades. Non-blocking: on
 * `passed:false` the student may edit + resubmit, then advance regardless.
 */
export interface ReasoningResult {
  passed: boolean;
  score: number;
  feedback: string;
}

// ---- F4: Practice Arc spine ----

/**
 * Ordered Practice Arc descriptor. `games` is a list of game KEYS — the same
 * keys the GameHost registry maps to components ("tile_match", "boss", …).
 * Optional: when absent, PracticeArc derives the order from the gb_* arrays
 * present on content_json, with the Boss always last.
 */
export interface PracticeArc {
  games?: string[];
  title?: string;
  intro?: string;
  [key: string]: unknown;
}

/**
 * One LEFT-column tile in the redacted hydration payload. `lid` is an opaque
 * per-side token (HMAC, server-held mapping) — it does NOT reveal which right
 * tile it pairs with. `text` is the concept label.
 */
export interface TileMatchLeft {
  lid: string;
  text: string;
}

/**
 * One RIGHT-column tile. `rid` is an opaque per-side token; `text` is the
 * meaning/definition. There is deliberately NO field linking a right to its
 * left — the pairing lives only on the server.
 */
export interface TileMatchRight {
  rid: string;
  text: string;
}

/**
 * The student-safe tile-match payload. The server replaced the leaky
 * `[{id,left,right}]` pair list (both sides shared one `id`, so the DOM encoded
 * every answer) with two independently-shuffled token columns. The client
 * submits a tapped `lid` + `rid`; the server inverts the tokens to pair indices
 * and grades by `left_index === right_index`. The client never decides
 * correctness, and no shared id is ever present to recover the mapping.
 */
export interface TileMatchPayload {
  lefts: TileMatchLeft[];
  rights: TileMatchRight[];
  // Leak guards — the legacy pairing shape must never reappear.
  id?: never;
  left?: never;
  right?: never;
  explanation?: never;
}

/** Per-pair Tile Match grade result (server-authoritative). */
export interface TileMatchResult {
  correct: boolean;
  hint: string | null;
  explanation: string | null;
  matched_count: number;
  total_pairs: number;
  complete: boolean;
  outcome: string | null;
  timer?: { remaining_seconds: number; delta_seconds: number };
  xp?: Record<string, number>;
  completion_bonus_xp?: number;
}

/**
 * A Boss question from the redacted hydration payload. `q`/`prompt` is the
 * display text; `id` is the key the server resolves the expected answer by.
 * Answer fields (`ans`, `accepted_answers`, `answer_spec`) are stripped server
 * side — the React boss NEVER self-grades, it submits the student's answer
 * with the question_id and reads correctness/damage from the response.
 */
export interface BossQuestion {
  id?: string;
  q?: string;
  prompt?: string;
  hint?: string;
  dmg?: number;
  tags?: string;
  // Leak guards — these never reach the client.
  ans?: never;
  accepted_answers?: never;
  answer_spec?: never;
}

// ---- F5: Reflection / Debrief + docked Tutor ----

/**
 * Performance snapshot sent to the reflection endpoint. Mirrors the backend's
 * `performance` dict shape ({correct, total, time_minutes, weak_phase}); all
 * fields optional so a partial journey still produces a debrief.
 */
export interface ReflectionPerformance {
  correct?: number;
  total?: number;
  time_minutes?: number;
  weak_phase?: string;
  passed?: boolean;
  score_pct?: number;
  [key: string]: unknown;
}

/**
 * AI debrief returned by POST /api/ai/reflection. The server produces a warm
 * coaching `feedback` paragraph, 2–3 concrete `next_steps`, and a one-line
 * `encouragement`. `ai_unavailable` flags the canned fallback. Pass/score are
 * NOT decided here — the client derives Pass | Needs Retry from gate/perf.
 */
export interface ReflectionResult {
  feedback: string;
  next_steps: string[];
  encouragement: string;
  ai_unavailable?: boolean;
}

/**
 * One live-tutor turn. `id` keys the React list; `role` distinguishes the
 * student bubble from the tutor bubble. The widget NEVER stores or requests
 * answer content — turns are help text only (the server redacts answers).
 */
export interface TutorTurn {
  id: string;
  role: "student" | "tutor";
  text: string;
}

/**
 * Response from POST /api/ai/tutor/chat. `response` is the tutor's reply text;
 * `message_id` is the persisted turn id (null on the homework-failed branch).
 * Warning fields ride along so a host could surface a chip — the widget reads
 * only `response`.
 */
export interface TutorChatResult {
  response: string;
  message_id: number | null;
  warning_level?: number;
  cumulative_deduction_pct?: number;
  homework_failed?: boolean;
}

export interface BossMeta {
  boss_type?: "sub" | "big" | "mythical";
  grade_band?: string;
  attempts_max?: number | null;
  starting_hp_override?: number;
  name?: string;
  intro?: string;
  [key: string]: unknown;
}

// ---- Dynamic Boss (Plan 5) — /api/ai/boss/* contract ----
//
// These mirror the Pydantic models in server/routes/ai_plan5.py 1:1. The
// dynamic boss flow REPLACES the static content_json.boss_questions turn loop:
// the server owns HP/trials/difficulty, generates each question on demand, and
// grades server-side. The client NEVER holds an answer, rubric, or expected
// value — the response types below carry only prompt + projected-state fields,
// guarded by `never` so a regression can't smuggle an answer key in.

/**
 * POST /api/ai/boss/start → opens (or resumes) a boss session. HP is
 * SERVER-DERIVED from the homework's grade band; the client never decides it.
 */
export interface BossStartResponse {
  boss_session_id: string;
  hp: number;
  max_hp: number;
  trials_left: number;
  current_difficulty: string;
  weak_topics: string[];
  strong_topics: string[];
  missing_context_flags: string[];
  // Leak guards — /start never returns an answer key.
  expected?: never;
  expected_answer?: never;
  rubric?: never;
  answer?: never;
}

/**
 * POST /api/ai/boss/generate-question → the next on-demand question. The
 * structured Why→How→What prompt (`scenario`/`why`/`how`/`what`) may be empty
 * for legacy questions; fall back to `question_text`. NEVER any answer/rubric.
 */
export interface BossGenerateQuestionResponse {
  question_id: string;
  question_text: string;
  // Structured prompt parts — PROMPT text only, safe to render. May be "".
  scenario?: string;
  why?: string;
  how?: string;
  what?: string;
  target_skill: string;
  difficulty: string;
  why_this_question: string;
  boss_session_id: string;
  // Leak guards — the generated question never carries its own answer.
  expected?: never;
  expected_answer?: never;
  rubric?: never;
  answer?: never;
  accepted_answers?: never;
  answer_spec?: never;
  correct?: never;
}

/**
 * POST /api/ai/boss/submit-answer → server-graded verdict + absolute state.
 * `hp`/`trials_left`/`current_difficulty` are ABSOLUTE post-turn values (the
 * client mirrors them, it does not compute them). `coverage` carries the
 * STUDENT's own per-axis why/how/what scores (NOT answer-bearing) for the
 * coverage bars. `outcome`/`stars`/`outcome_xp` populate only on terminal
 * status transitions.
 */
export interface BossSubmitAnswerResponse {
  is_correct: boolean;
  score: number;
  confidence: number;
  feedback: string;
  damage: number;
  hp: number;
  trials_left: number;
  current_difficulty: string;
  boss_status: "active" | "won" | "failed";
  should_retry_same_skill: boolean;
  misconception_tags: string[];
  outcome?: string | null;
  stars?: number | null;
  outcome_xp?: number | null;
  coverage?: { why: number; how: number; what: number } | null;
  // Leak guards — the verdict reveals feedback, not the expected answer.
  expected?: never;
  expected_answer?: never;
  rubric?: never;
  answer?: never;
}

/**
 * POST /api/ai/boss/state and /api/ai/boss/give-up → projected session state
 * (no answer keys). `current_question` mirrors the active question's prompt
 * parts on resume.
 */
export interface BossStateResponse {
  boss_session_id: string;
  session_id: string;
  homework_id: string;
  status: string;
  hp: number;
  max_hp: number;
  trials_left: number;
  current_difficulty: string;
  current_question_id?: string | null;
  asked_question_ids?: string[];
  weak_topics?: string[];
  strong_topics?: string[];
  current_question?: {
    question_id: string;
    question_text: string;
    scenario?: string;
    why?: string;
    how?: string;
    what?: string;
    difficulty: string;
    target_skill: string;
  } | null;
  // Leak guards.
  expected?: never;
  expected_answer?: never;
  rubric?: never;
}
