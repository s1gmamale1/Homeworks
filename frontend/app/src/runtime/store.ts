// Zustand store for the v2 runtime. Server-authoritative `gateState` is
// hydrated from the API and never set optimistically — the client renders
// gate state, it does not decide it (it has no answers).

import { create } from "zustand";
import type {
  BossGenerateQuestionResponse,
  BossSubmitAnswerResponse,
  CheckAnswerResult,
  GateState,
  HydratePayload,
  IntegrityNudge,
  ReasoningResult,
  ReflectionDebrief,
  ReflectionPerformance,
  TutorTurn,
} from "../shared/types";
import {
  ApiError,
  bossGenerateQuestion,
  bossStart,
  bossSubmitAnswer,
  finalizeReflection,
  getGateState,
  redoReflection,
  submitCheckpoint,
  submitMemoryCheckItem,
  submitReasoning,
  tutorChat,
} from "../shared/api";
import { resolveGameOrder } from "./gameOrder";
import type { AnswerTelemetry } from "./hooks/useAnswerTelemetry";

export type Screen = "hub" | "cbp" | "fc" | "practice" | "reflection";

// The three tutor phases the backend accepts (server ALLOWED_PHASES). Finer
// screen identity rides in `subphase`. screenToTutorPhase() maps the current
// store screen → one of these so the widget always emits a valid phase.
export type TutorPhase = "preview" | "practice" | "boss";

// Map the current runtime screen → the tutor `phase` the backend accepts, plus
// a finer `subphase` hint. Hub/CBP-setup → preview; flashcards/memory/practice
// games → practice; Boss → boss; reflection → practice (subphase "reflection").
// The Boss lives inside the practice screen as the final arc node, so the
// caller passes `inBoss` to disambiguate practice vs. boss on that screen.
export function screenToTutorPhase(
  screen: Screen,
  inBoss: boolean
): { phase: TutorPhase; subphase?: string } {
  // CBP checkpoints are GATED (≥2/3 to pass) — they must use "practice" so the
  // tutor redacts the answer_spec (preview phase passes the answer through
  // unchanged, which would let a student ask the tutor for a gated answer).
  if (screen === "cbp") return { phase: "practice", subphase: "case_based" };
  if (screen === "fc") return { phase: "practice" };
  if (screen === "practice")
    return inBoss
      ? { phase: "boss", subphase: "final-boss" }
      : { phase: "practice" };
  if (screen === "reflection")
    return { phase: "practice", subphase: "reflection" };
  return { phase: "preview" }; // hub
}

// CBP sub-machine:
//   setup → ck0 → lb0 → ck1 → lb1 → ck2 → lb2 → reasoning → sim → feedback.
// The "reasoning" step (open-ended Decision Process Explanation) sits between
// the last learning block and the simulation; it's server-graded but
// non-blocking (a failed pass still advances to sim after a resubmit).
export type CbpSubStage =
  | "setup"
  | "checkpoint"
  | "learningBlock"
  | "reasoning"
  | "sim"
  | "feedback";

// Flashcards/Memory-Check sub-machine (Tile B):
//   flashcards (study the deck) → memoryCheck (graded recall) → result.
// On a failed Memory Check we soft-retry: bounce back to `flashcards` with the
// missed items highlighted, then re-test. Pass/fail is read from the server
// gate (mc.passed) — never decided client-side.
export type FcSubStage = "flashcards" | "memoryCheck" | "result";

// Per-item Memory Check outcome (server-confirmed). `null` = not yet answered.
export type McResult = boolean | null;

const SESSION_KEY = "nets_v2_session_id";

function ensureSessionId(injected: string | null): string {
  if (injected) {
    sessionStorage.setItem(SESSION_KEY, injected);
    return injected;
  }
  const existing = sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const fresh =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  sessionStorage.setItem(SESSION_KEY, fresh);
  return fresh;
}

interface CbpState {
  subStage: CbpSubStage;
  checkpointIndex: number; // 0..2 — current checkpoint
  results: boolean[]; // per-checkpoint correctness (server-confirmed)
  lastFeedback: string | null; // feedback for the just-submitted checkpoint
  lastLearningBlock: string | null; // learning block returned post-submit
  submitting: boolean;
  submitError: string | null;
  // ---- Reasoning step (Decision Process Explanation) ----
  reasoningText: string; // the student's typed reasoning (controlled textarea)
  reasoningResult: ReasoningResult | null; // server verdict (passed/score/feedback)
  reasoningSubmitting: boolean; // POST in flight
  // Advisory anti-cheat nudge from the latest CBP submit (checkpoint OR
  // reasoning). Display-only; NEVER feeds correctness / gate / advance.
  lastNudge: IntegrityNudge | null;
}

interface FcState {
  subStage: FcSubStage;
  // Flashcards study sub-state.
  cardIndex: number; // current card being shown
  viewedCards: number[]; // indices the student has flipped/seen ≥1×
  // Memory Check sub-state.
  itemIndex: number; // current Memory Check item
  results: McResult[]; // per-item correctness (server-confirmed); null = unanswered
  weakItems: number[]; // item indices answered wrong on the last pass (soft-retry)
  scorePct: number; // running %-correct over answered items
  lastFeedback: string | null; // feedback for the just-submitted item
  lastCorrect: boolean | null; // correctness of the just-submitted item
  submitting: boolean;
  submitError: string | null;
  // Advisory anti-cheat nudge from the latest Memory Check submit. Display-only;
  // NEVER feeds correctness / gate / score / advance.
  lastNudge: IntegrityNudge | null;
}

