// Dynamic Boss Arena (Plan 5) component tests. Drives the turn loop through the
// store (API mocked) and asserts the rendered surfaces: intro → fighting →
// won/lost, the 3 Why/How/What inputs + concatenated submit, the loading
// skeleton, the 502 retry/refresh escalation, the combo/tier/hint chrome, the
// reduced-motion path, and an answer-leak assertion (the FE only ever sends
// `student_answer`; the question/state response types carry no answer key).

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

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
import { ApiError } from "../shared/api";
import { useRuntimeStore } from "./store";
import BossArena from "./BossArena";

const mockStart = bossStart as ReturnType<typeof vi.fn>;
const mockGen = bossGenerateQuestion as ReturnType<typeof vi.fn>;
const mockSubmit = bossSubmitAnswer as ReturnType<typeof vi.fn>;

const onComplete = vi.fn();

function startResponse(over: Record<string, unknown> = {}) {
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

function structuredQuestion(over: Record<string, unknown> = {}) {
  return {
    question_id: "q1",
    question_text: "Fallback text.",
    scenario: "A train leaves the station.",
    why: "Why does it accelerate?",
    how: "How would you compute it?",
    what: "What is the final speed?",
    target_skill: "kinematics",
    difficulty: "medium",
    why_this_question: "weak topic",
    boss_session_id: "bs_1",
    ...over,
  };
}

function flatQuestion(over: Record<string, unknown> = {}) {
  return {
    question_id: "qflat",
    question_text: "Define momentum.",
    scenario: "",
    why: "",
    how: "",
    what: "",
    target_skill: "momentum",
    difficulty: "easy",
    why_this_question: "weak topic",
    boss_session_id: "bs_1",
    ...over,
  };
}

function submitResponse(over: Record<string, unknown> = {}) {
  return {
    is_correct: true,
    score: 1,
    confidence: 0.9,
    feedback: "Solid.",
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
  useRuntimeStore.setState({ hwId: "hw1", sessionId: "s1", payload: null });
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
  onComplete.mockClear();
  resetStore();
});

describe("intro → fighting", () => {
  it("renders the intro scaffold and enters the arena on click", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValue(structuredQuestion());

    render(<BossArena onComplete={onComplete} />);
    expect(screen.getByTestId("boss-intro")).toBeInTheDocument();

    await user.click(screen.getByTestId("boss-begin"));

    await waitFor(() => expect(screen.getByTestId("boss-fighting")).toBeInTheDocument());
    expect(screen.getByTestId("boss-hp")).toHaveTextContent("100 / 100 HP");
    expect(screen.getByTestId("boss-trials")).toHaveTextContent("7");
    expect(screen.getByTestId("boss-difficulty")).toHaveTextContent("medium");
    expect(screen.getByTestId("boss-combo")).toHaveTextContent("Combo ×0");
    expect(screen.getByTestId("boss-hint")).toBeInTheDocument();
  });

  it("shows the start error and keeps the intro when /start fails", async () => {
    const user = userEvent.setup();
    mockStart.mockRejectedValue(new Error("no session"));

    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));

    await waitFor(() => expect(screen.getByTestId("boss-start-error")).toHaveTextContent("no session"));
    expect(screen.getByTestId("boss-intro")).toBeInTheDocument();
  });
});

