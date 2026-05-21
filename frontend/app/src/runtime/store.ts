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
  ReflectionPerformance,
  ReflectionResult,
  TutorTurn,
} from "../shared/types";
import {
  ApiError,
  bossGenerateQuestion,
  bossStart,
  bossSubmitAnswer,
  getGateState,
  submitCheckpoint,
  submitMemoryCheckItem,
  submitReflection,
  tutorChat,
} from "../shared/api";
import { resolveGameOrder } from "./gameOrder";

export type Screen = "hub" | "cbp" | "fc" | "gate" | "practice" | "reflection";

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
  if (screen === "gate") return { phase: "preview" };
  if (screen === "practice")
    return inBoss
      ? { phase: "boss", subphase: "final-boss" }
      : { phase: "practice" };
  if (screen === "reflection")
    return { phase: "practice", subphase: "reflection" };
  return { phase: "preview" }; // hub
}

// CBP sub-machine: setup → ck0 → lb0 → ck1 → lb1 → ck2 → lb2 → sim → feedback.
export type CbpSubStage = "setup" | "checkpoint" | "learningBlock" | "sim" | "feedback";

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

// Boss Arena (F4): the mastery peak. PLAN-5 dynamic boss — questions are
// generated per-turn by Kimi against the student's adaptive context; HP /
// damage / trials / current_difficulty are all SERVER-AUTHORITATIVE (the
// /boss/submit-answer response carries the absolute new HP, NOT a delta to
// subtract). status drives intro / fighting / won / lost rendering.
//
// Lifecycle: startBoss → POST /boss/start (server picks resume vs fresh via
// the 30-min staleness window) → loadNextQuestion → POST /boss/generate-question
// → bossAnswer → POST /boss/submit-answer → auto-chain to loadNextQuestion if
// boss_status is still "active". 502 on /generate-question (anti-rep / floor /
// drift retry exhaustion) is surfaced as `generateError` for the UI to render a
// "Try again" CTA per Boss Arena spec §10 (forbids fixed-question fallback).
export type BossStatus = "intro" | "fighting" | "won" | "lost";

interface BossState {
  // Plan-5 server session — opened by /boss/start, drives every subsequent call.
  bossSessionId: string | null;
  hp: number; // server-authoritative absolute HP (NOT a client-mutated cursor)
  maxHp: number;
  trialsLeft: number; // server-tracked trials remaining
  currentDifficulty: string; // server's current difficulty tier (e.g. "easy" | "medium" | "hard")
  currentQuestion: BossGenerateQuestionResponse | null; // server-generated; null while loading
  questionIndex: number; // local turn counter for display only (no longer indexes a static array)
  attemptNumber: number; // legacy — Plan-5 has no "retry same Q"; PR-3 removes from UI
  status: BossStatus;
  lastResult: BossSubmitAnswerResponse | null; // most recent server submit (is_correct/damage/hp/outcome…)
  submitting: boolean; // bossAnswer in flight
  loadingQuestion: boolean; // loadNextQuestion in flight
  submitError: string | null; // generic submit / session-open error surface
  generateError: string | null; // /generate-question 502-style error (PR-3 surfaces "Try again")
}

// Reflection / Debrief (F5): the closing screen after the Boss. A short
// free-text reflection sub-stage ("prompt") → on submit we POST the reflection
// + a performance snapshot and render the AI debrief ("debrief"). Pass | Needs
// Retry is DERIVED from the server gate + boss outcome, never decided by the
// reflection endpoint (which only returns coaching prose).
export type ReflectionStage = "prompt" | "debrief";

interface ReflectionState {
  stage: ReflectionStage;
  prompts: string[]; // 1–2 reflection prompts shown to the student
  answers: string[]; // the student's free-text answers, one per prompt
  debrief: ReflectionResult | null; // AI coaching response
  performance: ReflectionPerformance | null; // snapshot sent + rendered
  passed: boolean; // derived Pass vs. Needs Retry
  submitting: boolean;
  submitError: string | null;
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
  submitCheckpointAnswer: (index: number, answer: string) => Promise<CheckAnswerResult | null>;
  advanceFromLearningBlock: () => void;
  enterSimulation: () => void;
  finishCbp: () => Promise<void>;
  retryCheckpoint: (index: number) => void;

