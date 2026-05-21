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

/**
 * Boss turn grade result. Mirrors the `tutor.boss_turn` shape plus the
 * Final-Boss adapter metadata. Correctness + damage are server-computed; the
 * client renders HP drama from these fields and never derives the verdict.
 */
export interface BossTurnResult {
  correct: boolean;
  damage_dealt: number;
  boss_response: string;
  hint: string | null;
  score?: number;
  axis_1?: number;
  axis_2?: number;
  axis_1_label?: string;
  axis_2_label?: string;
  done?: boolean;
  // Final-Boss adapter metadata (additive).
  phase?: string;
  boss_type_used?: string;
  grade_band?: string;
  max_hp?: number;
  hint_cost_per_use?: number;
  attempts_used?: number;
  hints_used?: number;
  // Surfaced only on defeat.
  outcome?: string;
  stars?: number;
  outcome_xp?: number;
}

// ---------------------------------------------------------------------------
// Plan-5 dynamic boss — adaptive per-turn generation.
//
// The React BossArena will migrate from the static `bossTurn()` flow (above)
// to this set of endpoints: `/boss/start` opens a session, each turn calls
// `/generate-question` then `/submit-answer`, and the server is authoritative
// for HP / damage / trial accounting. These types mirror Pydantic models in
// server/routes/ai_plan5.py (BossStartResponse, BossGenerateQuestionResponse,
// BossSubmitAnswerResponse).
// ---------------------------------------------------------------------------

/**
 * Response from POST /api/ai/boss/start. Opens a Plan-5 boss session for a
 * (session_id, homework_id) pair. The server's staleness window (~30 min)
 * auto-resumes an existing active session if recent, else spawns a fresh one
 * — so the client can call this unconditionally on boss entry and let the
 * server decide resume-vs-fresh. `weak_topics` / `strong_topics` derive from
 * upstream phase_attempts; `missing_context_flags` surfaces gaps like
 * `no_attempts` / `empty_metrics` for diagnostics.
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
}

/**
 * Response from POST /api/ai/boss/generate-question. The LLM produces one
 * adaptive question targeted to the student's weakest unaddressed skill at
 * the current difficulty tier. `question_text` is student-safe (no answer
 * keys — the server holds them, keyed by `question_id`). `why_this_question`
 * is internal diagnostics; the runtime may surface it or hide it.
 *
 * On retry exhaustion (anti-repetition / language-drift / per-skill floor
 * violation), this endpoint returns HTTP 502. The client must handle that
 * with a user-triggered retry — fallback to static questions is forbidden
 * per Boss Arena spec §10 ("Fixed question pools... defeats the design").
 */
export interface BossGenerateQuestionResponse {
  question_id: string;
  question_text: string;
  target_skill: string;
  difficulty: string;
  why_this_question: string;
  boss_session_id: string;
}

/**
 * Response from POST /api/ai/boss/submit-answer. Server is authoritative:
 * the returned `hp` is the absolute new boss HP (NOT a delta to subtract),
 * `trials_left` is the new trials remaining, and `boss_status` is the
 * canonical terminal-vs-active signal. Per Plan-5 semantics every submission
 * consumes one trial — there is no "retry the same question" path.
 *
 * On terminal status (`won` | `failed`), the optional outcome triplet
 * (`outcome` / `stars` / `outcome_xp`) is populated by compute_boss_outcome.
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
  // Terminal-only — populated when boss_status != "active"
  outcome?: string | null;
  stars?: number | null;
  outcome_xp?: number | null;
}
