// Typed, same-origin fetch client for the v2 runtime JSON API.
// Base is "" (the SPA is served from the same FastAPI origin as the API).
// Every call throws on a non-2xx response so callers can surface error UI.

import type {
  BossGenerateQuestionResponse,
  BossStartResponse,
  BossSubmitAnswerResponse,
  BossTurnResult,
  CheckAnswerResult,
  GateState,
  HydratePayload,
  ReflectionPerformance,
  ReflectionResult,
  TileMatchResult,
  TutorChatResult,
} from "./types";

const BASE = "";

class ApiError extends Error {
  constructor(message: string, public status: number, public url: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch (networkErr) {
    throw new ApiError(
      `Network error reaching ${path}: ${(networkErr as Error).message}`,
      0,
      url
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body — keep statusText */
    }
    throw new ApiError(`${res.status} ${detail}`, res.status, url);
  }

  return (await res.json()) as T;
}

/** GET the redacted, student-safe content_json + metadata for a homework. */
export function hydrate(hwId: string): Promise<HydratePayload> {
  return request<HydratePayload>(
    `/api/runtime/homeworks/${encodeURIComponent(hwId)}`
  );
}

/** GET server-authoritative gate state for the current session. */
export function getGateState(hwId: string, sessionId: string): Promise<GateState> {
  const qs = new URLSearchParams({ session_id: sessionId });
  return request<GateState>(
    `/api/runtime/homeworks/${encodeURIComponent(hwId)}/gate-state?${qs}`
  );
}

/**
 * Submit a Case-Based Preview checkpoint answer.
 * Backend resolves the checkpoint by `item_index` (0-based) from content_json,
 * grades server-side, and returns {correct, feedback, learning_block?}.
 * Correctness is ALWAYS read from the server response, never derived here.
 */
export function submitCheckpoint(
  hwId: string,
  sessionId: string,
  checkpointIndex: number,
  answer: string
): Promise<CheckAnswerResult> {
  return request<CheckAnswerResult>("/api/ai/check-answer", {
    method: "POST",
    body: JSON.stringify({
      phase: "case_based_preview",
      homework_id: hwId,
      session_id: sessionId,
      question_id: `cbp_ck${checkpointIndex}`,
      item_index: checkpointIndex,
      student_answer: answer,
    }),
  });
}

/**
 * Submit a Memory Check item answer.
 * Mirrors {@link submitCheckpoint} exactly but with `phase:"memory_check"`.
 * Backend resolves the item by `item_index` (0-based) from content_json,
 * grades server-side, and returns {correct, feedback, learning_block?}.
 *
 * The caller is responsible for shaping `answer` per item type:
 *   - option types (mcq/true_false/choose_explanation): the tapped option
 *     INDEX as a string (server holds the expected option_index).
 *   - fill_blank: the typed text.
 * Correctness is ALWAYS read from the server response, never derived here.
 */
export function submitMemoryCheckItem(
  hwId: string,
  sessionId: string,
  itemIndex: number,
  answer: string
): Promise<CheckAnswerResult> {
  return request<CheckAnswerResult>("/api/ai/check-answer", {
    method: "POST",
    body: JSON.stringify({
      phase: "memory_check",
      homework_id: hwId,
      session_id: sessionId,
      question_id: `mc_item${itemIndex}`,
      item_index: itemIndex,
      student_answer: answer,
    }),
  });
}

// ---- F4: Practice Arc game submissions ----

/**
 * Submit one Practice Arc game interaction. Generic seam for the GameHost
 * registry: each game maps its own `phase` + payload onto /check-answer, the
 * single grading endpoint. v1 wires `tile-match`; the other 8 games slot in by
 * passing their phase + per-game payload. Correctness is ALWAYS the server's.
 *
 * `payload` is merged verbatim into the POST body alongside the resolved
 * homework_id / session_id, so a game contributes exactly the fields its
 * backend handler reads (e.g. tile-match → {left_id, right_id}).
 */
export function submitGameAnswer<T = unknown>(
  hwId: string,
  sessionId: string,
  phase: string,
  payload: Record<string, unknown>
): Promise<T> {
  return request<T>("/api/ai/check-answer", {
    method: "POST",
    body: JSON.stringify({
      phase,
      homework_id: hwId,
      session_id: sessionId,
      ...payload,
    }),
  });
}

/**
 * Submit a single Tile Match pairing. The client sends the two tapped OPAQUE
 * per-side tokens (`lid` + `rid`) — there is no shared id, so the client never
 * holds the answer key. The server inverts each token to its pair index and
 * grades by `left_index === right_index`, returning
 * {correct, hint?, matched_count, total_pairs, complete, outcome?, …}.
 * The wrong-match `hint` is the LEFT-side text of the picked right tile's TRUE
 * partner — already visible in the DOM, so not a new leak surface.
 *
 * Param names stay `leftId`/`rightId` for call-site stability; they now carry
 * the opaque tokens, not pair ids.
 */
export function submitTileMatch(
  hwId: string,
  sessionId: string,
  leftId: string,
  rightId: string
): Promise<TileMatchResult> {
  return submitGameAnswer<TileMatchResult>(hwId, sessionId, "tile-match", {
    left_id: leftId,
    right_id: rightId,
  });
}

/**
 * Submit one Boss combat turn. Routed through /check-answer phase="final-boss"
 * (NOT the legacy /api/ai/boss-turn): that endpoint resolves the expected
 * answers SERVER-SIDE from content_json.boss_questions by `question_id`, so the
 * redacted client never holds or sends the answer. The response carries
 * server-computed {correct, damage_dealt, boss_response, hint?, ...}. Win/lose
 * is driven by the client's HP cursor (HP is frontend authoritative per the
 * backend adapter), not by a client verdict. The boss NEVER self-grades
 * correctness.
 */
export function bossTurn(
  hwId: string,
  sessionId: string,
  questionId: string,
  studentAnswer: string,
  opts: {
    hpRemaining: number;
    attemptNumber: number;
    bossType?: string;
  }
): Promise<BossTurnResult> {
  return request<BossTurnResult>("/api/ai/check-answer", {
    method: "POST",
    body: JSON.stringify({
      phase: "final-boss",
      homework_id: hwId,
      session_id: sessionId,
      question_id: questionId,
      student_answer: studentAnswer,
      hp_remaining: opts.hpRemaining,
      attempt_number: opts.attemptNumber,
      ...(opts.bossType ? { boss_type: opts.bossType } : {}),
    }),
  });
}

// ---------------------------------------------------------------------------
// Plan-5 dynamic boss — adaptive per-turn flow.
//
// Replaces the static bossTurn() path: each turn is a sequenced call of
// `/boss/start` (once, on entry — server auto-resumes a fresh session if one
// exists), `/boss/generate-question` (every turn, fetches the next adaptive
// question), then `/boss/submit-answer` (grades + drains HP + decrements
// trials). The server is authoritative for HP / damage / trial accounting;
// the client never derives correctness or simulates damage.
//
// Failure mode: `/boss/generate-question` can return HTTP 502 on retry
// exhaustion (anti-repetition / language drift / per-skill difficulty
// floor). The Boss Arena spec §10 forbids fixed-question fallback, so the
// runtime must surface a "Try again" UI on these errors — see PR notes.
// ---------------------------------------------------------------------------

/** Open a Plan-5 boss session. Idempotent within the staleness window. */
export function bossStart(
  sessionId: string,
  homeworkId: string,
  opts?: {
    maxHp?: number;
    trialsLeft?: number;
    initialDifficulty?: string;
    forceFresh?: boolean;
  }
): Promise<BossStartResponse> {
  return request<BossStartResponse>("/api/ai/boss/start", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      homework_id: homeworkId,
      ...(typeof opts?.maxHp === "number" ? { max_hp: opts.maxHp } : {}),
      ...(typeof opts?.trialsLeft === "number" ? { trials_left: opts.trialsLeft } : {}),
      ...(opts?.initialDifficulty ? { initial_difficulty: opts.initialDifficulty } : {}),
      ...(opts?.forceFresh ? { force_fresh: true } : {}),
    }),
  });
}