// Practice Arc (F4): a linear rail of game keys → Boss last. The arc tracks
// which node is active; each game self-reports completion via `completeGame`.
// `gameOrder` is resolved once on entry (author order, else derived from gb_*
// arrays) — see gameOrder.ts.
interface PracticeState {
  gameOrder: string[]; // ordered game keys; Boss is the final element
  currentGameIndex: number; // 0-based cursor into gameOrder
  completed: boolean[]; // per-node completion (client progress only)
  finished: boolean; // whole arc cleared (Boss defeated / skipped)
}

// Boss Arena (F4): the mastery peak — DYNAMIC (Plan 5). The SERVER owns
// hp/trials/difficulty: /boss/start derives HP from the grade band, each
// /boss/generate-question fetches the next on-demand question, and
// /boss/submit-answer returns the verdict + ABSOLUTE post-turn state. The
// client mirrors that state, it never computes HP or self-grades. `combo` and
// `hintsUsed` are client-tracked UI affordances (no server hint endpoint
// exists — a hint only reveals the cost, nothing answer-bearing).
export type BossStatus = "intro" | "fighting" | "won" | "lost";

interface BossState {
  bossSessionId: string | null; // server session handle (null until started)
  hp: number; // ABSOLUTE boss HP from the server (drains as hits land)
  maxHp: number;
  trialsLeft: number; // ABSOLUTE attempts remaining from the server
  currentDifficulty: string; // server-adapted difficulty tier
  currentQuestion: BossGenerateQuestionResponse | null; // active question
  questionIndex: number; // 0-based count of questions faced (display only)
  combo: number; // consecutive-correct streak (client meter)
  hintsUsed: number; // local hint-cost tracker (no server hint endpoint)
  loadingQuestion: boolean; // generate-question in flight
  submitting: boolean; // submit-answer in flight (also covers /start)
  lastResult: BossSubmitAnswerResponse | null; // most recent server verdict
  submitError: string | null; // start/submit failure copy
  generateError: string | null; // generate-question failure copy (incl. 502)
  consecutiveGenerateFailures: number; // escalates 502 retry → refresh CTA
  status: BossStatus;
}

// Reflection / Debrief (F5): the closing screen after the Boss. A short
// free-text reflection sub-stage ("prompt") → on submit we POST the answers to
// the finalize endpoint and render the rich SERVER-AUTHORITATIVE debrief
// ("debrief"). The verdict (passed | needs_retry) now comes FROM the server
// response — `enterReflection` keeps only a PROVISIONAL client guess for the
// loading copy; once the debrief returns it is the source of truth.
export type ReflectionStage = "prompt" | "debrief";

interface ReflectionState {
  stage: ReflectionStage;
  prompts: string[]; // 1–2 reflection prompts shown to the student
  answers: string[]; // the student's free-text answers, one per prompt
  debrief: ReflectionDebrief | null; // server-authoritative rich debrief
  performance: ReflectionPerformance | null; // provisional snapshot (loading copy)
  passed: boolean; // SERVER verdict once `debrief` lands; provisional before
  submitting: boolean; // finalize POST in flight
  submitError: string | null;
  retaking: boolean; // redo POST in flight (the retake CTA)
  retakeError: string | null;
}

// Docked tutor (F5): persistent, collapsible help channel across every screen.
// `turns` interleaves student + tutor bubbles. It NEVER holds answer content —
// the server redacts answers, the widget just relays the student message and
// renders the tutor's reply.
interface TutorState {
  open: boolean;
  turns: TutorTurn[];
  sending: boolean;
  sendError: string | null;
}

interface RuntimeState {
  hwId: string;
  sessionId: string;
  payload: HydratePayload | null;
  gateState: GateState | null;
  screen: Screen;
  cbp: CbpState;
  fc: FcState;
  practice: PracticeState;
  boss: BossState;
  reflection: ReflectionState;
  tutor: TutorState;

  // ---- session/boot ----
  initSession: (hwId: string, injectedSessionId: string | null) => void;
  setPayload: (p: HydratePayload) => void;
  setGateState: (g: GateState) => void;
  refreshGateState: () => Promise<void>;

  // ---- navigation ----
  goto: (screen: Screen) => void;
  startCbp: () => void;

  // ---- CBP sub-machine ----
  enterCheckpoint: (index: number) => void;
  submitCheckpointAnswer: (
    index: number,
    answer: string,
    tele?: Partial<AnswerTelemetry>
  ) => Promise<CheckAnswerResult | null>;
  advanceFromLearningBlock: () => void;
  setReasoningText: (text: string) => void;
  submitReasoning: (
    tele?: Partial<AnswerTelemetry>
  ) => Promise<ReasoningResult | null>;
  enterSimulation: () => void;
  finishCbp: () => Promise<void>;
  retryCheckpoint: (index: number) => void;
  // Dismiss the advisory CBP integrity nudge (display-only; no flow effect).
  dismissCbpNudge: () => void;

