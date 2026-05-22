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

// Mock the API surface TileMatch touches. Each test stages the values it needs.
vi.mock("../../shared/api", async () => {
  const actual = await vi.importActual<typeof import("../../shared/api")>(
    "../../shared/api"
  );
  return {
    ...actual,
    submitTileMatch: vi.fn(),
    getTileMatchState: vi.fn(),
  };
});

import { getTileMatchState, submitTileMatch } from "../../shared/api";
import { useRuntimeStore } from "../store";
import TileMatch from "./TileMatch";
import type { HydratePayload } from "../../shared/types";

const mockSubmit = submitTileMatch as ReturnType<typeof vi.fn>;
const mockState = getTileMatchState as ReturnType<typeof vi.fn>;

// Default fresh-board state probe response — tests that need otherwise
// override mockState.mockResolvedValueOnce / mockResolvedValue before render.
function freshStateResponse() {
  return {
    matched_count: 0,
    matched_tokens: [],
    total_pairs: 4,
    complete: false,
  };
}

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
  mockState.mockReset();
  // Default: assume a fresh board for any test that doesn't override.
  mockState.mockResolvedValue(freshStateResponse());
  seedStore();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("mount-time state probe (navigation rehydrate)", () => {
  it("auto-advances past a completed Tile Match — onComplete fires, board NEVER renders", async () => {
    // Reported repro: student finished Tile Match, returned to the Hub,
    // re-entered the Practice Arc. Old behavior was "0/N matched, every
    // click flashes wrong." Correct behavior is "skip the slot entirely —
    // the server already knows you finished, the runtime should advance."
    //
    // Mount-time probe returns complete=true → onComplete is called → the
    // board markup (board / counter / completion screen / bootstrapping
    // placeholder are all transient) is NEVER user-visible.
    mockState.mockResolvedValue({
      matched_count: 4,
      matched_tokens: [
        { lid: "L01", rid: "R01" },
        { lid: "L02", rid: "R02" },
        { lid: "L03", rid: "R03" },
        { lid: "L04", rid: "R04" },
      ],
      total_pairs: 4,
      complete: true,
    });

    const onComplete = vi.fn();
    render(<TileMatch onComplete={onComplete} />);

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1);
    });
    // The interactive board MUST NOT have been rendered. Counter / column /
    // completion screen are all part of the post-bootstrap board — none of
    // them should appear when the runtime auto-skips.
    expect(screen.queryByTestId("tile-match-progress")).not.toBeInTheDocument();
    expect(screen.queryByTestId("tile-match-complete")).not.toBeInTheDocument();
    expect(screen.queryByTestId("tm-left-L01")).not.toBeInTheDocument();
  });

  it("seeds matchedLefts/matchedRights from a partial probe — student resumes from prior progress", async () => {
    // Mid-game rehydrate via the mount probe: student matched 2 pairs in a
    // prior session, came back. The board renders with those 2 tiles
    // already locked, counter at 2/4, ready for the remaining 2.
    mockState.mockResolvedValue({
      matched_count: 2,
      matched_tokens: [
        { lid: "L01", rid: "R01" },
        { lid: "L02", rid: "R02" },
      ],
      total_pairs: 4,
      complete: false,
    });

    render(<TileMatch onComplete={() => {}} />);

    await waitFor(() => {
      expect(screen.getByTestId("tile-match-progress")).toHaveTextContent("2/4 matched");
    });
    expect(screen.getByTestId("tm-left-L01")).toBeDisabled();
    expect(screen.getByTestId("tm-left-L02")).toBeDisabled();
    expect(screen.getByTestId("tm-left-L03")).not.toBeDisabled();
    expect(screen.getByTestId("tm-left-L04")).not.toBeDisabled();
    expect(screen.queryByTestId("tile-match-complete")).not.toBeInTheDocument();
  });

  it("renders a fresh board when the probe says no prior state", async () => {
    // The default fresh-state mock is set in beforeEach.
    render(<TileMatch onComplete={() => {}} />);
    await waitFor(() => {
      expect(screen.getByTestId("tile-match-progress")).toHaveTextContent("0/4 matched");
    });
    expect(screen.getByTestId("tm-left-L01")).not.toBeDisabled();
    expect(screen.queryByTestId("tile-match-complete")).not.toBeInTheDocument();
  });

  it("falls through to a fresh board when the probe errors (non-fatal)", async () => {
    // A flaky probe must NOT block the student from playing. The submission-
    // time matched_tokens sync still re-bases the UI from the first response.
    mockState.mockRejectedValue(new Error("network blip"));
    render(<TileMatch onComplete={() => {}} />);
    await waitFor(() => {
      expect(screen.getByTestId("tile-match-progress")).toHaveTextContent("0/4 matched");
    });
  });
});

describe("submission-time matched_tokens sync", () => {
  // The mount-time probe resolves async, so submission-time tests must wait
  // for the board to mount (counter visible) before firing clicks. Helper:
  async function waitForBoard() {
    await waitFor(() => {
      expect(screen.getByTestId("tile-match-progress")).toBeInTheDocument();
    });
  }

  it("syncs partial matched state on a correct response — 3/4 after one click on a session that already had 2 matched", async () => {
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
    await waitForBoard();
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
    await waitForBoard();
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
