// Typed, same-origin fetch client for the v2 runtime JSON API.
// Base is "" (the SPA is served from the same FastAPI origin as the API).
// Every call throws on a non-2xx response so callers can surface error UI.

import type {
  BossGenerateQuestionResponse,
  BossStartResponse,
  BossStateResponse,
  BossSubmitAnswerResponse,
  CheckAnswerResult,
  GateState,
  HydratePayload,
  ReasoningResult,
  ReflectionDebrief,
  ReflectionPerformance,
  ReflectionResult,
  TileMatchResult,
  TutorChatResult,
} from "./types";
import type { AnswerTelemetry } from "../runtime/hooks/useAnswerTelemetry";

const BASE = "";

/**
 * Build the additive telemetry sub-object for a submit request body. Only emits
 * keys that are actually present, so an absent (or empty) `tele` contributes
 * NOTHING to the request — existing callers/tests see an identical body. These
 * are ADVISORY behavioral signals (timing + paste), never a correctness claim.
 */
function teleBody(
  tele?: Partial<AnswerTelemetry>
): Record<string, number | boolean> {
  if (!tele) return {};
  const out: Record<string, number | boolean> = {};
  if (typeof tele.client_time_ms === "number") {
    out.client_time_ms = tele.client_time_ms;
  }
  if (typeof tele.paste_detected === "boolean") {
    out.paste_detected = tele.paste_detected;
  }
  return out;
}

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
  answer: string,
  tele?: Partial<AnswerTelemetry>
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
      // Advisory anti-cheat telemetry — optional, additive, never a correctness
      // claim. Spread only the keys present so absent telemetry changes nothing.
      ...teleBody(tele),
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
  answer: string,
  tele?: Partial<AnswerTelemetry>
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
      ...teleBody(tele),
    }),
  });
}

/**
 * Submit the open-ended Case-Based Preview reasoning ("Decision Process
 * Explanation"). Uses the SAME /api/ai/check-answer endpoint + request() helper
 * as {@link submitCheckpoint}, with phase="case_based_preview_reasoning". The
 * server grades the typed reasoning and returns {passed, score, feedback}.
 * The verdict is ALWAYS the server's — the client never self-grades.
 */
