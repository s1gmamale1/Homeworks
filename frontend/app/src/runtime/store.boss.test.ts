// Dynamic Boss (Plan 5) store-slice tests. The slice must:
//   - startBoss → open the session, load the first question, flip to "fighting"
//   - submitBossAnswer → apply the ABSOLUTE server hp/trials/difficulty, bump or
//     reset the combo, map boss_status → status, and auto-chain on "active"
//   - a 502 on generate → set generateError + escalate consecutiveGenerateFailures
//   - retryBoss → POST /start with force_fresh and reset combo/hints/index

import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiError } from "../shared/api";

// Mock the API surface the boss slice touches. Each test sets the resolved
// values / rejections it needs.
vi.mock("../shared/api", async () => {
  const actual = await vi.importActual<typeof import("../shared/api")>("../shared/api");
  return {
    ...actual,
    bossStart: vi.fn(),
    bossGenerateQuestion: vi.fn(),
    bossSubmitAnswer: vi.fn(),
  };
});

import { bossStart, bossGenerateQuestion, bossSubmitAnswer } from "../shared/api";
import { useRuntimeStore } from "./store";

const mockStart = bossStart as ReturnType<typeof vi.fn>;
const mockGen = bossGenerateQuestion as ReturnType<typeof vi.fn>;
const mockSubmit = bossSubmitAnswer as ReturnType<typeof vi.fn>;

function startResponse(over: Partial<Record<string, unknown>> = {}) {
  return {
    boss_session_id: "bs_1",
    hp: 100,
    max_hp: 100,
    trials_left: 7,
    current_difficulty: "medium",
    weak_topics: [],
    strong_topics: [],
    missing_context_flags: [],
    ...over,
  };
}

function questionResponse(over: Partial<Record<string, unknown>> = {}) {
  return {
    question_id: "q1",
    question_text: "Define X.",
    scenario: "",
    why: "",
    how: "",
    what: "",
    target_skill: "skill",
    difficulty: "medium",
    why_this_question: "weak topic",
    boss_session_id: "bs_1",
    ...over,
  };
}

function submitResponse(over: Partial<Record<string, unknown>> = {}) {
  return {
    is_correct: true,
    score: 1,
    confidence: 0.9,
    feedback: "Nice.",
    damage: 20,
    hp: 80,
    trials_left: 6,
    current_difficulty: "medium",
    boss_status: "active",
    should_retry_same_skill: false,
    misconception_tags: [],
    ...over,
  };
}

function resetStore() {
  useRuntimeStore.setState({
    hwId: "hw1",
    sessionId: "s1",
    payload: null,
  });
  // Reset boss slice to the intro defaults.
  useRuntimeStore.setState((st) => ({
    boss: {
      ...st.boss,
      bossSessionId: null,
      hp: 100,
      maxHp: 100,
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
    },
  }));
}

beforeEach(() => {
  vi.clearAllMocks();
  resetStore();
});

describe("startBoss", () => {
  it("opens the session, loads the first question, and flips to fighting", async () => {
    mockStart.mockResolvedValue(startResponse({ hp: 90, max_hp: 90, trials_left: 5, current_difficulty: "easy" }));
    mockGen.mockResolvedValue(questionResponse({ question_id: "qA" }));

    await useRuntimeStore.getState().startBoss();

    const boss = useRuntimeStore.getState().boss;
    expect(mockStart).toHaveBeenCalledTimes(1);
    expect(mockGen).toHaveBeenCalledTimes(1);
    expect(boss.bossSessionId).toBe("bs_1");
    expect(boss.hp).toBe(90);
    expect(boss.maxHp).toBe(90);
    expect(boss.trialsLeft).toBe(5);
    expect(boss.currentDifficulty).toBe("easy");
    expect(boss.currentQuestion?.question_id).toBe("qA");
    expect(boss.status).toBe("fighting");
  });

  it("passes starting_hp_override (>=10) as advisory max_hp", async () => {
    useRuntimeStore.setState({
      payload: {
        id: "hw1",
        title: "T",
        subject: null,
        grade: null,
        lang: null,
        flow_version: "v2",
        content_json: { boss_meta: { starting_hp_override: 150 } },
      },
    });
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValue(questionResponse());

    await useRuntimeStore.getState().startBoss();

    expect(mockStart).toHaveBeenCalledWith(
      expect.objectContaining({ sessionId: "s1", homeworkId: "hw1", maxHp: 150 })
    );
  });

  it("keeps the intro screen and surfaces submitError when /start fails", async () => {
    mockStart.mockRejectedValue(new Error("boom"));

    await useRuntimeStore.getState().startBoss();

    const boss = useRuntimeStore.getState().boss;
    expect(boss.status).toBe("intro");
    expect(boss.submitError).toBe("boom");
    expect(mockGen).not.toHaveBeenCalled();
  });
});