describe("structured Why/How/What submit", () => {
  it("renders 3 inputs and submits the concatenated answer", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(structuredQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    expect(screen.getByTestId("boss-input-why")).toBeInTheDocument();
    expect(screen.getByTestId("boss-input-how")).toBeInTheDocument();
    expect(screen.getByTestId("boss-input-what")).toBeInTheDocument();

    await user.type(screen.getByTestId("boss-input-why"), "inertia");
    await user.type(screen.getByTestId("boss-input-how"), "F=ma");
    await user.type(screen.getByTestId("boss-input-what"), "10 m/s");

    // Chain to a terminal verdict so we don't need a follow-up question.
    mockSubmit.mockResolvedValue(submitResponse({ boss_status: "won", hp: 0, stars: 2, outcome_xp: 90 }));
    await user.click(screen.getByTestId("boss-attack"));

    await waitFor(() => expect(mockSubmit).toHaveBeenCalledTimes(1));
    expect(mockSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        bossSessionId: "bs_1",
        questionId: "q1",
        studentAnswer: "Why: inertia\nHow: F=ma\nWhat: 10 m/s",
      })
    );
  });

  it("gates the attack button until the What field is non-empty", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(structuredQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    expect(screen.getByTestId("boss-attack")).toBeDisabled();
    await user.type(screen.getByTestId("boss-input-why"), "only why");
    expect(screen.getByTestId("boss-attack")).toBeDisabled();
    await user.type(screen.getByTestId("boss-input-what"), "the result");
    expect(screen.getByTestId("boss-attack")).toBeEnabled();
  });

  it("renders a single textarea for a flat (non-structured) question", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(flatQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    expect(screen.queryByTestId("boss-input-why")).not.toBeInTheDocument();
    expect(screen.getByTestId("boss-input-what")).toBeInTheDocument();

    await user.type(screen.getByTestId("boss-input-what"), "p = mv");
    mockSubmit.mockResolvedValue(submitResponse({ boss_status: "won", hp: 0 }));
    await user.click(screen.getByTestId("boss-attack"));
    await waitFor(() => expect(mockSubmit).toHaveBeenCalled());
    expect(mockSubmit.mock.calls[0][0].studentAnswer).toBe("p = mv");
  });
});

describe("turn-result card", () => {
  it("shows damage, feedback, misconceptions, and coverage bars", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(structuredQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    await user.type(screen.getByTestId("boss-input-what"), "answer");
    // Wrong answer keeps us in the fighting view (active) so the card renders.
    mockSubmit.mockResolvedValue(
      submitResponse({
        is_correct: false,
        damage: 0,
        feedback: "Close, but check the units.",
        misconception_tags: ["unit_error"],
        coverage: { why: 0.9, how: 0.4, what: 0.6 },
      })
    );
    // The auto-chained next question.
    mockGen.mockResolvedValueOnce(structuredQuestion({ question_id: "q2" }));

    await user.click(screen.getByTestId("boss-attack"));

    await waitFor(() => expect(screen.getByTestId("boss-turn-result")).toBeInTheDocument());
    expect(screen.getByTestId("boss-turn-result")).toHaveTextContent("Close, but check the units.");
    expect(screen.getByTestId("boss-misconceptions")).toHaveTextContent("unit_error");
    const coverage = screen.getByTestId("boss-coverage");
    expect(coverage).toHaveTextContent("90%");
    expect(coverage).toHaveTextContent("40%");
    expect(coverage).toHaveTextContent("60%");
  });
});

describe("won / lost screens", () => {
  it("renders the won screen with stars + XP and calls onComplete on claim", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(structuredQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    await user.type(screen.getByTestId("boss-input-what"), "answer");
    mockSubmit.mockResolvedValue(submitResponse({ boss_status: "won", hp: 0, stars: 3, outcome_xp: 150 }));
    await user.click(screen.getByTestId("boss-attack"));

    await waitFor(() => expect(screen.getByTestId("boss-won")).toBeInTheDocument());
    expect(screen.getByTestId("boss-xp")).toHaveTextContent("150 XP");

    await user.click(screen.getByTestId("boss-finish"));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it("renders the lost screen and restarts via force_fresh on retry", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(structuredQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    await user.type(screen.getByTestId("boss-input-what"), "answer");
    mockSubmit.mockResolvedValue(submitResponse({ boss_status: "failed", is_correct: false, trials_left: 0 }));
    await user.click(screen.getByTestId("boss-attack"));

    await waitFor(() => expect(screen.getByTestId("boss-lost")).toBeInTheDocument());

    mockStart.mockClear();
    mockStart.mockResolvedValue(startResponse({ trials_left: 7 }));
    mockGen.mockResolvedValueOnce(structuredQuestion({ question_id: "qFresh" }));
    await user.click(screen.getByTestId("boss-retry"));

    await waitFor(() => expect(screen.getByTestId("boss-fighting")).toBeInTheDocument());
    expect(mockStart).toHaveBeenCalledWith(expect.objectContaining({ forceFresh: true }));
  });
});

describe("combo + hint", () => {
  it("shows the +20% bonus chip once the combo reaches the threshold", async () => {
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValue(structuredQuestion());
    const user = userEvent.setup();
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    act(() => {
      useRuntimeStore.setState((st) => ({ boss: { ...st.boss, combo: 3 } }));
    });
    expect(screen.getByTestId("boss-combo")).toHaveTextContent("+20%");
  });

  it("tracks hint cost locally without any network call", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(structuredQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    mockGen.mockClear();
    await user.click(screen.getByTestId("boss-hint"));
    expect(useRuntimeStore.getState().boss.hintsUsed).toBe(1);
    expect(mockGen).not.toHaveBeenCalled();
    expect(mockSubmit).not.toHaveBeenCalled();
  });
});

describe("502 generate-error block", () => {
  it("offers Try again on the first failure and Refresh after two", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    // First generate (during startBoss) 502s → we stay on intro with the error.
    mockGen.mockRejectedValueOnce(new ApiError("502", 502, "/x"));
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));

    // Force the fighting view to surface the inline generate-error block by
    // putting the store in a fighting state with the generateError set.
    act(() => {
      useRuntimeStore.setState((st) => ({
        boss: { ...st.boss, status: "fighting", consecutiveGenerateFailures: 1 },
      }));
    });
    expect(screen.getByTestId("boss-generate-error")).toBeInTheDocument();
    expect(screen.getByTestId("boss-generate-retry")).toBeInTheDocument();

    act(() => {
      useRuntimeStore.setState((st) => ({
        boss: { ...st.boss, consecutiveGenerateFailures: 2 },
      }));
    });
    expect(screen.getByTestId("boss-generate-refresh")).toBeInTheDocument();
  });
});

