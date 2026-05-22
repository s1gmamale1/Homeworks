// Dynamic Boss (Plan 5) API client tests — each method must POST the right
// path + body, surface a 502 as ApiError.status === 502, and (critically)
// NEVER send an answer key. The only student-supplied field that leaves the
// client is `student_answer` (the student's OWN text).

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  ApiError,
  bossStart,
  bossGenerateQuestion,
  bossSubmitAnswer,
  bossState,
  bossGiveUp,
} from "./api";

type FetchCall = { url: string; init: RequestInit };

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "ERR",
    json: async () => body,
  } as Response;
}

function lastCall(): FetchCall {
  const mock = globalThis.fetch as ReturnType<typeof vi.fn>;
  const [url, init] = mock.mock.calls[mock.mock.calls.length - 1] as [string, RequestInit];
  return { url, init };
}

function bodyOf(call: FetchCall): Record<string, unknown> {
  return JSON.parse(String(call.init.body));
}

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

describe("bossStart", () => {
  it("POSTs /api/ai/boss/start with session + homework", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
        boss_session_id: "bs_1",
        hp: 100,
        max_hp: 100,
        trials_left: 7,
        current_difficulty: "medium",
        weak_topics: [],
        strong_topics: [],
        missing_context_flags: [],
      })
    );
    const res = await bossStart({ sessionId: "s1", homeworkId: "hw1" });
    const call = lastCall();
    expect(call.url).toBe("/api/ai/boss/start");
    expect(call.init.method).toBe("POST");
    const body = bodyOf(call);
    expect(body).toMatchObject({ session_id: "s1", homework_id: "hw1" });
    expect(res.boss_session_id).toBe("bs_1");
  });

  it("only sends max_hp when provided, and force_fresh when true", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
        boss_session_id: "bs_2",
        hp: 80,
        max_hp: 80,
        trials_left: 5,
        current_difficulty: "easy",
        weak_topics: [],
        strong_topics: [],
        missing_context_flags: [],
      })
    );
    await bossStart({ sessionId: "s1", homeworkId: "hw1" });
    expect(bodyOf(lastCall())).not.toHaveProperty("max_hp");
    expect(bodyOf(lastCall())).not.toHaveProperty("force_fresh");

    await bossStart({ sessionId: "s1", homeworkId: "hw1", maxHp: 120, forceFresh: true });
    const body = bodyOf(lastCall());
    expect(body.max_hp).toBe(120);
    expect(body.force_fresh).toBe(true);
  });
});

describe("bossGenerateQuestion", () => {
  it("POSTs /api/ai/boss/generate-question with the session id", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
        question_id: "q1",
        question_text: "Define X.",
        scenario: "A scenario.",
        why: "Why?",
        how: "How?",
        what: "What?",
        target_skill: "skill",
        difficulty: "medium",
        why_this_question: "weak topic",
        boss_session_id: "bs_1",
      })
    );
    const res = await bossGenerateQuestion({ bossSessionId: "bs_1" });
    const call = lastCall();
    expect(call.url).toBe("/api/ai/boss/generate-question");
    expect(bodyOf(call)).toEqual({ boss_session_id: "bs_1" });
    expect(res.question_id).toBe("q1");
  });

  it("surfaces a 502 as ApiError with status 502", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({ detail: "generation exhausted" }, 502)
    );
    await expect(bossGenerateQuestion({ bossSessionId: "bs_1" })).rejects.toMatchObject({
      status: 502,
    });
    // And it's specifically an ApiError instance.
    try {
      (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
        jsonResponse({ detail: "again" }, 502)
      );
      await bossGenerateQuestion({ bossSessionId: "bs_1" });
      throw new Error("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(502);
    }
  });

  it("forwards recent_boss_phrases only when non-empty", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
        question_id: "q2",
        question_text: "Q",
        target_skill: "s",
        difficulty: "hard",
        why_this_question: "w",
        boss_session_id: "bs_1",
      })
    );
    await bossGenerateQuestion({ bossSessionId: "bs_1", recentBossPhrases: [] });
    expect(bodyOf(lastCall())).not.toHaveProperty("recent_boss_phrases");

    await bossGenerateQuestion({ bossSessionId: "bs_1", recentBossPhrases: ["So…"] });
    expect(bodyOf(lastCall()).recent_boss_phrases).toEqual(["So…"]);
  });
});

describe("bossSubmitAnswer", () => {
  it("POSTs /api/ai/boss/submit-answer with exactly the student answer + ids", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
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
      })
    );
    await bossSubmitAnswer({
      bossSessionId: "bs_1",
      questionId: "q1",
      studentAnswer: "Why: a\nHow: b\nWhat: c",
    });
    const call = lastCall();
    expect(call.url).toBe("/api/ai/boss/submit-answer");
    const body = bodyOf(call);
    expect(body).toEqual({
      boss_session_id: "bs_1",
      question_id: "q1",
      student_answer: "Why: a\nHow: b\nWhat: c",
    });
  });

  it("NEVER sends an answer/expected/rubric key — only student_answer", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
        is_correct: false,
        score: 0,
        confidence: 0.8,
        feedback: "No.",
        damage: 0,
        hp: 100,
        trials_left: 4,
        current_difficulty: "medium",
        boss_status: "active",
        should_retry_same_skill: true,
        misconception_tags: ["x"],
      })
    );
    await bossSubmitAnswer({
      bossSessionId: "bs_1",
      questionId: "q1",
      studentAnswer: "guess",
    });
    const body = bodyOf(lastCall());
    const keys = Object.keys(body);
    for (const forbidden of ["expected", "expected_answer", "rubric", "answer", "answer_spec", "correct", "accepted_answers"]) {
      expect(keys).not.toContain(forbidden);
    }
    expect(keys.sort()).toEqual(["boss_session_id", "question_id", "student_answer"]);
  });
});

describe("bossState / bossGiveUp", () => {
  it("bossState POSTs /api/ai/boss/state with the session id", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
        boss_session_id: "bs_1",
        session_id: "s1",
        homework_id: "hw1",
        status: "active",
        hp: 60,
        max_hp: 100,
        trials_left: 3,
        current_difficulty: "hard",
      })
    );
    await bossState("bs_1");
    const call = lastCall();
    expect(call.url).toBe("/api/ai/boss/state");
    expect(bodyOf(call)).toEqual({ boss_session_id: "bs_1" });
  });

  it("bossGiveUp POSTs /api/ai/boss/give-up with the session id", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
        boss_session_id: "bs_1",
        session_id: "s1",
        homework_id: "hw1",
        status: "abandoned",
        hp: 60,
        max_hp: 100,
        trials_left: 3,
        current_difficulty: "hard",
      })
    );
    await bossGiveUp("bs_1");
    const call = lastCall();
    expect(call.url).toBe("/api/ai/boss/give-up");
    expect(bodyOf(call)).toEqual({ boss_session_id: "bs_1" });
  });
});