describe("submitBossAnswer", () => {
  async function arm(questionOver = {}) {
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValue(questionResponse(questionOver));
    await useRuntimeStore.getState().startBoss();
    mockGen.mockClear();
  }

  it("applies absolute hp/trials/difficulty and increments combo on a correct answer", async () => {
    await arm();
    mockSubmit.mockResolvedValue(
      submitResponse({ hp: 70, trials_left: 5, current_difficulty: "hard", is_correct: true })
    );
    // The next chained question.
    mockGen.mockResolvedValue(questionResponse({ question_id: "q2" }));

    await useRuntimeStore.getState().submitBossAnswer("Why: a\nHow: b\nWhat: c");

    const boss = useRuntimeStore.getState().boss;
    expect(boss.hp).toBe(70); // absolute, not 100 - damage computed client-side
    expect(boss.trialsLeft).toBe(5);
    expect(boss.currentDifficulty).toBe("hard");
    expect(boss.combo).toBe(1);
    expect(boss.status).toBe("fighting");
    // Auto-chain fetched the next question.
    expect(mockGen).toHaveBeenCalledTimes(1);
    expect(boss.currentQuestion?.question_id).toBe("q2");
  });

  it("resets combo to 0 on a wrong answer", async () => {
    await arm();
    useRuntimeStore.setState((st) => ({ boss: { ...st.boss, combo: 4 } }));
    mockSubmit.mockResolvedValue(submitResponse({ is_correct: false, hp: 100, damage: 0 }));
    mockGen.mockResolvedValue(questionResponse({ question_id: "q3" }));

    await useRuntimeStore.getState().submitBossAnswer("guess");

    expect(useRuntimeStore.getState().boss.combo).toBe(0);
  });

  it("maps boss_status 'won' → status 'won' and does NOT chain another question", async () => {
    await arm();
    mockSubmit.mockResolvedValue(
      submitResponse({ boss_status: "won", hp: 0, stars: 3, outcome_xp: 120, is_correct: true })
    );

    await useRuntimeStore.getState().submitBossAnswer("Why: a\nHow: b\nWhat: c");

    const boss = useRuntimeStore.getState().boss;
    expect(boss.status).toBe("won");
    expect(boss.lastResult?.stars).toBe(3);
    expect(mockGen).not.toHaveBeenCalled();
  });

  it("maps boss_status 'failed' → status 'lost'", async () => {
    await arm();
    mockSubmit.mockResolvedValue(
      submitResponse({ boss_status: "failed", is_correct: false, trials_left: 0, hp: 40 })
    );

    await useRuntimeStore.getState().submitBossAnswer("guess");

    expect(useRuntimeStore.getState().boss.status).toBe("lost");
    expect(mockGen).not.toHaveBeenCalled();
  });
});

describe("loadNextQuestion 502 handling", () => {
  it("sets generateError and increments failures on a 502", async () => {
    mockStart.mockResolvedValue(startResponse());
    // First generate (during startBoss) fails with 502.
    mockGen.mockRejectedValueOnce(new ApiError("502 boom", 502, "/x"));

    await useRuntimeStore.getState().startBoss();

    let boss = useRuntimeStore.getState().boss;
    expect(boss.generateError).toBeTruthy();
    expect(boss.consecutiveGenerateFailures).toBe(1);
    // startBoss left us on intro (no question landed).
    expect(boss.status).toBe("intro");

    // A second 502 escalates to >= 2 (the refresh threshold).
    mockGen.mockRejectedValueOnce(new ApiError("502 again", 502, "/x"));
    await useRuntimeStore.getState().loadNextQuestion();
    boss = useRuntimeStore.getState().boss;
    expect(boss.consecutiveGenerateFailures).toBe(2);
  });

  it("resets the failure counter once a question loads", async () => {
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockRejectedValueOnce(new ApiError("502", 502, "/x"));
    await useRuntimeStore.getState().startBoss();
    expect(useRuntimeStore.getState().boss.consecutiveGenerateFailures).toBe(1);

    mockGen.mockResolvedValueOnce(questionResponse({ question_id: "qOK" }));
    await useRuntimeStore.getState().loadNextQuestion();
    const boss = useRuntimeStore.getState().boss;
    expect(boss.consecutiveGenerateFailures).toBe(0);
    expect(boss.generateError).toBeNull();
    expect(boss.currentQuestion?.question_id).toBe("qOK");
  });
});

describe("retryBoss", () => {
  it("POSTs /start with force_fresh and resets combo/hints/index", async () => {
    // Arm a finished-ish state with non-zero combo/hints/index.
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValue(questionResponse());
    await useRuntimeStore.getState().startBoss();
    useRuntimeStore.setState((st) => ({
      boss: { ...st.boss, combo: 5, hintsUsed: 2, questionIndex: 6, status: "lost" },
    }));
    mockStart.mockClear();
    mockGen.mockClear();

    mockStart.mockResolvedValue(startResponse({ trials_left: 7 }));
    mockGen.mockResolvedValue(questionResponse({ question_id: "qFresh" }));

    await useRuntimeStore.getState().retryBoss();

    expect(mockStart).toHaveBeenCalledWith(expect.objectContaining({ forceFresh: true }));
    const boss = useRuntimeStore.getState().boss;
    expect(boss.combo).toBe(0);
    expect(boss.hintsUsed).toBe(0);
    expect(boss.questionIndex).toBe(0);
    expect(boss.status).toBe("fighting");
    expect(boss.currentQuestion?.question_id).toBe("qFresh");
  });
});

describe("requestHint", () => {
  it("only increments the local hintsUsed counter (no network, no reveal)", async () => {
    useRuntimeStore.getState().requestHint();
    useRuntimeStore.getState().requestHint();
    expect(useRuntimeStore.getState().boss.hintsUsed).toBe(2);
    expect(mockGen).not.toHaveBeenCalled();
    expect(mockSubmit).not.toHaveBeenCalled();
  });
});
