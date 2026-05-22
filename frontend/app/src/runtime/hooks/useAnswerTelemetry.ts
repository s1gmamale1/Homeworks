// useAnswerTelemetry — tiny, dependency-free behavioral-signal collector for the
// process-supervision anti-cheat system. Mirrors hooks/useColorTrail.ts in
// placement + style: a single hook, refs only, full SSR guards.
//
// RESEARCH CONTRACT (docs/NETS_Academic_Integrity_AntiCheat_Research.md):
//   • Behavioral signals are ADVISORY teacher intelligence ONLY.
//   • This hook NEVER blocks, penalizes, gates, or grades the student.
//   • It NEVER touches the server-authoritative store (correctness / gate / hp /
//     combo / unlock). It is ref-based so it can never trigger a re-render and
//     can never feed any flow-control state.
//   • It carries NO correctness claim — only two neutral observations:
//       - client_time_ms : how long the question was on screen before submit.
//       - paste_detected  : whether a paste event fired into the answer field.
//
// The collected telemetry rides along OPTIONAL request fields (the backend
// contract is additive). If the hook isn't wired or the fields are dropped, the
// UI degrades to exactly its prior behavior.

import { useEffect, useRef } from "react";
import type { ClipboardEventHandler } from "react";

/** The two neutral, non-correctness signals collected per answered item. */
export interface AnswerTelemetry {
  /** ms the question was on screen before submit (>= 0, rounded). */
  client_time_ms: number;
  /** Whether a paste event fired into the answer field this question. */
  paste_detected: boolean;
}

// SSR / non-DOM guard: performance.now() is the timing source, but the hook may
// be imported in a non-browser context (tests, SSR). Fall back to Date.now().
const nowMs = (): number =>
  typeof performance !== "undefined" && typeof performance.now === "function"
    ? performance.now()
    : Date.now();

/**
 * Collect lightweight answer telemetry for ONE question/item at a time.
 *
 * @param resetKey  Changes per question/item (e.g. the item index, a blank
 *                  index, or a stable literal for single-question surfaces).
 *                  When it changes, the render timestamp + paste flag reset so
 *                  every item is measured from its own first paint.
 *
 * Returns ref-based handles (no state, never re-renders):
 *   • onPaste — attach to the answer <input>/<textarea>. NEVER preventDefault;
 *               it only OBSERVES that a paste happened (sets the flag).
 *   • markPaste — imperative escape hatch for non-DOM paste paths.
 *   • read    — call at submit time → { client_time_ms, paste_detected }.
 *   • reset   — manually re-baseline (rarely needed; resetKey handles the common
 *               per-item case).
 */
export function useAnswerTelemetry(resetKey: string | number | null): {
  onPaste: ClipboardEventHandler;
  markPaste: () => void;
  read: () => AnswerTelemetry;
  reset: () => void;
} {
  // Render timestamp the current question first appeared at, and whether a paste
  // has fired into its field. Refs — mutating them never schedules a render and
  // never touches the server-authoritative store.
  const renderedAtRef = useRef<number>(nowMs());
  const pastedRef = useRef<boolean>(false);

  const reset = () => {
    renderedAtRef.current = nowMs();
    pastedRef.current = false;
  };

  // Re-baseline whenever the question/item changes. Run synchronously after the
  // new item paints so client_time_ms measures from THIS item's appearance.
  useEffect(() => {
    reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey]);

  const markPaste = () => {
    pastedRef.current = true;
  };

  // Passive observer — sets the flag, NEVER calls preventDefault (paste must
  // still work normally; we only note that it happened).
  const onPaste: ClipboardEventHandler = () => {
    markPaste();
  };

  const read = (): AnswerTelemetry => ({
    client_time_ms: Math.max(0, Math.round(nowMs() - renderedAtRef.current)),
    paste_detected: pastedRef.current,
  });

  return { onPaste, markPaste, read, reset };
}
