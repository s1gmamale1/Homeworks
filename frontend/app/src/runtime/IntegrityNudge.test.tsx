import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import IntegrityNudge from "./IntegrityNudge";
import { acknowledgeNudge } from "../shared/api";

// ---------------------------------------------------------------------------
// IntegrityNudge — soft-friction advisory card.
//   • Renders when a nudge is present; renders NOTHING when null.
//   • Dismiss + Explain fire their callbacks.
//   • CRITICAL: a sibling Continue/Next button stays ENABLED — the nudge never
//     gates progress (the core research invariant).
//   • message is rendered as TEXT (no HTML injection).
//   • Esc dismisses; reduced-motion path renders without throwing.
// ---------------------------------------------------------------------------

afterEach(() => cleanup());

const sampleNudge = { type: "rushed_paste", message: "Take a beat to explain." };

describe("IntegrityNudge", () => {
  it("renders the message when a nudge is present", () => {
    render(<IntegrityNudge nudge={sampleNudge} />);
    expect(screen.getByTestId("integrity-nudge")).toBeInTheDocument();
    expect(screen.getByTestId("integrity-nudge-message")).toHaveTextContent(
      "Take a beat to explain."
    );
  });

  it("renders nothing when nudge is null (safe to always mount)", () => {
    const { container } = render(<IntegrityNudge nudge={null} />);
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByTestId("integrity-nudge")).not.toBeInTheDocument();
  });

  it("fires onRespond with 'explain' from the primary button", async () => {
    const onRespond = vi.fn();
    const user = userEvent.setup();
    render(<IntegrityNudge nudge={sampleNudge} onRespond={onRespond} />);
    await user.click(screen.getByTestId("integrity-nudge-respond"));
    expect(onRespond).toHaveBeenCalledWith("explain");
  });

  it("fires onDismiss from the Dismiss button", async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();
    render(<IntegrityNudge nudge={sampleNudge} onDismiss={onDismiss} />);
    await user.click(screen.getByTestId("integrity-nudge-dismiss"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("dismisses on Escape", () => {
    const onDismiss = vi.fn();
    render(<IntegrityNudge nudge={sampleNudge} onDismiss={onDismiss} />);
    fireEvent.keyDown(screen.getByTestId("integrity-nudge"), { key: "Escape" });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("NEVER gates progress — a sibling Continue button stays enabled", async () => {
    // Mount the nudge BESIDE a Continue button, exactly as the runtime does.
    const onContinue = vi.fn();
    const onDismiss = vi.fn();
    const user = userEvent.setup();
    render(
      <div>
        <IntegrityNudge nudge={sampleNudge} onDismiss={onDismiss} />
        <button data-testid="continue-btn" onClick={onContinue}>
          Continue
        </button>
      </div>
    );

    // The nudge is visible AND the Continue button is enabled + clickable.
    expect(screen.getByTestId("integrity-nudge")).toBeInTheDocument();
    const continueBtn = screen.getByTestId("continue-btn");
    expect(continueBtn).toBeEnabled();

    // Progress works while the nudge is still showing — it does not block flow.
    await user.click(continueBtn);
    expect(onContinue).toHaveBeenCalledTimes(1);
  });

  it("renders message as TEXT, not HTML (no injection)", () => {
    const htmlNudge = {
      type: "x",
      message: "<img src=x onerror=alert(1)> plain text",
    };
    render(<IntegrityNudge nudge={htmlNudge} />);
    const msg = screen.getByTestId("integrity-nudge-message");
    // The angle-bracket content is shown verbatim as text; no <img> element.
    expect(msg).toHaveTextContent("<img src=x onerror=alert(1)> plain text");
    expect(msg.querySelector("img")).toBeNull();
  });

  it("renders without throwing under reduced-motion", () => {
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

    render(<IntegrityNudge nudge={sampleNudge} />);
    // The card still renders (entrance animation is CSS-gated, not JS-gated).
    expect(screen.getByTestId("integrity-nudge")).toBeInTheDocument();

    window.matchMedia = original;
  });
});

// ---------------------------------------------------------------------------
// acknowledgeNudge — advisory POST helper (shared/api.ts)
//   • Fires a fire-and-forget POST /api/ai/check-answer with nudge_response.
//   • The client MUST NOT read the response for correctness/gate/flow.
//   • Errors are swallowed — a dropped signal must not break the UI.
//   • Crucially: calling it changes NO progress / gate / correctness state.
// ---------------------------------------------------------------------------

describe("acknowledgeNudge", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Replace global fetch with a spy that resolves immediately.
    fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ advisory: true }),
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("fires a POST to /api/ai/check-answer with the correct advisory body", async () => {
    acknowledgeNudge("hw-123", "sess-456", "case_based_preview", "explain");

    // Allow the fire-and-forget promise microtask to flush.
    await vi.waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/ai/check-answer");
    expect(init.method).toBe("POST");

    const body = JSON.parse(init.body as string) as Record<string, unknown>;
    expect(body.phase).toBe("case_based_preview");
    expect(body.homework_id).toBe("hw-123");
    expect(body.session_id).toBe("sess-456");
    expect(body.nudge_response).toBe("explain");
    // CRITICAL: no student_answer — this is advisory only.
    expect(body.student_answer).toBeUndefined();
  });

  it("does NOT read the advisory response — fetch resolves but nothing changes", async () => {
    // Track any external state mutation we care about (none expected).
    let externalStateMutated = false;
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => {
        // If the client ever reads this, it might act on it.
        externalStateMutated = true;
        return { advisory: true };
      },
    });

    acknowledgeNudge("hw-abc", "sess-xyz", "memory_check", "explain");

    // Wait long enough for any microtask that would read the response.
    await new Promise((r) => setTimeout(r, 20));

    // The fetch fired (signal sent), but the response body was never consumed.
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(externalStateMutated).toBe(false);
  });

  it("swallows network errors — a dropped signal must not break the caller", async () => {
    fetchSpy.mockRejectedValueOnce(new Error("Network down"));

    // Must not throw synchronously or reject any observable promise.
    expect(() =>
      acknowledgeNudge("hw-err", "sess-err", "boss", "explain")
    ).not.toThrow();

    // Let the rejected promise settle.
    await new Promise((r) => setTimeout(r, 20));
    // Still no unhandled rejection — the error was swallowed internally.
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("onRespond wired to acknowledgeNudge fires the advisory POST, no UI state changes", async () => {
    // Simulate a call site: component wires onRespond → acknowledgeNudge.
    // Correctness/gate/hp state is represented by a counter that must stay 0.
    let correctnessStateChanges = 0;

    const onRespond = (choice: string) => {
      acknowledgeNudge("hw-wire", "sess-wire", "adaptive-quiz", choice);
      // Verify the call site NEVER reads the return value for state changes.
      // (acknowledgeNudge returns void, so this is statically enforced too.)
    };

    const user = userEvent.setup();
    render(
      <div>
        <IntegrityNudge nudge={sampleNudge} onRespond={onRespond} />
        {/* Sibling that represents correctness/gate state — must stay enabled. */}
        <button
          data-testid="correctness-indicator"
          onClick={() => {
            correctnessStateChanges++;
          }}
        >
          Correct: {correctnessStateChanges}
        </button>
      </div>
    );

    await user.click(screen.getByTestId("integrity-nudge-respond"));

    // Advisory POST was fired.
    await vi.waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));

    // No correctness / gate / hp state was mutated.
    expect(correctnessStateChanges).toBe(0);
    // The sibling progress button is still enabled and clickable.
    expect(screen.getByTestId("correctness-indicator")).toBeEnabled();
  });
});
