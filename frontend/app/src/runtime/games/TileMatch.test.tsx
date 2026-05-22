// Tile Match component tests. The load-bearing scenario is the
// "leave-the-panel-and-come-back" rehydrate path — the server's
// `_TM_ATTEMPTS` dict survives across navigation while the React component
// remounts with an empty matched-set. Without server→client sync on every
// response, returning students see "0/N matched" and every click on a
// previously-matched pair fires wrong-flash with no recovery path.
//
// These tests pin the rehydrate semantics that close that bug:
//   - sync matchedLefts/matchedRights from `res.matched_tokens` on every
//     response (correct / already_matched / wrong-with-prior-progress)
//   - respect `res.complete` regardless of `res.correct`
//   - suppress wrong-flash on `res.already_matched` (no-op replay, not a miss)

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";

// Mock the submitTileMatch fetch wrapper — each test sets the resolved value.
vi.mock("../../shared/api", async () => {
  const actual = await vi.importActual<typeof import("../../shared/api")>(
    "../../shared/api"
  );
  return {
    ...actual,
    submitTileMatch: vi.fn(),
  };
});

import { submitTileMatch } from "../../shared/api";
import { useRuntimeStore } from "../store";
import TileMatch from "./TileMatch";
import type { HydratePayload } from "../../shared/types";

const mockSubmit = submitTileMatch as ReturnType<typeof vi.fn>;

// Four-pair board mirroring HW-20260521-001's tile_match shape.
const LEFTS = [
  { lid: "L01", text: "1/2" },
  { lid: "L02", text: "3/4" },
  { lid: "L03", text: "1/5" },
  { lid: "L04", text: "1/4" },
];
const RIGHTS = [
  { rid: "R01", text: "0.5" },
  { rid: "R02", text: "0.75" },
  { rid: "R03", text: "0.2" },
  { rid: "R04", text: "0.25" },
];

function basePayload(): HydratePayload {
  return {
    id: "HW-001",
    title: "Test homework",
    subject: "math",
    grade: 5,
    lang: "en",
    flow_version: "v2",
    content_json: {
      gb_tile_match: { lefts: LEFTS, rights: RIGHTS },
    },
  };
}

function seedStore() {
  useRuntimeStore.setState({
    hwId: "HW-001",
    sessionId: "sess-1",
    payload: basePayload(),
  });
}

beforeEach(() => {
  mockSubmit.mockReset();
  seedStore();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("matched_tokens rehydrate (return-after-completion)", () => {
  it("syncs all matched tiles + shows completion when the first click after remount hits a previously-matched pair", async () => {
    // Bug repro: student finished Tile Match in a prior session, navigated
    // back to the Hub, returned. React remounted with empty matched-set, but
    // server still has all 4 pairs matched. Their first click — on a pair
    // that's "correct" by their reasoning but already-matched server-side —
    // must NOT show as wrong. Instead, the matched_tokens echo re-bases the
    // UI to ground truth (all 4 matched) and the completion screen renders.
    mockSubmit.mockResolvedValue({
      correct: false,
      already_matched: true,
      hint: null,
      explanation: null,
      matched_count: 4,
      matched_tokens: [
        { lid: "L01", rid: "R01" },
        { lid: "L02", rid: "R02" },
        { lid: "L03", rid: "R03" },
        { lid: "L04", rid: "R04" },
      ],
      total_pairs: 4,
      complete: true,
      outcome: "flawless",
    });

    render(<TileMatch onComplete={() => {}} />);

    // Pre-click sanity: counter shows 0/4.
    expect(screen.getByTestId("tile-match-progress")).toHaveTextContent("0/4 matched");

    // Click the pair the student "knows" is correct (1/2 → 0.5).
    await act(async () => {
      fireEvent.click(screen.getByTestId("tm-left-L01"));
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("tm-right-R01"));
    });

    // After the response: completion screen renders, NO wrong-flash, NO hint.
    await waitFor(() => {
      expect(screen.getByTestId("tile-match-complete")).toBeInTheDocument();
    });
    expect(screen.queryByText(/Not a match/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Every pair locked in/i)).toBeInTheDocument();
  });

  it("syncs partial matched state — student matched 2 in prior session, completes the next pair, sees 3/4", async () => {
    // Mid-game rehydrate. Server returns the THREE pairs now matched (2 prior
    // + the just-completed). UI must reflect all three as locked.
    mockSubmit.mockResolvedValue({
      correct: true,
      hint: null,
      explanation: null,
      matched_count: 3,
      matched_tokens: [
        { lid: "L01", rid: "R01" },
        { lid: "L02", rid: "R02" },
        { lid: "L03", rid: "R03" },
      ],
      total_pairs: 4,
      complete: false,
      outcome: null,
    });

    render(<TileMatch onComplete={() => {}} />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("tm-left-L03"));
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("tm-right-R03"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("tile-match-progress")).toHaveTextContent("3/4 matched");
    });
    // Completion screen NOT shown (still one pair to go).
    expect(screen.queryByTestId("tile-match-complete")).not.toBeInTheDocument();
    // The 2 prior-session tiles + the just-matched one are all in the
    // matched-set (their `disabled` attr is true via matchedLefts/matchedRights).
    expect(screen.getByTestId("tm-left-L01")).toBeDisabled();
    expect(screen.getByTestId("tm-left-L02")).toBeDisabled();
    expect(screen.getByTestId("tm-left-L03")).toBeDisabled();
    expect(screen.getByTestId("tm-left-L04")).not.toBeDisabled();
  });

  it("wrong pair on a fresh board: flashes wrong + shows hint, does NOT pollute matched-set", async () => {
    // Baseline: no rehydrate, server returns a clean wrong response with
    // empty matched_tokens. Must behave like before — wrong-flash + hint.
    mockSubmit.mockResolvedValue({
      correct: false,
      already_matched: false,
      hint: "1/2", // server's "your TRUE partner is …" hint
      explanation: null,
      matched_count: 0,
      matched_tokens: [],
      total_pairs: 4,
      complete: false,
      outcome: null,
    });

    render(<TileMatch onComplete={() => {}} />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("tm-left-L01")); // 1/2
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("tm-right-R04")); // 0.25 — wrong
    });

    await waitFor(() => {
      expect(screen.getByText(/Not a match/i)).toBeInTheDocument();
    });
    expect(screen.getByTestId("tile-match-progress")).toHaveTextContent("0/4 matched");
    expect(screen.queryByTestId("tile-match-complete")).not.toBeInTheDocument();
  });
});
