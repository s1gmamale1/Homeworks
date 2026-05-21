// Tests for the Plan-5 dynamic boss API client (bossStart /
// bossGenerateQuestion / bossSubmitAnswer). Pins the request shape (path,
// method, body) and response decoding so a future refactor can't silently
// drift from the Pydantic models at server/routes/ai_plan5.py.
//
// Mocks global.fetch — no real network. Each test is self-contained.

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  bossGenerateQuestion,
  bossStart,
  bossSubmitAnswer,
} from "./api";

// Build a 200-OK Response-like object that the fetch wrapper will accept.
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

// Decode the request body the wrapper sent so we can assert on shape.
function bodyOf(call: ReturnType<typeof vi.fn>["mock"]["calls"][number]): Record<string, unknown> {
  const init = call[1] as RequestInit;
  return JSON.parse(init.body as string);
}

beforeEach(() => {
  // Reset the global fetch mock between tests so call counts don't leak.
  vi.restoreAllMocks();
});

describe("bossStart", () => {
  it("POSTs to /api/ai/boss/start with the required session + homework ids", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      okResponse({
        boss_session_id: "bs_abc123",
        hp: 100,
        max_hp: 100,
        trials_left: 5,
        current_difficulty: "medium",
        weak_topics: [],
        strong_topics: [],
        missing_context_flags: ["no_attempts"],
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const res = await bossStart("sess-1", "HW-001");

    // Path + method
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/ai/boss/start");
    expect((init as RequestInit).method).toBe("POST");

    // Required-only body shape (no optional fields when not passed)
    expect(bodyOf(fetchMock.mock.calls[0])).toEqual({
      session_id: "sess-1",
      homework_id: "HW-001",
    });

    // Response decoded
    expect(res.boss_session_id).toBe("bs_abc123");
    expect(res.hp).toBe(100);
    expect(res.trials_left).toBe(5);
  });

  it("forwards optional max_hp / trials_left / initial_difficulty / force_fresh when provided", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      okResponse({
        boss_session_id: "bs_xyz",
        hp: 50,
        max_hp: 50,
        trials_left: 3,
        current_difficulty: "hard",
        weak_topics: [],
        strong_topics: [],
        missing_context_flags: [],
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await bossStart("sess-2", "HW-002", {
      maxHp: 50,
      trialsLeft: 3,
      initialDifficulty: "hard",
      forceFresh: true,
    });

    // Snake_case mapping for backend Pydantic model
    expect(bodyOf(fetchMock.mock.calls[0])).toEqual({
      session_id: "sess-2",
      homework_id: "HW-002",
      max_hp: 50,
      trials_left: 3,
      initial_difficulty: "hard",
      force_fresh: true,
    });
  });
});

describe("bossGenerateQuestion", () => {
  it("POSTs to /api/ai/boss/generate-question with boss_session_id + empty phrase list by default", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      okResponse({
        question_id: "gbq_q1",
        question_text: "Why does the method apply?",
        target_skill: "fraction_division",
        difficulty: "medium",
        why_this_question: "weak topic",
        boss_session_id: "bs_abc123",
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const res = await bossGenerateQuestion("bs_abc123");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/ai/boss/generate-question");
    expect(bodyOf(fetchMock.mock.calls[0])).toEqual({
      boss_session_id: "bs_abc123",
      recent_boss_phrases: [],
    });
    expect(res.question_id).toBe("gbq_q1");
    expect(res.target_skill).toBe("fraction_division");
  });

  it("forwards recent_boss_phrases when supplied", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      okResponse({
        question_id: "gbq_q2",
        question_text: "...",
        target_skill: "x",
        difficulty: "medium",
        why_this_question: "...",
        boss_session_id: "bs_abc",
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await bossGenerateQuestion("bs_abc", ["The boss laughs.", "Strike harder."]);

    expect(bodyOf(fetchMock.mock.calls[0])).toEqual({
      boss_session_id: "bs_abc",
      recent_boss_phrases: ["The boss laughs.", "Strike harder."],
    });
  });

  it("throws ApiError on a 502 — anti-repetition / floor-violation retry exhaustion", async () => {
    // Boss Arena spec §10 forbids static fallback. The UI must surface this
    // failure as a user-triggered retry, which means the API client MUST throw
    // (not silently return a default shape) so the caller can branch.
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      errResponse(502, "boss question generation failed: difficulty_below_skill_floor")
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(bossGenerateQuestion("bs_xyz")).rejects.toBeInstanceOf(ApiError);
    await expect(bossGenerateQuestion("bs_xyz")).rejects.toMatchObject({
      status: 502,
    });
  });
});

describe("bossSubmitAnswer", () => {
  it("POSTs to /api/ai/boss/submit-answer with all three required fields", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      okResponse({
        is_correct: true,
        score: 1.0,
        confidence: 0.92,
        feedback: "Strong reasoning.",
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
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const res = await bossSubmitAnswer("bs_abc", "gbq_q1", "Because a/b ÷ n = a/(b×n).");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/ai/boss/submit-answer");
    expect(bodyOf(fetchMock.mock.calls[0])).toEqual({
      boss_session_id: "bs_abc",
      question_id: "gbq_q1",
      student_answer: "Because a/b ÷ n = a/(b×n).",
    });

    // Server is HP-authoritative — response surfaces absolute HP, not a delta.
    expect(res.hp).toBe(70);
    expect(res.damage).toBe(30);
    expect(res.boss_status).toBe("active");
  });

  it("decodes terminal-status responses with outcome / stars / outcome_xp populated", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      okResponse({
        is_correct: true,
        score: 1.0,
        confidence: 0.95,
        feedback: "Victory.",
        damage: 70,
        hp: 0,
        trials_left: 2,
        current_difficulty: "hard",
        boss_status: "won",
        should_retry_same_skill: false,
        misconception_tags: [],
        outcome: "expert",
        stars: 3,
        outcome_xp: 5000,
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const res = await bossSubmitAnswer("bs_abc", "gbq_final", "Full explanation.");

    expect(res.boss_status).toBe("won");
    expect(res.outcome).toBe("expert");
    expect(res.stars).toBe(3);
    expect(res.outcome_xp).toBe(5000);
  });
});