  // ---- Flashcards / Memory Check sub-machine (Tile B) ----
  enterFlashcards: () => void;
  setCardIndex: (index: number) => void;
  markViewed: (index: number) => void;
  startMemoryCheck: () => void;
  submitMemoryItem: (
    index: number,
    answer: string,
    tele?: Partial<AnswerTelemetry>
  ) => Promise<CheckAnswerResult | null>;
  // Dismiss the advisory Memory Check integrity nudge (display-only; no flow).
  dismissMcNudge: () => void;
  advanceMemoryItem: () => void;
  finishMemoryCheck: () => Promise<void>;
  retryMemoryCheck: () => void;

  // ---- Practice Arc (F4) ----
  enterPracticeArc: () => Promise<void>;
  advanceGame: () => void; // mark current node done, move to next (or finish)
  setGameIndex: (index: number) => void;

  // ---- Boss Arena (F4) — dynamic (Plan 5) ----
  startBoss: () => Promise<void>; // POST /start → load first question → fighting
  loadNextQuestion: () => Promise<void>; // POST /generate-question
  submitBossAnswer: (
    answer: string,
    tele?: Partial<AnswerTelemetry>
  ) => Promise<BossSubmitAnswerResponse | null>;
  requestHint: () => void; // LOCAL cost tracker only (no server hint endpoint)
  retryBoss: () => Promise<void>; // POST /start force_fresh → restart clean

  // ---- Reflection / Debrief (F5) ----
  enterReflection: () => void; // Boss finish → closing screen; seeds prompts + provisional verdict
  setReflectionAnswer: (index: number, value: string) => void;
  submitReflection: () => Promise<ReflectionDebrief | null>; // POST finalize → server-authoritative debrief
  retakeFromReflection: () => Promise<void>; // Needs Retry → POST redo, then fresh Practice Arc

  // ---- Docked tutor (F5) ----
  toggleTutor: (open?: boolean) => void;
  sendTutorMessage: (
    message: string,
    ctx: { questionId?: string; screenContext?: string }
  ) => Promise<void>;
}

const initialCbp: CbpState = {
  subStage: "setup",
  checkpointIndex: 0,
  results: [false, false, false],
  lastFeedback: null,
  lastLearningBlock: null,
  submitting: false,
  submitError: null,
  reasoningText: "",
  reasoningResult: null,
  reasoningSubmitting: false,
  lastNudge: null,
};

const initialFc: FcState = {
  subStage: "flashcards",
  cardIndex: 0,
  viewedCards: [],
  itemIndex: 0,
  results: [],
  weakItems: [],
  scorePct: 0,
  lastFeedback: null,
  lastCorrect: null,
  submitting: false,
  submitError: null,
  lastNudge: null,
};

const initialPractice: PracticeState = {
  gameOrder: [],
  currentGameIndex: 0,
  completed: [],
  finished: false,
};

// Placeholder HP until /boss/start returns the SERVER-derived values. The
// client never decides HP — these are only the pre-start intro-screen defaults
// (the bar isn't shown until status === "fighting", so they're never visible
// as truth). The real hp/max_hp/trials_left arrive from the server response.
const DEFAULT_BOSS_HP = 100;

// Combo bonus kicks in at a 3-correct streak (mirrors the backend's
// COMBO_STREAK_THRESHOLD); the "+20%" chip is shown at combo >= this.
export const COMBO_BONUS_THRESHOLD = 3;

const initialBoss: BossState = {
  bossSessionId: null,
  hp: DEFAULT_BOSS_HP,
  maxHp: DEFAULT_BOSS_HP,
  trialsLeft: 0,
  currentDifficulty: "medium",
  currentQuestion: null,
  questionIndex: 0,
  combo: 0,
  hintsUsed: 0,
  loadingQuestion: false,
  submitting: false,
  lastResult: null,
  submitError: null,
  generateError: null,
  consecutiveGenerateFailures: 0,
  status: "intro",
};

// Default reflection prompts (Flow v2 "What was hardest? Why did you make your
// main decision?"). Authors can override via content_json.reflection.prompts.
const DEFAULT_REFLECTION_PROMPTS = [
  "What was the hardest part, and why?",
  "Why did you make your main decision the way you did?",
] as const;

const initialReflection: ReflectionState = {
  stage: "prompt",
  prompts: [...DEFAULT_REFLECTION_PROMPTS],
  answers: ["", ""],
  debrief: null,
  performance: null,
  passed: false,
  submitting: false,
  submitError: null,
  retaking: false,
  retakeError: null,
};

const initialTutor: TutorState = {
  open: false,
  turns: [],
  sending: false,
  sendError: null,
};

