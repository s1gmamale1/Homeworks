// Tests for the Plan-5 boss slice of useRuntimeStore. Drives the store
// actions end-to-end against a mocked global.fetch, asserting the state
// transitions that the BossArena UI relies on (status flips, HP being
// server-absolute, trials decrement, terminal-vs-active branch, 502 surfacing).
//
// Why integration-style tests over pure unit tests: the actions chain
// (startBoss → loadNextQuestion; bossAnswer → loadNextQuestion on "active"),
// and the value of these tests is in pinning that chain — not in mocking
// individual API client functions.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useRuntimeStore } from "./store";
import type { HydratePayload } from "../shared/types";

// Minimal payload — only the fields the boss slice reads (boss_meta).
function makePayload(opts?: { startingHpOverride?: number }): HydratePayload {
  return {
    id: "HW-001",
    title: "Test homework",
    subject: "math",
    grade: 5,
    lang: "en",
    flow_version: "v2",
    content_json: {
      ...(opts?.startingHpOverride !== undefined
        ? { boss_meta: { starting_hp_override: opts.startingHpOverride } }
        : {}),
    },
  };
}

// Construct a Response-shaped object the fetch wrapper accepts.
function okResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => body,
  } as unknown as Response;
}

function errResponse(status: number, detail: string): Response {
  return {
    ok: false,
    status,
    statusText: detail,
    json: async () => ({ detail }),
  } as unknown as Response;
}