export function submitReasoning(
  hwId: string,
  sessionId: string,
  text: string,
  tele?: Partial<AnswerTelemetry>
): Promise<ReasoningResult> {
  return request<ReasoningResult>("/api/ai/check-answer", {
    method: "POST",
    body: JSON.stringify({
      homework_id: hwId,
      session_id: sessionId,
      phase: "case_based_preview_reasoning",
      reasoning_text: text,
      ...teleBody(tele),
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
 * Read-only snapshot of the per-session Tile Match progress. Used on the
 * TileMatch component mount so the runtime can auto-skip past a Tile Match
 * the server already considers complete (rather than briefly rendering an
 * empty board that flashes wrong on the first click). Returns
 * `total_pairs=0` when no Tile Match is authored on this homework.
 */
export function getTileMatchState(
  hwId: string,
  sessionId: string
): Promise<{
  matched_count: number;
  matched_tokens: { lid: string; rid: string }[];
  total_pairs: number;
  complete: boolean;
}> {
  const qs = new URLSearchParams({ homework_id: hwId, session_id: sessionId });
  return request(`/api/ai/tile-match-state?${qs}`);
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

// ---- F4: Dynamic Boss (Plan 5) — /api/ai/boss/* ----
//
// The dynamic boss owns its own endpoints (NOT the legacy /check-answer
// phase="final-boss" path). The SERVER owns HP/trials/difficulty and grades
// every answer; the client only forwards the student's `student_answer` and
// renders the projected state. NONE of these calls ever send or receive an
// answer/rubric/expected field — the answer-leak guarantee lives in the
// response types (BossGenerateQuestionResponse / BossSubmitAnswerResponse).

/**
 * POST /api/ai/boss/start — open or resume a boss session for this
 * (session_id, homework_id). HP is SERVER-DERIVED from the grade band;
 * `max_hp` here is advisory only (the server may ignore it). `force_fresh`
 * archives any active session and spawns a clean one (used by "Restart boss").
 */
export function bossStart(opts: {
  sessionId: string;
  homeworkId: string;
  maxHp?: number;
  trialsLeft?: number;
  initialDifficulty?: string;
  forceFresh?: boolean;
}): Promise<BossStartResponse> {
  return request<BossStartResponse>("/api/ai/boss/start", {
    method: "POST",
    body: JSON.stringify({
      session_id: opts.sessionId,
      homework_id: opts.homeworkId,
      ...(typeof opts.maxHp === "number" ? { max_hp: opts.maxHp } : {}),
      ...(typeof opts.trialsLeft === "number" ? { trials_left: opts.trialsLeft } : {}),
      ...(opts.initialDifficulty ? { initial_difficulty: opts.initialDifficulty } : {}),
      ...(opts.forceFresh ? { force_fresh: true } : {}),
    }),
  });
}

/**
 * POST /api/ai/boss/generate-question — fetch the next on-demand question.
 * A 502 means generation retries were exhausted; it surfaces as
 * `ApiError.status === 502` so the UI can offer Try again / Refresh.
 * `recentBossPhrases` lets the generator vary surface form.
 */
export function bossGenerateQuestion(opts: {
  bossSessionId: string;
  recentBossPhrases?: string[];
}): Promise<BossGenerateQuestionResponse> {
  return request<BossGenerateQuestionResponse>("/api/ai/boss/generate-question", {
    method: "POST",
    body: JSON.stringify({
      boss_session_id: opts.bossSessionId,
      ...(opts.recentBossPhrases && opts.recentBossPhrases.length
        ? { recent_boss_phrases: opts.recentBossPhrases }
        : {}),
    }),
  });
}

/**
 * POST /api/ai/boss/submit-answer — submit the student's answer for grading.
 * `studentAnswer` is a SINGLE string; for structured Why→How→What questions
 * the caller concatenates the three parts as "Why: …\nHow: …\nWhat: …". The
 * server returns the verdict + ABSOLUTE post-turn hp/trials/difficulty. The
 * client NEVER sends an answer key — only the student's own text.
 */
export function bossSubmitAnswer(opts: {
  bossSessionId: string;
  questionId: string;
  studentAnswer: string;
  // Advisory anti-cheat telemetry — optional, additive, never a correctness
  // claim. Omitted from the body when absent so existing callers are unchanged.
  clientTimeMs?: number;
  pasteDetected?: boolean;
}): Promise<BossSubmitAnswerResponse> {
  return request<BossSubmitAnswerResponse>("/api/ai/boss/submit-answer", {
    method: "POST",
    body: JSON.stringify({
      boss_session_id: opts.bossSessionId,
      question_id: opts.questionId,
      student_answer: opts.studentAnswer,
      ...(typeof opts.clientTimeMs === "number"
        ? { client_time_ms: opts.clientTimeMs }
        : {}),
      ...(typeof opts.pasteDetected === "boolean"
        ? { paste_detected: opts.pasteDetected }
        : {}),
    }),
  });
}

/** POST /api/ai/boss/state — projected session state (no answer keys). */
export function bossState(bossSessionId: string): Promise<BossStateResponse> {
  return request<BossStateResponse>("/api/ai/boss/state", {
    method: "POST",
    body: JSON.stringify({ boss_session_id: bossSessionId }),
  });
}

/** POST /api/ai/boss/give-up — abandon the session; returns projected state. */
export function bossGiveUp(bossSessionId: string): Promise<BossStateResponse> {
  return request<BossStateResponse>("/api/ai/boss/give-up", {
    method: "POST",
    body: JSON.stringify({ boss_session_id: bossSessionId }),
  });
}

// ---- F5: Reflection / Debrief (v2 — SERVER-AUTHORITATIVE) ----

/**
 * Finalize the journey and fetch the rich, server-authoritative debrief.
 * POST /api/runtime/reflection/finalize — the server scores every division,
 * decides the verdict (passed | needs_retry), assigns a band, and composes the
 * AI narrative + strong/weak points + next steps. The verdict here is the
 * SOURCE OF TRUTH — the client no longer derives Pass | Needs Retry.
 *
 * `reflectionAnswers` is the student's free-text prompt answers (one per prompt,
 * in order), forwarded so the narrative can reference what they wrote.
 */
export function finalizeReflection(opts: {
  sessionId: string;
  hwId: string;
  reflectionAnswers: string[];
}): Promise<ReflectionDebrief> {
  return request<ReflectionDebrief>("/api/runtime/reflection/finalize", {
    method: "POST",
    body: JSON.stringify({
      session_id: opts.sessionId,
      hw_id: opts.hwId,
      reflection_answers: opts.reflectionAnswers,
    }),
  });
}

/**
 * Kick off a retake on a `needs_retry` verdict — same concepts, fresh
 * questions. POST /api/runtime/reflection/redo resets the server-side attempt
 * state and reshuffles the question pool; the client then re-enters the
 * Practice Arc (which re-resolves the game order). Returns {ok, reshuffled}.
 */
export function redoReflection(opts: {
  sessionId: string;
  hwId: string;
}): Promise<{ ok: boolean; reshuffled: boolean }> {
  return request<{ ok: boolean; reshuffled: boolean }>(
    "/api/runtime/reflection/redo",
    {
      method: "POST",
      body: JSON.stringify({ session_id: opts.sessionId, hw_id: opts.hwId }),
    }
  );
}

/**
 * Re-fetch a previously-finalized debrief for resume (e.g. a refresh on the
 * debrief screen). GET /api/runtime/reflection/{hw_id}?session_id= → the same
 * ReflectionDebrief the finalize call returned.
 */
export function getReflection(
  hwId: string,
  sessionId: string
): Promise<ReflectionDebrief> {
  const qs = new URLSearchParams({ session_id: sessionId });
  return request<ReflectionDebrief>(
    `/api/runtime/reflection/${encodeURIComponent(hwId)}?${qs}`
  );
}

// ---- F5: Reflection / Debrief (LEGACY v1) ----

/**
 * LEGACY: submit the student's closing reflection and fetch coaching prose.
 * POST /api/ai/reflection — the server composes a warm coaching paragraph,
 * 2–3 next steps, and a one-line encouragement from the reflection text +
 * the performance snapshot. Pass/score were derived client-side. The v2 flow
 * uses {@link finalizeReflection} instead; this stays for back-compat.
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

// ---- Anti-cheat: advisory nudge acknowledgement ----

/**
 * Fire-and-forget advisory signal: student responded to an integrity nudge.
 *
 * CONTRACT (read before calling):
 *   • NEVER await this in a way that gates, delays, or conditions UI flow.
 *   • The backend receives `nudge_response` and early-returns {advisory:true}
 *     WITHOUT grading. The client MUST ignore the response entirely.
 *   • Errors are swallowed — a dropped signal is fine; the UX must not break.
 *   • No student_answer is sent — this is purely a behavioural advisory ping.
 */
export function acknowledgeNudge(
  hwId: string,
  sessionId: string,
  phase: string,
  choice: string
): void {
  // Intentionally NOT awaited. We swallow both network errors and the response
  // body — the server returns {advisory:true} which the client must never read
  // for correctness, gate, or flow decisions.
  void fetch("/api/ai/check-answer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      phase,
      homework_id: hwId,
      session_id: sessionId,
      nudge_response: choice,
    }),
  }).catch(() => {
    /* advisory — dropped signals are acceptable */
  });
}

export { ApiError };