  // ---- Flashcards / Memory Check sub-machine (Tile B) ----
  enterFlashcards: () => void;
  setCardIndex: (index: number) => void;
  markViewed: (index: number) => void;
  startMemoryCheck: () => void;
  submitMemoryItem: (index: number, answer: string) => Promise<CheckAnswerResult | null>;
  advanceMemoryItem: () => void;
  finishMemoryCheck: () => Promise<void>;
  retryMemoryCheck: () => void;

  // ---- Unlock Gate ----
  enterUnlockGate: () => void;

  // ---- Practice Arc (F4) ----
  enterPracticeArc: () => Promise<void>;
  advanceGame: () => void; // mark current node done, move to next (or finish)
  setGameIndex: (index: number) => void;

  // ---- Boss Arena (F4) ----
  startBoss: () => Promise<void>; // POST /boss/start → loadNextQuestion → status "fighting"
  loadNextQuestion: () => Promise<void>; // POST /boss/generate-question; 502 → generateError
  bossAnswer: (answer: string) => Promise<BossSubmitAnswerResponse | null>; // POST /boss/submit-answer + auto-chain
  advanceBossQuestion: () => void; // dismiss the turn-summary surface (PR-3 removes from UI)
  retryBoss: () => Promise<void>; // restart with force_fresh: true

  // ---- Reflection / Debrief (F5) ----
  enterReflection: () => void; // Boss finish → closing screen; seeds prompts + perf
  setReflectionAnswer: (index: number, value: string) => void;
  submitReflection: () => Promise<ReflectionResult | null>;
  retakeFromReflection: () => void; // Needs Retry → fresh Practice Arc (same concepts)

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
};

const initialPractice: PracticeState = {
  gameOrder: [],
  currentGameIndex: 0,
  completed: [],
  finished: false,
};

// Grade-band-style HP defaults mirror the backend's _fb_default_hp; the actual
// HP arrives from /boss/start (server-authoritative) — this is just the
// placeholder while the session is still being opened.
const DEFAULT_BOSS_HP = 100;