// Reset the store + global fetch between tests so state never leaks across cases.
beforeEach(() => {
  useRuntimeStore.setState({
    hwId: "HW-001",
    sessionId: "sess-1",
    payload: makePayload(),
    boss: {
      bossSessionId: null,
      hp: 100,
      maxHp: 100,
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
    },
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

// Helper: stage a sequence of fetch responses, one per call in order.
function stageResponses(responses: Response[]): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn<typeof fetch>();
  for (const r of responses) {
    fetchMock.mockResolvedValueOnce(r);
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("startBoss", () => {
  it("opens a Plan-5 session, loads the first question, and flips status to fighting", async () => {
    stageResponses([
      okResponse({
        boss_session_id: "bs_1",
        hp: 100,
        max_hp: 100,
        trials_left: 5,
        current_difficulty: "medium",
        weak_topics: [],
        strong_topics: [],
        missing_context_flags: [],
      }),
      okResponse({
        question_id: "gbq_1",
        question_text: "What is 2+2?",
        target_skill: "addition",
        difficulty: "easy",
        why_this_question: "warmup",
        boss_session_id: "bs_1",
      }),
    ]);

    await useRuntimeStore.getState().startBoss();

    const boss = useRuntimeStore.getState().boss;
    expect(boss.status).toBe("fighting");
    expect(boss.bossSessionId).toBe("bs_1");
    expect(boss.hp).toBe(100);
    expect(boss.maxHp).toBe(100);
    expect(boss.trialsLeft).toBe(5);
    expect(boss.currentDifficulty).toBe("easy"); // updated by loadNextQuestion
    expect(boss.currentQuestion?.question_id).toBe("gbq_1");
    expect(boss.submitting).toBe(false);
    expect(boss.loadingQuestion).toBe(false);
    expect(boss.submitError).toBeNull();
  });

  it("forwards starting_hp_override from boss_meta as max_hp to /boss/start", async () => {
    useRuntimeStore.setState({ payload: makePayload({ startingHpOverride: 150 }) });
    const fetchMock = stageResponses([
      okResponse({
        boss_session_id: "bs_2",
        hp: 150,
        max_hp: 150,
        trials_left: 5,
        current_difficulty: "medium",
        weak_topics: [],
        strong_topics: [],
        missing_context_flags: [],
      }),
      okResponse({
        question_id: "gbq_1",
        question_text: "Q",
        target_skill: "x",
        difficulty: "medium",
        why_this_question: "",
        boss_session_id: "bs_2",
      }),
    ]);

    await useRuntimeStore.getState().startBoss();

    // First call is /boss/start; assert the body includes max_hp.
    const [, init] = fetchMock.mock.calls[0];
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.max_hp).toBe(150);
    expect(useRuntimeStore.getState().boss.maxHp).toBe(150);
  });

  it("stays on intro and surfaces submitError when /boss/start fails", async () => {
    stageResponses([errResponse(500, "kimi_unavailable")]);

    await useRuntimeStore.getState().startBoss();

    const boss = useRuntimeStore.getState().boss;
    expect(boss.status).toBe("intro");
    expect(boss.bossSessionId).toBeNull();
    expect(boss.submitError).toContain("kimi_unavailable");
  });
});

describe("loadNextQuestion", () => {
  it("populates currentQuestion + currentDifficulty on a 200", async () => {
    useRuntimeStore.setState((st) => ({
      boss: { ...st.boss, bossSessionId: "bs_1" },
    }));
    stageResponses([
      okResponse({
        question_id: "gbq_42",
        question_text: "Why does 1/2 ÷ 4 equal 1/8?",
        target_skill: "fraction_division",
        difficulty: "hard",
        why_this_question: "weak_topic_match",
        boss_session_id: "bs_1",
      }),
    ]);

    await useRuntimeStore.getState().loadNextQuestion();

    const boss = useRuntimeStore.getState().boss;
    expect(boss.currentQuestion?.question_id).toBe("gbq_42");
    expect(boss.currentDifficulty).toBe("hard");
    expect(boss.attemptNumber).toBe(1);
    expect(boss.lastResult).toBeNull();
    expect(boss.loadingQuestion).toBe(false);
    expect(boss.generateError).toBeNull();
  });

  it("surfaces 502 retry exhaustion as generateError (Boss Arena §10 — no static fallback)", async () => {
    useRuntimeStore.setState((st) => ({
      boss: { ...st.boss, bossSessionId: "bs_1" },
    }));
    stageResponses([errResponse(502, "boss question generation failed: language_drift")]);

    await useRuntimeStore.getState().loadNextQuestion();

    const boss = useRuntimeStore.getState().boss;
    expect(boss.loadingQuestion).toBe(false);
    expect(boss.currentQuestion).toBeNull();
    expect(boss.generateError).toMatch(/regrouping|try again/i);
  });

  it("no-ops when bossSessionId is null (defensive — should not happen in practice)", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);

    await useRuntimeStore.getState().loadNextQuestion();

    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("bossAnswer", () => {
  // Helper: seed an active session with one question loaded.
  function seedActiveSession() {
    useRuntimeStore.setState((st) => ({
      boss: {
        ...st.boss,
        bossSessionId: "bs_1",
        hp: 100,
        maxHp: 100,
        trialsLeft: 5,
        currentDifficulty: "medium",
        currentQuestion: {
          question_id: "gbq_1",
          question_text: "Q",
          target_skill: "s",
          difficulty: "medium",
          why_this_question: "",
          boss_session_id: "bs_1",
        },
        status: "fighting",
      },
    }));
  }

  it("on a non-terminal correct hit: assigns absolute HP from server, auto-loads next question", async () => {
    seedActiveSession();
    stageResponses([
      // /boss/submit-answer
      okResponse({
        is_correct: true,
        score: 1.0,
        confidence: 0.9,
        feedback: "Solid.",
        damage: 30,
        hp: 70,
        trials_left: 4,
        current_difficulty: "medium",
        boss_status: "active",
        should_retry_same_skill: false,
        misconception_tags: [],
        outcome: null,
        stars: null,
        outcome_xp: null,
      }),
      // /boss/generate-question (auto-chained)
      okResponse({
        question_id: "gbq_2",
        question_text: "Next question.",
        target_skill: "s",
        difficulty: "medium",
        why_this_question: "",
        boss_session_id: "bs_1",
      }),
    ]);

    const res = await useRuntimeStore.getState().bossAnswer("Because.");

    const boss = useRuntimeStore.getState().boss;
    expect(res?.is_correct).toBe(true);
    expect(boss.hp).toBe(70); // ABSOLUTE — not 100 - 30 client computation
    expect(boss.trialsLeft).toBe(4);
    expect(boss.status).toBe("fighting");
    expect(boss.lastResult?.damage).toBe(30);
    // Auto-chain: the next question replaced the previous one.
    expect(boss.currentQuestion?.question_id).toBe("gbq_2");
  });

  it("on a wrong answer (still active): consumes a trial and auto-loads a NEW question", async () => {
    seedActiveSession();
    stageResponses([
      okResponse({
        is_correct: false,
        score: 0.0,
        confidence: 0.85,
        feedback: "Not quite.",
        damage: 0,
        hp: 100,
        trials_left: 4,
        current_difficulty: "medium",
        boss_status: "active",
        // should_retry_same_skill: true signals the NEXT generated question
        // targets the same skill — NOT that this question is re-asked.
        should_retry_same_skill: true,
        misconception_tags: ["misreads_question"],
        outcome: null,
        stars: null,
        outcome_xp: null,
      }),
      okResponse({
        question_id: "gbq_3",
        question_text: "Try this framing.",
        target_skill: "s",
        difficulty: "medium",
        why_this_question: "same_skill_retry",
        boss_session_id: "bs_1",
      }),
    ]);

    await useRuntimeStore.getState().bossAnswer("wrong");

    const boss = useRuntimeStore.getState().boss;
    expect(boss.lastResult?.is_correct).toBe(false);
    expect(boss.trialsLeft).toBe(4);
    expect(boss.status).toBe("fighting");
    // Critical Plan-5 contract: wrong answer = NEW question, NOT a retry of gbq_1.
    expect(boss.currentQuestion?.question_id).toBe("gbq_3");
  });

  it("on terminal win: flips status to won, surfaces outcome/stars/outcome_xp, does NOT auto-load", async () => {
    seedActiveSession();
    const fetchMock = stageResponses([
      okResponse({
        is_correct: true,
        score: 1.0,
        confidence: 0.95,
        feedback: "Victory.",
        damage: 100,
        hp: 0,
        trials_left: 3,
        current_difficulty: "hard",
        boss_status: "won",
        should_retry_same_skill: false,
        misconception_tags: [],
        outcome: "expert",
        stars: 3,
        outcome_xp: 5000,
      }),
    ]);

    await useRuntimeStore.getState().bossAnswer("Final answer.");

    const boss = useRuntimeStore.getState().boss;
    expect(boss.status).toBe("won");
    expect(boss.hp).toBe(0);
    expect(boss.lastResult?.outcome).toBe("expert");
    expect(boss.lastResult?.stars).toBe(3);
    expect(boss.lastResult?.outcome_xp).toBe(5000);
    // No auto-chain on terminal — only one fetch call should have fired.
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("on terminal failure: flips status to lost and skips auto-load", async () => {
    seedActiveSession();
    const fetchMock = stageResponses([
      okResponse({
        is_correct: false,
        score: 0.0,
        confidence: 0.8,
        feedback: "Out of trials.",
        damage: 0,
        hp: 50,
        trials_left: 0,
        current_difficulty: "medium",
        boss_status: "failed",
        should_retry_same_skill: false,
        misconception_tags: [],
        outcome: "needs_review",
        stars: 0,
        outcome_xp: 500,
      }),
    ]);

    await useRuntimeStore.getState().bossAnswer("guess");

    const boss = useRuntimeStore.getState().boss;
    expect(boss.status).toBe("lost");
    expect(boss.trialsLeft).toBe(0);
    expect(fetchMock).toHaveBeenCalledTimes(1); // no auto-load
  });

  it("returns null and does not POST when there is no current question", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);

    const res = await useRuntimeStore.getState().bossAnswer("hello");

    expect(res).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("retryBoss", () => {
  it("calls /boss/start with force_fresh: true and reloads the first question", async () => {
    useRuntimeStore.setState((st) => ({
      boss: {
        ...st.boss,
        bossSessionId: "bs_old",
        status: "lost",
        hp: 0,
        maxHp: 100,
      },
    }));
    const fetchMock = stageResponses([
      okResponse({
        boss_session_id: "bs_fresh",
        hp: 100,
        max_hp: 100,
        trials_left: 5,
        current_difficulty: "medium",
        weak_topics: [],
        strong_topics: [],
        missing_context_flags: [],
      }),
      okResponse({
        question_id: "gbq_retry_1",
        question_text: "Round two.",
        target_skill: "s",
        difficulty: "medium",
        why_this_question: "",
        boss_session_id: "bs_fresh",
      }),
    ]);

    await useRuntimeStore.getState().retryBoss();

    // Body of /boss/start MUST include force_fresh: true.
    const [, init] = fetchMock.mock.calls[0];
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.force_fresh).toBe(true);

    const boss = useRuntimeStore.getState().boss;
    expect(boss.bossSessionId).toBe("bs_fresh");
    expect(boss.status).toBe("fighting");
    expect(boss.hp).toBe(100);
    expect(boss.currentQuestion?.question_id).toBe("gbq_retry_1");
  });
});
