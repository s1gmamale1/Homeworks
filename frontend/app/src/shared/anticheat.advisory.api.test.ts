// Advisory-only guarantee at the API boundary: the FE NEVER sends a correctness
// claim. Every submit body carries the student's own answer + OPTIONAL advisory
// telemetry (timing/paste). Telemetry is ADDITIVE — omitted entirely when not
// provided, so existing callers send an identical body.
//
// Research contract: docs/NETS_Academic_Integrity_AntiCheat_Research.md.

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  submitCheckpoint,
  submitMemoryCheckItem,
  submitReasoning,
  bossSubmitAnswer,
} from "./api";

function jsonResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => body,
  } as Response;
}

function lastBody(): Record<string, unknown> {
  const mock = globalThis.fetch as ReturnType<typeof vi.fn>;
  const [, init] = mock.mock.calls[mock.mock.calls.length - 1] as [string, RequestInit];
  return JSON.parse(String(init.body));
}

// The FE must never put any of these (a correctness claim or an answer key) on
// the wire — correctness/gating is 100% server-decided.
const FORBIDDEN = [
  "correct",
  "is_correct",
  "expected",
  "expected_answer",
  "rubric",
  "answer",
  "answer_spec",
  "accepted_answers",
];

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

describe("anti-cheat advisory — submit bodies carry no correctness claim", () => {
  it("submitCheckpoint omits telemetry when none is passed", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({ correct: true, feedback: "ok", learning_block: null })
    );
    await submitCheckpoint("hw1", "s1", 0, "A");
    const body = lastBody();
    for (const k of FORBIDDEN) expect(body).not.toHaveProperty(k);
    expect(body).not.toHaveProperty("client_time_ms");
    expect(body).not.toHaveProperty("paste_detected");
    expect(body.student_answer).toBe("A");
  });

  it("submitCheckpoint adds advisory telemetry when provided (never a verdict)", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({ correct: false, feedback: "no", learning_block: null })
    );
    await submitCheckpoint("hw1", "s1", 1, "B", {
      client_time_ms: 1234,
      paste_detected: true,
    });
    const body = lastBody();
    for (const k of FORBIDDEN) expect(body).not.toHaveProperty(k);
    expect(body.client_time_ms).toBe(1234);
    expect(body.paste_detected).toBe(true);
  });

  it("submitMemoryCheckItem carries only answer + the telemetry keys provided", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({ correct: true, feedback: "ok", learning_block: null })
    );
    await submitMemoryCheckItem("hw1", "s1", 2, "cat", { client_time_ms: 50 });
    const body = lastBody();
    for (const k of FORBIDDEN) expect(body).not.toHaveProperty(k);
    expect(body.student_answer).toBe("cat");
    expect(body.client_time_ms).toBe(50);
    // paste flag absent here → must NOT appear in the body.
    expect(body).not.toHaveProperty("paste_detected");
  });

  it("submitReasoning carries only reasoning_text + optional telemetry", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({ passed: true, score: 90, feedback: "ok" })
    );
    await submitReasoning("hw1", "s1", "because X", { paste_detected: false });
    const body = lastBody();
    for (const k of FORBIDDEN) expect(body).not.toHaveProperty(k);
    expect(body.reasoning_text).toBe("because X");
    expect(body.paste_detected).toBe(false);
    expect(body).not.toHaveProperty("client_time_ms");
  });

  it("bossSubmitAnswer carries only student_answer + optional telemetry", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({
        is_correct: true,
        score: 1,
        confidence: 0.9,
        feedback: "ok",
        damage: 10,
        hp: 90,
        trials_left: 5,
        current_difficulty: "medium",
        boss_status: "active",
        should_retry_same_skill: false,
        misconception_tags: [],
      })
    );
    await bossSubmitAnswer({
      bossSessionId: "bs1",
      questionId: "q1",
      studentAnswer: "the answer",
      clientTimeMs: 999,
      pasteDetected: true,
    });
    const body = lastBody();
    for (const k of FORBIDDEN) expect(body).not.toHaveProperty(k);
    expect(body.student_answer).toBe("the answer");
    expect(body.client_time_ms).toBe(999);
    expect(body.paste_detected).toBe(true);
  });
});