/**
 * Fetch the next adaptive question for an active boss session.
 *
 * Throws ApiError on 502 — the runtime should catch that specifically and
 * surface a "Try again" affordance (Boss Arena spec §10 forbids falling back
 * to a static question pool). `recentBossPhrases` is forwarded so the
 * generator can vary surface form across turns.
 */
export function bossGenerateQuestion(
  bossSessionId: string,
  recentBossPhrases: string[] = []
): Promise<BossGenerateQuestionResponse> {
  return request<BossGenerateQuestionResponse>("/api/ai/boss/generate-question", {
    method: "POST",
    body: JSON.stringify({
      boss_session_id: bossSessionId,
      recent_boss_phrases: recentBossPhrases,
    }),
  });
}

/**
 * Submit the student's answer for the current boss question.
 *
 * Plan-5 semantics: every submission consumes one trial. There is no
 * "retry the same question" path — `should_retry_same_skill: true` in the
 * response signals that the NEXT generated question should target the same
 * skill, not that the student gets another shot at this one. The server
 * returns absolute `hp` (NOT a delta to subtract from the client's cursor).
 */
export function bossSubmitAnswer(
  bossSessionId: string,
  questionId: string,
  studentAnswer: string
): Promise<BossSubmitAnswerResponse> {
  return request<BossSubmitAnswerResponse>("/api/ai/boss/submit-answer", {
    method: "POST",
    body: JSON.stringify({
      boss_session_id: bossSessionId,
      question_id: questionId,
      student_answer: studentAnswer,
    }),
  });
}