const initialBoss: BossState = {
  bossSessionId: null,
  hp: DEFAULT_BOSS_HP,
  maxHp: DEFAULT_BOSS_HP,
  trialsLeft: 0,
  currentDifficulty: "medium",
  currentQuestion: null,
  questionIndex: 0,
  attemptNumber: 1,
  status: "intro",
  lastResult: null,
  submitting: false,
  loadingQuestion: false,
  submitError: null,
  generateError: null,
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
        submitError: null,
      },
    })),

  submitCheckpointAnswer: async (index, answer) => {
    const { hwId, sessionId } = get();
    set((st) => ({ cbp: { ...st.cbp, submitting: true, submitError: null } }));
    try {
      const res = await submitCheckpoint(hwId, sessionId, index, answer);
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
      get().enterSimulation();
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
        submitError: null,
      },
    })),

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
  submitMemoryItem: async (index, answer) => {
    const { hwId, sessionId } = get();
    set((st) => ({ fc: { ...st.fc, submitting: true, submitError: null } }));
    try {
      const res = await submitMemoryCheckItem(hwId, sessionId, index, answer);
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
        fc: { ...st.fc, itemIndex: next, lastFeedback: null, lastCorrect: null },
      }));
    } else {
      void get().finishMemoryCheck();
    }
  },

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
          submitError: null,
        },
      };
    }),

  // ---- Unlock Gate ----
  enterUnlockGate: () => set({ screen: "gate" }),

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

  // ---- Boss Arena (F4) ----

  // Open the Plan-5 boss session and fetch the first question. Plan-5's
  // 30-min staleness window means we can call /boss/start unconditionally:
  // the server decides resume-vs-fresh and returns the live session state.
  // Only flip status → "fighting" once the first question lands; until then
  // we stay on the intro screen with a loading affordance.
  startBoss: async () => {
    const { hwId, sessionId, payload } = get();
    const meta = payload?.content_json.boss_meta;
    const maxHpOverride =
      typeof meta?.starting_hp_override === "number" && meta.starting_hp_override >= 10
        ? meta.starting_hp_override
        : undefined;

    set({
      boss: {
        ...initialBoss,
        status: "intro",
        submitting: true,
      },
    });

    try {
      const start = await bossStart(
        sessionId,
        hwId,
        maxHpOverride !== undefined ? { maxHp: maxHpOverride } : undefined
      );
      set((st) => ({
        boss: {
          ...st.boss,
          bossSessionId: start.boss_session_id,
          hp: start.hp,
          maxHp: start.max_hp,
          trialsLeft: start.trials_left,
          currentDifficulty: start.current_difficulty,
          submitting: false,
          submitError: null,
        },
      }));
    } catch (err) {
      set((st) => ({
        boss: {
          ...st.boss,
          submitting: false,
          submitError: (err as Error).message || "Couldn't open the boss session.",
        },
      }));
      return;
    }

    await get().loadNextQuestion();
    set((st) =>
      st.boss.currentQuestion ? { boss: { ...st.boss, status: "fighting" } } : {}
    );
  },

  // Fetch the next adaptive question from Plan-5. Surfaces 502 (anti-rep /
  // skill-floor / drift retry exhaustion) as `generateError` for the UI to
  // render a user-triggered "Try again" CTA per Boss Arena spec §10
  // (forbids static fallback). Resets per-question scaffold (attemptNumber,
  // lastResult) so the UI shows the fresh question cleanly.
  loadNextQuestion: async () => {
    const { boss } = get();
    if (!boss.bossSessionId) return;
    set((st) => ({
      boss: {
        ...st.boss,
        loadingQuestion: true,
        generateError: null,
      },
    }));
    try {
      const q = await bossGenerateQuestion(boss.bossSessionId);
      set((st) => ({
        boss: {
          ...st.boss,
          currentQuestion: q,
          currentDifficulty: q.difficulty,
          // Bump the local turn counter only after the FIRST question lands.
          questionIndex: st.boss.currentQuestion ? st.boss.questionIndex + 1 : 0,
          attemptNumber: 1,
          loadingQuestion: false,
          // NOTE: do NOT clear lastResult here — bossAnswer chains into this
          // action immediately after setting lastResult for the just-finished
          // turn, and the UI relies on lastResult to render the feedback card
          // alongside the next question. Use advanceBossQuestion() to dismiss
          // the turn summary explicitly.
        },
      }));
    } catch (err) {
      const retryExhausted = err instanceof ApiError && err.status === 502;
      set((st) => ({
        boss: {
          ...st.boss,
          loadingQuestion: false,
          generateError: retryExhausted
            ? "The boss is regrouping — try again."
            : (err as Error).message || "Couldn't fetch the next question.",
        },
      }));
    }
  },

  // Submit one boss answer to Plan-5. The server is HP-authoritative —
  // response.hp is the absolute new boss HP, NOT a delta; response.is_correct
  // and response.boss_status are canonical. On a non-terminal turn we
  // auto-chain to loadNextQuestion (every submission consumes one trial and
  // Plan-5 advances; there is no "retry same Q" path —
  // `should_retry_same_skill` only signals that the NEXT question targets the
  // same skill). On terminal (won/failed) we surface outcome/stars/outcome_xp
  // via lastResult for the results screen.
  bossAnswer: async (answer) => {
    const { boss } = get();
    if (!boss.bossSessionId || !boss.currentQuestion) return null;
    set((st) => ({ boss: { ...st.boss, submitting: true, submitError: null } }));
    try {
      const res = await bossSubmitAnswer(
        boss.bossSessionId,
        boss.currentQuestion.question_id,
        answer
      );
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
          hp: res.hp,
          trialsLeft: res.trials_left,
          currentDifficulty: res.current_difficulty,
          lastResult: res,
          status: nextStatus,
        },
      }));
      if (res.boss_status === "active") {
        // Auto-load the next adaptive question. Failures here surface via
        // generateError; the UI can render a "Try again" CTA without losing
        // the just-rendered turn feedback.
        await get().loadNextQuestion();
      }
      return res;
    } catch (err) {
      set((st) => ({
        boss: {
          ...st.boss,
          submitting: false,
          submitError: (err as Error).message || "Boss turn failed.",
        },
      }));
      return null;
    }
  },

  // Dismiss the turn-summary surface so the freshly auto-loaded question shows.
  // Kept as a no-op shim for BossArena's current "Press the attack" CTA; PR-3
  // removes that CTA and this action with it.
  advanceBossQuestion: () =>
    set((st) => ({ boss: { ...st.boss, lastResult: null } })),

  // Restart the fight: ask Plan-5 to archive the prior session and spawn a
  // fresh one, then re-fetch the first question. force_fresh skips the
  // staleness-window auto-resume.
  retryBoss: async () => {
    const { hwId, sessionId, payload } = get();
    const meta = payload?.content_json.boss_meta;
    const maxHpOverride =
      typeof meta?.starting_hp_override === "number" && meta.starting_hp_override >= 10
        ? meta.starting_hp_override
        : undefined;

    set({
      boss: {
        ...initialBoss,
        status: "intro",
        submitting: true,
      },
    });

    try {
      const start = await bossStart(sessionId, hwId, {
        ...(maxHpOverride !== undefined ? { maxHp: maxHpOverride } : {}),
        forceFresh: true,
      });
      set((st) => ({
        boss: {
          ...st.boss,
          bossSessionId: start.boss_session_id,
          hp: start.hp,
          maxHp: start.max_hp,
          trialsLeft: start.trials_left,
          currentDifficulty: start.current_difficulty,
          submitting: false,
          submitError: null,
        },
      }));
    } catch (err) {
      set((st) => ({
        boss: {
          ...st.boss,
          submitting: false,
          submitError: (err as Error).message || "Couldn't restart the boss.",
        },
      }));
      return;
    }

    await get().loadNextQuestion();
    set((st) =>
      st.boss.currentQuestion ? { boss: { ...st.boss, status: "fighting" } } : {}
    );
  },

  // ---- Reflection / Debrief (F5) ----

  // Enter the closing screen. We seed the reflection prompts (author override
  // via content_json.reflection.prompts, else the Flow-v2 defaults) and capture
  // a performance snapshot. Pass | Needs Retry is DERIVED here — never from the
  // reflection endpoint: a Boss win + a passed gate is the pass; a Boss loss or
  // a failed gate is Needs Retry. The server gate stays authoritative on grading.
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

  // POST the combined reflection + performance snapshot and render the debrief.
  // The endpoint returns coaching prose only ({feedback, next_steps[],
  // encouragement}); pass/score were already derived in enterReflection.
  submitReflection: async () => {
    const { payload, reflection } = get();
    set((st) => ({ reflection: { ...st.reflection, submitting: true, submitError: null } }));
    const studentReflection = reflection.prompts
      .map((p, i) => `${p}\n${(reflection.answers[i] ?? "").trim()}`)
      .join("\n\n")
      .trim();
    const summary =
      (payload?.content_json.case_based_preview?.case_setup?.task as string | undefined) ??
      (payload?.subject ?? "");
    const gradeNum =
      typeof payload?.grade === "number"
        ? payload.grade
        : Number.parseInt(String(payload?.grade ?? ""), 10);
    try {
      const debrief = await submitReflection({
        homeworkTitle: payload?.title ?? "",
        homeworkSummary: summary,
        studentReflection,
        performance: reflection.performance ?? { passed: reflection.passed },
        ...(payload?.subject ? { subject: payload.subject } : {}),
        ...(Number.isFinite(gradeNum) ? { grade: gradeNum } : {}),
      });
      set((st) => ({
        reflection: { ...st.reflection, submitting: false, debrief, stage: "debrief" },
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

  // Needs Retry → retake = SAME concepts, fresh questions. We re-enter the
  // Practice Arc from the top (which re-resolves the game order and resets the
  // Boss); the backend serves fresh questions for the same concepts.
  retakeFromReflection: () => {
    void get().enterPracticeArc();
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