describe("loading skeleton", () => {
  it("shows the generation skeleton while the first question loads", async () => {
    let resolveGen: (v: unknown) => void = () => {};
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockReturnValue(new Promise((res) => { resolveGen = res; }));

    const user = userEvent.setup();
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));

    await waitFor(() => expect(screen.getByTestId("boss-loading-question")).toBeInTheDocument());

    await act(async () => {
      resolveGen(structuredQuestion());
    });
    await waitFor(() => expect(screen.getByTestId("boss-fighting")).toBeInTheDocument());
  });
});

describe("reduced-motion path", () => {
  it("still renders the full fighting view when reduced motion is preferred", async () => {
    // matchMedia default returns matches:false; flip it for this test.
    const original = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: query.includes("reduce"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as unknown as typeof window.matchMedia;

    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(structuredQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => expect(screen.getByTestId("boss-fighting")).toBeInTheDocument());
    expect(screen.getByTestId("boss-hp")).toBeInTheDocument();

    window.matchMedia = original;
  });
});

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Answer-leak assertion (compile-time + runtime). The dynamic boss response
// types carry NO answer/rubric/expected field, and the FE only ever sends
// `student_answer`. This guards the Plan 5 / TUTOR answer-leak invariant.
// ---------------------------------------------------------------------------
describe("answer-leak guarantee", () => {
  it("the FE only ever sends student_answer (never an answer key)", async () => {
    const user = userEvent.setup();
    mockStart.mockResolvedValue(startResponse());
    mockGen.mockResolvedValueOnce(structuredQuestion());
    render(<BossArena onComplete={onComplete} />);
    await user.click(screen.getByTestId("boss-begin"));
    await waitFor(() => screen.getByTestId("boss-fighting"));

    await user.type(screen.getByTestId("boss-input-what"), "the answer");
    mockSubmit.mockResolvedValue(submitResponse({ boss_status: "won", hp: 0 }));
    await user.click(screen.getByTestId("boss-attack"));
    await waitFor(() => expect(mockSubmit).toHaveBeenCalled());

    const sent = mockSubmit.mock.calls[0][0] as Record<string, unknown>;
    const keys = Object.keys(sent);
    for (const forbidden of ["expected", "expected_answer", "rubric", "answer", "answer_spec", "correct", "accepted_answers"]) {
      expect(keys).not.toContain(forbidden);
    }
    expect(keys.sort()).toEqual(["bossSessionId", "questionId", "studentAnswer"]);
  });

  it("the generate-question response type carries no answer-bearing field", () => {
    // Compile-time guard (the `never` fields in BossGenerateQuestionResponse)
    // is the real protection; this runtime check documents the same contract.
    const q = structuredQuestion();
    const keys = Object.keys(q);
    for (const forbidden of ["expected", "expected_answer", "rubric", "answer", "answer_spec", "correct", "accepted_answers"]) {
      expect(keys).not.toContain(forbidden);
    }
  });
});