// ---- F5: Reflection / Debrief ----

/**
 * Submit the student's closing reflection and fetch the AI debrief.
 * POST /api/ai/reflection — the server composes a warm coaching paragraph,
 * 2–3 next steps, and a one-line encouragement from the reflection text +
 * the performance snapshot. Pass/score are derived client-side from the gate
 * + performance; the endpoint itself returns coaching prose only.
 */
export function submitReflection(opts: {
  homeworkTitle: string;
  homeworkSummary: string;
  studentReflection: string;
  performance: ReflectionPerformance;
  subject?: string;
  grade?: number;
}): Promise<ReflectionResult> {
  return request<ReflectionResult>("/api/ai/reflection", {
    method: "POST",
    body: JSON.stringify({
      homework_title: opts.homeworkTitle,
      homework_summary: opts.homeworkSummary,
      student_reflection: opts.studentReflection,
      performance: opts.performance,
      ...(opts.subject ? { subject: opts.subject } : {}),
      ...(typeof opts.grade === "number" ? { grade: opts.grade } : {}),
    }),
  });
}

// ---- F5: Live tutor chat (docked widget) ----

/**
 * Send one live-tutor message. POST /api/ai/tutor/chat.
 * The server rebuilds question context + redacts answers SERVER-SIDE
 * (server/services/tutor.py), so the widget NEVER holds, requests, or sends the
 * answer — it only forwards the student's message + the screen-derived `phase`
 * (one of "preview" | "practice" | "boss") and an optional `question_id` for
 * context. `subphase` carries the finer screen label (e.g. "case_based",
 * "reflection") for prompt tuning; `screen_context`/`ui_state` are light hints.
 */
export function tutorChat(opts: {
  sessionId: string;
  hwId: string;
  phase: "preview" | "practice" | "boss";
  message: string;
  questionId?: string;
  subphase?: string;
  screenContext?: string;
  uiState?: Record<string, unknown>;
}): Promise<TutorChatResult> {
  return request<TutorChatResult>("/api/ai/tutor/chat", {
    method: "POST",
    body: JSON.stringify({
      session_id: opts.sessionId,
      hw_id: opts.hwId,
      phase: opts.phase,
      message: opts.message,
      ...(opts.questionId ? { question_id: opts.questionId } : {}),
      ...(opts.subphase ? { subphase: opts.subphase } : {}),
      ...(opts.screenContext ? { screen_context: opts.screenContext } : {}),
      ...(opts.uiState ? { ui_state: opts.uiState } : {}),
    }),
  });
}

export { ApiError };
