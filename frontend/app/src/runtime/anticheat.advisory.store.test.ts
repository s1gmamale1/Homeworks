// Advisory-only guarantee at the store layer: an `integrity_nudge` on a submit
// response is parked as DISPLAY-ONLY signal and NEVER flips gate / hp / combo /
// correctness state. Correctness + the absolute boss state are always the
// server's; the nudge rides alongside.
//
// Research contract: docs/NETS_Academic_Integrity_AntiCheat_Research.md.

import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock just the submit endpoints the store slice touches.
vi.mock("../shared/api", async () => {
  const actual = await vi.importActual<typeof import("../shared/api")>("../shared/api");
  return {
    ...actual,
    bossStart: vi.fn(),
    bossGenerateQuestion: vi.fn(),
    bossSubmitAnswer: vi.fn(),
    submitCheckpoint: vi.fn(),
    submitMemoryCheckItem: vi.fn(),
    submitReasoning: vi.fn(),
  };
});

import {
  bossSubmitAnswer,
  submitCheckpoint,
  submitMemoryCheckItem,
} from "../shared/api";
import { useRuntimeStore } from "./store";

const mockBossSubmit = bossSubmitAnswer as ReturnType<typeof vi.fn>;
const mockCheckpoint = submitCheckpoint as ReturnType<typeof vi.fn>;
const mockMemory = submitMemoryCheckItem as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
  useRuntimeStore.setState({ hwId: "hw1", sessionId: "s1", payload: null });
});

describe("anti-cheat advisory — the store keeps a nudge display-only", () => {
  it("a boss verdict's nudge is stored but hp/status come from the server", async () => {
    useRuntimeStore.setState((st) => ({
      boss: {
        ...st.boss,
        bossSessionId: "bs1",
        currentQuestion: {
          question_id: "q1",
          question_text: "Q",
          scenario: "",
          why: "",
          how: "",
          what: "",
          difficulty: "medium",
          target_skill: "s",
          why_this_question: "weak topic",
          boss_session_id: "bs1",
        },
        hp: 80,
        maxHp: 100,
        trialsLeft: 5,
        combo: 2,
        status: "fighting",
        lastResult: null,
      },
    }));

    mockBossSubmit.mockResolvedValue({
      is_correct: true,
      score: 1,
      confidence: 0.9,
      feedback: "ok",
      damage: 80,
      hp: 0, // server says HP is 0 → won
      trials_left: 5,
      current_difficulty: "medium",
      boss_status: "won",
      should_retry_same_skill: false,
      misconception_tags: [],
      integrity_nudge: { type: "rushed", message: "Slow down a touch." },
    });

    await useRuntimeStore.getState().submitBossAnswer("answer");

    const boss = useRuntimeStore.getState().boss;
    // Absolute server state — mirrored, NOT derived from the nudge.
    expect(boss.hp).toBe(0);
    expect(boss.status).toBe("won");
    // The nudge rides on lastResult for display; the verdict is unchanged.
    expect(boss.lastResult?.integrity_nudge?.message).toBe("Slow down a touch.");
    expect(boss.lastResult?.is_correct).toBe(true);
  });

  it("the boss combo still follows is_correct, not the presence of a nudge", async () => {
    useRuntimeStore.setState((st) => ({
      boss: {
        ...st.boss,
        bossSessionId: "bs1",
        currentQuestion: {
          question_id: "q1",
          question_text: "Q",
          scenario: "",
          why: "",
          how: "",
          what: "",
          difficulty: "medium",
          target_skill: "s",
          why_this_question: "weak topic",
          boss_session_id: "bs1",
        },
        combo: 3,
        status: "fighting",
        lastResult: null,
      },
    }));

    // A WRONG answer that still carries a nudge → combo must RESET to 0.
    mockBossSubmit.mockResolvedValue({
      is_correct: false,
      score: 0,
      confidence: 0.4,
      feedback: "no",
      damage: 0,
      hp: 60,
      trials_left: 4,
      current_difficulty: "medium",
      boss_status: "failed",
      should_retry_same_skill: true,
      misconception_tags: [],
      integrity_nudge: { type: "paste", message: "Type it yourself." },
    });

    await useRuntimeStore.getState().submitBossAnswer("answer");

    const boss = useRuntimeStore.getState().boss;
    expect(boss.combo).toBe(0); // driven by is_correct=false, not the nudge
    expect(boss.status).toBe("lost");
    expect(boss.lastResult?.integrity_nudge?.message).toBe("Type it yourself.");
  });

  it("a CBP nudge is stored but correctness still comes from the server", async () => {
    useRuntimeStore.setState((st) => ({
      cbp: { ...st.cbp, results: [false, false, false], lastNudge: null },
    }));

    mockCheckpoint.mockResolvedValue({
      correct: true,
      feedback: "Right.",
      learning_block: "Lesson.",
      integrity_nudge: { type: "paste", message: "Explain in your own words." },
    });

    await useRuntimeStore.getState().submitCheckpointAnswer(0, "A", {
      client_time_ms: 10,
      paste_detected: true,
    });

    const cbp = useRuntimeStore.getState().cbp;
    // Correctness is the server's; the nudge is parked separately.
    expect(cbp.results[0]).toBe(true);
    expect(cbp.lastNudge?.message).toBe("Explain in your own words.");
  });

  it("a Memory Check nudge is stored without changing score or correctness", async () => {
    useRuntimeStore.setState((st) => ({
      fc: { ...st.fc, results: [null, null], scorePct: 0, lastNudge: null },
    }));

    mockMemory.mockResolvedValue({
      correct: false,
      feedback: "Not quite.",
      learning_block: null,
      integrity_nudge: { type: "rushed", message: "Take your time." },
    });

    await useRuntimeStore.getState().submitMemoryItem(0, "x", { client_time_ms: 5 });

    const fc = useRuntimeStore.getState().fc;
    expect(fc.results[0]).toBe(false); // server-confirmed
    expect(fc.lastNudge?.message).toBe("Take your time.");
  });

  it("dismissing a CBP nudge clears ONLY the nudge, not the results", () => {
    useRuntimeStore.setState((st) => ({
      cbp: {
        ...st.cbp,
        results: [true, false, false],
        lastNudge: { type: "x", message: "hi" },
      },
    }));

    useRuntimeStore.getState().dismissCbpNudge();

    const cbp = useRuntimeStore.getState().cbp;
    expect(cbp.lastNudge).toBeNull();
    // Server-confirmed correctness is untouched by the dismissal.
    expect(cbp.results).toEqual([true, false, false]);
  });

  it("dismissing a Memory Check nudge clears ONLY the nudge, not the score", () => {
    useRuntimeStore.setState((st) => ({
      fc: {
        ...st.fc,
        results: [true, false],
        scorePct: 50,
        lastNudge: { type: "x", message: "hi" },
      },
    }));

    useRuntimeStore.getState().dismissMcNudge();

    const fc = useRuntimeStore.getState().fc;
    expect(fc.lastNudge).toBeNull();
    expect(fc.scorePct).toBe(50);
    expect(fc.results).toEqual([true, false]);
  });
});