function uid(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `t-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const useRuntimeStore = create<RuntimeState>((set, get) => ({
  hwId: "",
  sessionId: "",
  payload: null,
  gateState: null,
  screen: "hub",
  cbp: { ...initialCbp },
  fc: { ...initialFc },
  practice: { ...initialPractice },
  boss: { ...initialBoss },
  reflection: { ...initialReflection, answers: [...initialReflection.answers] },
  tutor: { ...initialTutor, turns: [] },

  initSession: (hwId, injectedSessionId) =>
    set({ hwId, sessionId: ensureSessionId(injectedSessionId) }),

  setPayload: (p) => set({ payload: p }),
  setGateState: (g) => set({ gateState: g }),

  refreshGateState: async () => {
    const { hwId, sessionId } = get();
    if (!hwId || !sessionId) return;
    const g = await getGateState(hwId, sessionId);
    set({ gateState: g });
  },

  goto: (screen) => set({ screen }),

  startCbp: () => set({ screen: "cbp", cbp: { ...initialCbp } }),

  enterCheckpoint: (index) =>
    set((st) => ({
      cbp: {
        ...st.cbp,
        subStage: "checkpoint",
        checkpointIndex: index,
        lastFeedback: null,
        lastLearningBlock: null,
        lastNudge: null,
        submitError: null,
      },
    })),

  submitCheckpointAnswer: async (index, answer, tele) => {
    const { hwId, sessionId } = get();
    set((st) => ({ cbp: { ...st.cbp, submitting: true, submitError: null } }));
    try {
      const res = await submitCheckpoint(hwId, sessionId, index, answer, tele);
      set((st) => {
        const results = [...st.cbp.results];
        results[index] = res.correct;
        return {
          cbp: {
            ...st.cbp,
            submitting: false,
            results,
            lastFeedback: res.feedback,
            lastLearningBlock: res.learning_block,
            // Advisory only — surfaced beside the learning block, never gates.
            lastNudge: res.integrity_nudge ?? null,
            // Always advance to the learning block so the student reads the
            // teaching beat; the gate decides pass/fail at the end.
            subStage: "learningBlock",
          },
        };
      });
      return res;
    } catch (err) {
      set((st) => ({
        cbp: {
          ...st.cbp,
          submitting: false,
          submitError: (err as Error).message || "Submission failed.",
        },
      }));
      return null;
    }
  },

  advanceFromLearningBlock: () => {
    const { cbp, payload } = get();
    const total = payload?.content_json.case_based_preview?.checkpoints?.length ?? 3;
    const next = cbp.checkpointIndex + 1;
    if (next < total) {
      get().enterCheckpoint(next);
    } else {
      // All checkpoints done. If the homework authored an open-ended reasoning
      // step, go there (server-graded but non-blocking; submitReasoning() then
      // routes onward via enterSimulation()). If not (legacy / no reasoning
      // authored), skip straight to the simulation — never strand the student
      // on an empty reasoning step the server would 404.
      const hasReasoning = Boolean(
        payload?.content_json.case_based_preview?.decision_process_explanation
          ?.prompt
      );
      if (!hasReasoning) {
        get().enterSimulation();
        return;
      }
      set((st) => ({
        cbp: {
          ...st.cbp,
          subStage: "reasoning",
          reasoningResult: null,
          lastNudge: null,
          submitError: null,
        },
      }));
    }
  },

  // Controlled textarea binding for the reasoning step.
  setReasoningText: (text) =>
    set((st) => ({ cbp: { ...st.cbp, reasoningText: text } })),

  // Submit the open-ended reasoning to the server grader. The verdict is the
  // server's (we never self-grade). On a pass we advance to the simulation; on
  // a fail we keep the student on the reasoning step to edit + resubmit (the
  // step teaches but never blocks — the gate is the MCQ checkpoints). Either
  // way the typed text + result stay in state for the feedback panel.
  submitReasoning: async (tele) => {
    const { hwId, sessionId, cbp } = get();
    const text = cbp.reasoningText.trim();
    set((st) => ({
      cbp: { ...st.cbp, reasoningSubmitting: true, submitError: null },
    }));
    try {
      const res = await submitReasoning(hwId, sessionId, text, tele);
      set((st) => ({
        cbp: {
          ...st.cbp,
          reasoningSubmitting: false,
          reasoningResult: res,
          // Advisory only — surfaced beside the reasoning verdict, never gates.
          lastNudge: res.integrity_nudge ?? null,
        },
      }));
      if (res.passed) {
        get().enterSimulation();
      }
      return res;
    } catch (err) {
      set((st) => ({
        cbp: {
          ...st.cbp,
          reasoningSubmitting: false,
          submitError: (err as Error).message || "Couldn't grade your reasoning.",
        },
      }));
      return null;
    }
  },

  enterSimulation: () =>
    set((st) => ({ cbp: { ...st.cbp, subStage: "sim" } })),

  finishCbp: async () => {
    // Refetch the server-authoritative gate, then show the feedback summary.
    await get().refreshGateState();
    set((st) => ({ cbp: { ...st.cbp, subStage: "feedback" } }));
  },

  retryCheckpoint: (index) =>
    set((st) => ({
      cbp: {
        ...st.cbp,
        subStage: "checkpoint",
        checkpointIndex: index,
        lastFeedback: null,
        lastLearningBlock: null,
        lastNudge: null,
        submitError: null,
      },
    })),

  // Advisory only — clearing the nudge changes NO flow/gate/correctness state.
  dismissCbpNudge: () =>
    set((st) => ({ cbp: { ...st.cbp, lastNudge: null } })),

  // ---- Flashcards / Memory Check sub-machine (Tile B) ----

  // Enter the deck from the hub. Fresh start: clear all study + check state.
  enterFlashcards: () => set({ screen: "fc", fc: { ...initialFc } }),

  setCardIndex: (index) => set((st) => ({ fc: { ...st.fc, cardIndex: index } })),

  // Record that a card has been seen ≥1× (the "viewed all" gate that enables
  // "Start Memory Check"). Dedup so the count stays accurate.
  markViewed: (index) =>
    set((st) => {
      if (st.fc.viewedCards.includes(index)) return {};
      return { fc: { ...st.fc, viewedCards: [...st.fc.viewedCards, index] } };
    }),

  // Move from studying into the graded Memory Check. We size `results` to the
  // item count and seed every entry to `null` (unanswered).
  startMemoryCheck: () => {
    const { payload } = get();
    const total = payload?.content_json.memory_check?.items?.length ?? 0;
    set((st) => ({
      fc: {
        ...st.fc,
        subStage: "memoryCheck",
        itemIndex: 0,
        results: Array.from({ length: total }, () => null as McResult),
        scorePct: 0,
        lastFeedback: null,
        lastCorrect: null,
        submitError: null,
      },
    }));
  },

  // Submit one Memory Check item. `answer` is pre-shaped by the component
  // (option index as string, or typed text for fill_blank). Correctness comes
  // straight from the server response — we never self-grade.
  submitMemoryItem: async (index, answer, tele) => {
    const { hwId, sessionId } = get();
    set((st) => ({ fc: { ...st.fc, submitting: true, submitError: null } }));
    try {
      const res = await submitMemoryCheckItem(hwId, sessionId, index, answer, tele);
      set((st) => {
        const results = [...st.fc.results];
        results[index] = res.correct;
        const answered = results.filter((r) => r !== null);
        const correctCount = answered.filter((r) => r === true).length;
        const scorePct = answered.length
          ? Math.round((100 * correctCount) / answered.length)
          : 0;
        return {
          fc: {
            ...st.fc,
            submitting: false,
            results,
            scorePct,
            lastCorrect: res.correct,
            lastFeedback: res.feedback,
            // Advisory only — surfaced beside MC feedback, never gates.
            lastNudge: res.integrity_nudge ?? null,
          },
        };
      });
      return res;
    } catch (err) {
      set((st) => ({
        fc: {
          ...st.fc,
          submitting: false,
          submitError: (err as Error).message || "Submission failed.",
        },
      }));
      return null;
    }
  },

  // Advance to the next unanswered item, or finish the check if none remain.
  // On a soft-retry pass we only walk the previously-weak items.
  advanceMemoryItem: () => {
    const { fc } = get();
    const inRetry = fc.weakItems.length > 0;
    const order = inRetry
      ? fc.weakItems
      : fc.results.map((_, i) => i);
    const pos = order.indexOf(fc.itemIndex);
    const next = order.slice(pos + 1).find((i) => fc.results[i] === null);
    if (next !== undefined) {
      set((st) => ({
        fc: {
          ...st.fc,
          itemIndex: next,
          lastFeedback: null,
          lastCorrect: null,
          lastNudge: null,
        },
      }));
    } else {
      void get().finishMemoryCheck();
    }
  },

  // Advisory only — clearing the nudge changes NO flow/gate/score state.
  dismissMcNudge: () =>
    set((st) => ({ fc: { ...st.fc, lastNudge: null } })),

  // End of a Memory Check pass: refetch the server gate, then show the result.
  // The component reads gateState.mc.passed to branch pass vs. soft-retry.
  finishMemoryCheck: async () => {
    await get().refreshGateState();
    set((st) => ({ fc: { ...st.fc, subStage: "result" } }));
  },

  // Soft-retry: bounce back to the deck with the missed items recorded as
  // `weakItems`, reset those entries to unanswered, and re-test just those.
  retryMemoryCheck: () =>
    set((st) => {
      const weakItems = st.fc.results
        .map((r, i) => (r === false ? i : -1))
        .filter((i) => i >= 0);
      const results = st.fc.results.map((r, i) =>
        weakItems.includes(i) ? (null as McResult) : r
      );
      return {
        fc: {
          ...st.fc,
          subStage: "flashcards",
          weakItems,
          results,
          itemIndex: weakItems[0] ?? 0,
          lastFeedback: null,
          lastCorrect: null,
          lastNudge: null,
          submitError: null,
        },
      };
    }),

  // ---- Practice Arc (F4) ----

  // Enter the arc: resolve the game order ONCE (author order, else derived from
  // gb_* arrays + Boss last), size the completion vector, reset to node 0.
  //
  // BLOCKER #3 (defense-in-depth): re-fetch server-authoritative gate state and
  // only proceed when `practice_arc_unlocked`. If a stale/tampered client tries
  // to enter while still locked, route back to the hub. The REAL enforcement is
  // server-side (the practice-arc check-answer branches 403 on a locked
  // session); this just keeps the UI honest. A network failure fails closed
  // (we don't enter the arc on an unconfirmed gate).
  enterPracticeArc: async () => {
    const { payload, hwId, sessionId } = get();
    if (hwId && sessionId) {
      try {
        const gate = await getGateState(hwId, sessionId);
        set({ gateState: gate });
        if (!gate.practice_arc_unlocked) {
          set({ screen: "hub" });
          return;
        }
      } catch {
        // Could not confirm the gate — fail closed back to the hub rather than
        // optimistically entering a possibly-locked arc.
        set({ screen: "hub" });
        return;
      }
    }
    const gameOrder = resolveGameOrder(payload?.content_json);
    set({
      screen: "practice",
      practice: {
        gameOrder,
        currentGameIndex: 0,
        completed: gameOrder.map(() => false),
        finished: gameOrder.length === 0,
      },
      boss: { ...initialBoss },
    });
  },

  // Mark the current node complete and advance. When the last node clears, the
  // whole arc is finished — and since the Boss is ALWAYS the final node, the
  // Boss finish (defeat or attempts exhausted → "Claim the arc") is what trips
  // this branch, so we route straight into the Reflection / Debrief close. Each
  // game calls this when it self-reports done.
  advanceGame: () => {
    let justFinished = false;
    set((st) => {
      const completed = [...st.practice.completed];
      completed[st.practice.currentGameIndex] = true;
      const next = st.practice.currentGameIndex + 1;
      const finished = next >= st.practice.gameOrder.length;
      justFinished = finished;
      return {
        practice: {
          ...st.practice,
          completed,
          currentGameIndex: finished ? st.practice.currentGameIndex : next,
          finished,
        },
      };
    });
    if (justFinished) get().enterReflection();
  },

  setGameIndex: (index) =>
    set((st) => ({ practice: { ...st.practice, currentGameIndex: index } })),

  // ---- Boss Arena (F4) — dynamic (Plan 5) ----

  // Open the fight. POST /boss/start: the SERVER derives HP from the grade
  // band (the client never decides HP). boss_meta.starting_hp_override is sent
  // as an ADVISORY max_hp only when authored ≥ 10. We store the server's
  // session/hp/trials/difficulty, then load the first question; status flips to
  // "fighting" once a question is in hand. A failed /start surfaces submitError
  // and keeps the intro screen up.
  startBoss: async () => {
    const { hwId, sessionId, payload } = get();
    const meta = payload?.content_json.boss_meta;
    const hpOverride =
      typeof meta?.starting_hp_override === "number" && meta.starting_hp_override >= 10
        ? meta.starting_hp_override
        : undefined;
    set({ boss: { ...initialBoss, submitting: true, submitError: null } });
    try {
      const res = await bossStart({
        sessionId,
        homeworkId: hwId,
        ...(typeof hpOverride === "number" ? { maxHp: hpOverride } : {}),
      });
      set({
        boss: {
          ...initialBoss,
          bossSessionId: res.boss_session_id,
          hp: res.hp,
          maxHp: res.max_hp,
          trialsLeft: res.trials_left,
          currentDifficulty: res.current_difficulty,
          submitting: false,
          // Stay on the intro/loading frame until the first question lands.
          status: "intro",
        },
      });
      await get().loadNextQuestion();
      // Promote to the fighting view only once a question actually exists.
      set((st) =>
        st.boss.currentQuestion
          ? { boss: { ...st.boss, status: "fighting" } }
          : {}
      );
    } catch (err) {
      set((st) => ({
        boss: {
          ...st.boss,
          submitting: false,
          submitError: (err as Error).message || "Couldn't open the arena.",
        },
      }));
    }
  },

  // Fetch the next on-demand question. POST /boss/generate-question. On success
  // we store currentQuestion + reset the failure counter. A 502 (generation
  // retries exhausted) sets generateError and increments
  // consecutiveGenerateFailures so the UI can escalate Try-again → Refresh.
  loadNextQuestion: async () => {
    const { boss } = get();
    if (!boss.bossSessionId) return;
    set((st) => ({
      boss: { ...st.boss, loadingQuestion: true, generateError: null },
    }));
    try {
      const q = await bossGenerateQuestion({ bossSessionId: boss.bossSessionId });
      // NOTE: do NOT overwrite the session `currentDifficulty` from the
      // generated question's own `difficulty` label — the session difficulty is
      // server-owned and arrives only via /boss/start and /boss/submit-answer.
      // The question's difficulty is just the tier the generator picked.
      //
      // We also KEEP `lastResult` here: when a correct/wrong-but-active answer
      // auto-chains the next question, the turn-result card (verdict + coverage)
      // must stay visible alongside the freshly-loaded question. It's cleared
      // only when the next answer is submitted (which sets a new lastResult).
      set((st) => ({
        boss: {
          ...st.boss,
          loadingQuestion: false,
          currentQuestion: q,
          consecutiveGenerateFailures: 0,
        },
      }));
    } catch (err) {
      const is502 = err instanceof ApiError && err.status === 502;
      set((st) => ({
        boss: {
          ...st.boss,
          loadingQuestion: false,
          generateError: is502
            ? "The boss is still thinking — generation timed out."
            : (err as Error).message || "Couldn't load the next question.",
          consecutiveGenerateFailures: st.boss.consecutiveGenerateFailures + 1,
        },
      }));
    }
  },

  // Submit the student's answer. POST /boss/submit-answer — the SERVER grades
  // and returns the verdict + ABSOLUTE post-turn hp/trials/difficulty (the
  // client mirrors them, never computes them). combo increments on a correct
  // answer and resets to 0 on a wrong one. boss_status maps to our status
  // (won → won, failed → lost, active → fighting); on "active" we auto-chain
  // to the next question. The boss NEVER self-grades.
  submitBossAnswer: async (answer, tele) => {
    const { boss } = get();
    if (!boss.bossSessionId || !boss.currentQuestion) return null;
    const questionId = boss.currentQuestion.question_id;
    set((st) => ({ boss: { ...st.boss, submitting: true, submitError: null } }));
    try {
      const res = await bossSubmitAnswer({
        bossSessionId: boss.bossSessionId,
        questionId,
        studentAnswer: answer,
        ...(typeof tele?.client_time_ms === "number"
          ? { clientTimeMs: tele.client_time_ms }
          : {}),
        ...(typeof tele?.paste_detected === "boolean"
          ? { pasteDetected: tele.paste_detected }
          : {}),
      });
      const nextStatus: BossStatus =
        res.boss_status === "won"
          ? "won"
          : res.boss_status === "failed"
            ? "lost"
            : "fighting";
      set((st) => ({
        boss: {
          ...st.boss,
          submitting: false,
          lastResult: res,
          // Absolute server state — the client mirrors, never computes.
          hp: res.hp,
          trialsLeft: res.trials_left,
          currentDifficulty: res.current_difficulty,
          combo: res.is_correct ? st.boss.combo + 1 : 0,
          questionIndex: st.boss.questionIndex + 1,
          status: nextStatus,
        },
      }));
      // Still active → chain to the next question automatically.
      if (nextStatus === "fighting") {
        await get().loadNextQuestion();
      }
      return res;
    } catch (err) {
      set((st) => ({
        boss: {
          ...st.boss,
          submitting: false,
          submitError: (err as Error).message || "Couldn't submit your answer.",
        },
      }));
      return null;
    }
  },

  // Request a hint — LOCAL ONLY. There is no server hint endpoint for the
  // dynamic boss; this never reveals anything answer-bearing. It only bumps the
  // local hintsUsed counter so the UI can show the cost of asking (the backend
  // reads its own hints_used column for damage penalties on its side).
  requestHint: () =>
    set((st) => ({ boss: { ...st.boss, hintsUsed: st.boss.hintsUsed + 1 } })),

  // Restart the fight cleanly. POST /boss/start with force_fresh — the server
  // archives the prior session and spawns a fresh one (trials reset). We reset
  // combo/hints/index and re-load the first question.
  retryBoss: async () => {
    const { hwId, sessionId, payload } = get();
    const meta = payload?.content_json.boss_meta;
    const hpOverride =
      typeof meta?.starting_hp_override === "number" && meta.starting_hp_override >= 10
        ? meta.starting_hp_override
        : undefined;
    set({ boss: { ...initialBoss, submitting: true, submitError: null } });
    try {
      const res = await bossStart({
        sessionId,
        homeworkId: hwId,
        forceFresh: true,
        ...(typeof hpOverride === "number" ? { maxHp: hpOverride } : {}),
      });
      set({
        boss: {
          ...initialBoss,
          bossSessionId: res.boss_session_id,
          hp: res.hp,
          maxHp: res.max_hp,
          trialsLeft: res.trials_left,
          currentDifficulty: res.current_difficulty,
          submitting: false,
          status: "intro",
        },
      });
      await get().loadNextQuestion();
      set((st) =>
        st.boss.currentQuestion
          ? { boss: { ...st.boss, status: "fighting" } }
          : {}
      );
    } catch (err) {
      set((st) => ({
        boss: {
          ...st.boss,
          submitting: false,
          submitError: (err as Error).message || "Couldn't restart the boss.",
        },
      }));
    }
  },

  // ---- Reflection / Debrief (F5) ----

  // Enter the closing screen. We seed the reflection prompts (author override
  // via content_json.reflection.prompts, else the Flow-v2 defaults) and capture
  // a performance snapshot. The Pass | Needs Retry shown here is only a
  // PROVISIONAL client guess (Boss win + passed gates), used purely for the
  // prompt-stage copy + the loading state. The REAL verdict arrives from the
  // finalize endpoint in submitReflection() and overwrites `passed`.
  enterReflection: () => {
    const { payload, gateState, boss, fc } = get();
    const refl = (payload?.content_json.reflection ?? {}) as {
      prompts?: unknown;
    };
    const authored = Array.isArray(refl.prompts)
      ? refl.prompts.filter((p): p is string => typeof p === "string" && p.trim() !== "")
      : [];
    const prompts = authored.length > 0 ? authored.slice(0, 2) : [...DEFAULT_REFLECTION_PROMPTS];

    // Derive Pass: the Boss must be down AND the gate (where present) must pass.
    const bossWon = boss.status === "won";
    const gatesOk = gateState
      ? (gateState.cbp?.passed ?? true) && (gateState.mc?.passed ?? true)
      : true;
    const passed = bossWon && gatesOk;

    // Performance snapshot for the reflection prompt + the rendered score line.
    const correct = gateState?.mc?.correct ?? undefined;
    const total = gateState?.mc?.total ?? undefined;
    const scorePct = gateState?.mc?.score_pct ?? fc.scorePct ?? undefined;
    const weakPhase = bossWon ? undefined : "boss";
    const performance: ReflectionPerformance = {
      ...(typeof correct === "number" ? { correct } : {}),
      ...(typeof total === "number" ? { total } : {}),
      ...(typeof scorePct === "number" ? { score_pct: scorePct } : {}),
      ...(weakPhase ? { weak_phase: weakPhase } : {}),
      passed,
    };

    set({
      screen: "reflection",
      reflection: {
        ...initialReflection,
        stage: "prompt",
        prompts,
        answers: prompts.map(() => ""),
        passed,
        performance,
      },
    });
  },

  setReflectionAnswer: (index, value) =>
    set((st) => {
      const answers = [...st.reflection.answers];
      answers[index] = value;
      return { reflection: { ...st.reflection, answers } };
    }),

  // POST the student's prompt answers to the SERVER-AUTHORITATIVE finalize
  // endpoint and render the rich debrief. The server scores every division,
  // decides the verdict, assigns a band, and composes the narrative — so the
  // returned `verdict` overwrites the provisional `passed` from enterReflection
  // (the client no longer derives Pass | Needs Retry).
  submitReflection: async () => {
    const { hwId, sessionId, reflection } = get();
    set((st) => ({ reflection: { ...st.reflection, submitting: true, submitError: null } }));
    // One trimmed answer per prompt, in prompt order (the backend pairs them
    // back to its own prompt list by index).
    const reflectionAnswers = reflection.prompts.map((_, i) =>
      (reflection.answers[i] ?? "").trim()
    );
    try {
      const debrief = await finalizeReflection({ sessionId, hwId, reflectionAnswers });
      set((st) => ({
        reflection: {
          ...st.reflection,
          submitting: false,
          debrief,
          // SERVER verdict is now the source of truth.
          passed: debrief.verdict === "passed",
          stage: "debrief",
        },
      }));
      return debrief;
    } catch (err) {
      set((st) => ({
        reflection: {
          ...st.reflection,
          submitting: false,
          submitError: (err as Error).message || "Couldn't load your debrief.",
        },
      }));
      return null;
    }
  },

  // Needs Retry → retake = SAME concepts, fresh questions. FIRST POST the redo
  // endpoint (resets server attempt state + reshuffles the pool); only on a
  // confirmed {ok} do we re-enter the Practice Arc (which re-resolves the game
  // order and resets the Boss). A redo failure surfaces `retakeError` and keeps
  // the student on the debrief — we never optimistically enter a stale arc.
  retakeFromReflection: async () => {
    const { hwId, sessionId } = get();
    set((st) => ({ reflection: { ...st.reflection, retaking: true, retakeError: null } }));
    try {
      const res = await redoReflection({ sessionId, hwId });
      if (!res.ok) {
        set((st) => ({
          reflection: {
            ...st.reflection,
            retaking: false,
            retakeError: "Couldn't start the retake. Try again.",
          },
        }));
        return;
      }
      set((st) => ({ reflection: { ...st.reflection, retaking: false } }));
      await get().enterPracticeArc();
    } catch (err) {
      set((st) => ({
        reflection: {
          ...st.reflection,
          retaking: false,
          retakeError: (err as Error).message || "Couldn't start the retake.",
        },
      }));
    }
  },

  // ---- Docked tutor (F5) ----

  toggleTutor: (open) =>
    set((st) => ({ tutor: { ...st.tutor, open: open ?? !st.tutor.open } })),

  // Relay one student message to the live tutor. We map the current screen →
  // a backend-valid phase (+ subphase hint) and forward the optional
  // question_id for context. The widget holds NO answer content — the server
  // rebuilds context and redacts answers; we only render the reply text.
  sendTutorMessage: async (message, ctx) => {
    const trimmed = message.trim();
    if (!trimmed) return;
    const { hwId, sessionId, screen, boss } = get();
    const inBoss = screen === "practice" && boss.status !== "intro";
    const { phase, subphase } = screenToTutorPhase(screen, inBoss);

    const studentTurn: TutorTurn = { id: uid(), role: "student", text: trimmed };
    set((st) => ({
      tutor: {
        ...st.tutor,
        turns: [...st.tutor.turns, studentTurn],
        sending: true,
        sendError: null,
      },
    }));

    try {
      const res = await tutorChat({
        sessionId,
        hwId,
        phase,
        message: trimmed,
        ...(ctx.questionId ? { questionId: ctx.questionId } : {}),
        ...(subphase ? { subphase } : {}),
        ...(ctx.screenContext ? { screenContext: ctx.screenContext } : {}),
      });
      const tutorTurn: TutorTurn = {
        id: uid(),
        role: "tutor",
        text: res.response || "…",
      };
      set((st) => ({
        tutor: { ...st.tutor, turns: [...st.tutor.turns, tutorTurn], sending: false },
      }));
    } catch (err) {
      set((st) => ({
        tutor: {
          ...st.tutor,
          sending: false,
          sendError: (err as Error).message || "Couldn't reach the tutor.",
        },
      }));
    }
  },
}));
