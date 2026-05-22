import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import IntegrityNudge from "./IntegrityNudge";

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
