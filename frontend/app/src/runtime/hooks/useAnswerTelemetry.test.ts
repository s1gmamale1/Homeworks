import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAnswerTelemetry } from "./useAnswerTelemetry";

// ---------------------------------------------------------------------------
// useAnswerTelemetry — the advisory anti-cheat signal collector.
//   • client_time_ms is positive and grows with time on screen.
//   • onPaste flips paste_detected (without preventing default).
//   • a resetKey change re-baselines BOTH timing and the paste flag.
// These guard the research invariant that the hook is a neutral OBSERVER:
// no correctness, no flow control — just timing + paste.
//
// The hook reads performance.now(); we drive a controllable fake clock so
// timing assertions are deterministic.
// ---------------------------------------------------------------------------

let fakeNow = 0;
let originalNow: typeof performance.now;

beforeEach(() => {
  fakeNow = 1000; // arbitrary non-zero baseline
  originalNow = performance.now;
  performance.now = () => fakeNow;
});

afterEach(() => {
  performance.now = originalNow;
});

describe("useAnswerTelemetry", () => {
  it("read() returns a positive client_time_ms after time on screen", () => {
    const { result } = renderHook(() => useAnswerTelemetry("q1"));

    // Advance the fake clock by 1500ms after the hook captured its baseline.
    fakeNow += 1500;

    const tele = result.current.read();
    expect(tele.client_time_ms).toBe(1500);
    expect(tele.client_time_ms).toBeGreaterThan(0);
    expect(tele.paste_detected).toBe(false);
  });

  it("onPaste sets paste_detected and never calls preventDefault", () => {
    const { result } = renderHook(() => useAnswerTelemetry("q1"));
    expect(result.current.read().paste_detected).toBe(false);

    const preventDefault = vi.fn();
    act(() => {
      result.current.onPaste({ preventDefault } as never);
    });

    expect(result.current.read().paste_detected).toBe(true);
    // The hook only OBSERVES — it must never block the paste.
    expect(preventDefault).not.toHaveBeenCalled();
  });

  it("markPaste() flips the flag imperatively", () => {
    const { result } = renderHook(() => useAnswerTelemetry("q1"));
    act(() => {
      result.current.markPaste();
    });
    expect(result.current.read().paste_detected).toBe(true);
  });

  it("a resetKey change re-baselines both timing and the paste flag", () => {
    let key = "q1";
    const { result, rerender } = renderHook(() => useAnswerTelemetry(key));

    // Paste + let time pass on the first question.
    act(() => {
      result.current.markPaste();
    });
    fakeNow += 3000;
    expect(result.current.read().paste_detected).toBe(true);
    expect(result.current.read().client_time_ms).toBe(3000);

    // Move to a new question → the effect re-baselines on the new resetKey.
    key = "q2";
    act(() => {
      rerender();
    });

    const afterReset = result.current.read();
    expect(afterReset.paste_detected).toBe(false);
    // Timing restarts at zero (re-baselined at the current fake clock).
    expect(afterReset.client_time_ms).toBe(0);
  });

  it("reset() manually re-baselines", () => {
    const { result } = renderHook(() => useAnswerTelemetry("q1"));
    act(() => {
      result.current.markPaste();
    });
    fakeNow += 2000;
    act(() => {
      result.current.reset();
    });
    const tele = result.current.read();
    expect(tele.paste_detected).toBe(false);
    expect(tele.client_time_ms).toBe(0);
  });

  it("never returns a negative client_time_ms (clamped at 0)", () => {
    const { result } = renderHook(() => useAnswerTelemetry("q1"));
    // Clock goes backwards (e.g. a flaky monotonic source) → clamp to 0.
    fakeNow -= 500;
    expect(result.current.read().client_time_ms).toBe(0);
  });
});
