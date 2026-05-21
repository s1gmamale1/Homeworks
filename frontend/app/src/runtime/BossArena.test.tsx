// React Testing Library tests for the Plan-5 BossArena component. Pins the
// surfaces the PR-3 UI swap introduced:
//   - intro CTA label flips while startBoss is in flight
//   - trials pill renders alongside HP
//   - loading skeleton when /generate-question is pending
//   - turn-result card flips Pill copy by correctness + Next CTA replaces the
//     legacy "Press the attack"
//   - misconception_tags chips on a wrong answer
//   - 502 retry block: "Try again" on first failure, "Refresh" on second
//   - won / lost terminal branches surface their CTAs
//
// We render the real component against a manually-seeded zustand store; the
// store actions themselves are pinned in store.boss-plan5.test.ts. These tests
// focus on DOM, not state transitions.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import BossArena from "./BossArena";
import { useRuntimeStore } from "./store";
import type { HydratePayload, BossSubmitAnswerResponse } from "../shared/types";

const noop = () => {};

function basePayload(): HydratePayload {
  return {
    id: "HW-001",
    title: "Test homework",
    subject: "math",
    grade: 5,
    lang: "en",
    flow_version: "v2",
    content_json: {
      boss_meta: { name: "Kasrlar Bahodiri", intro: "The peak awaits." },
    },
  };
}

// Seed the boss slice with overrides; everything else mirrors initialBoss.
function seedBoss(overrides: Partial<ReturnType<typeof useRuntimeStore.getState>["boss"]>) {
  useRuntimeStore.setState({
    hwId: "HW-001",
    sessionId: "sess-1",
    payload: basePayload(),
    boss: {
      bossSessionId: "bs_1",
      hp: 100,
      maxHp: 100,
      trialsLeft: 5,
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
      consecutiveGenerateFailures: 0,
      ...overrides,
    },
  });
}

beforeEach(() => {
  seedBoss({});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("intro state", () => {
  it("renders the boss name and the Enter the arena CTA", () => {
    seedBoss({ status: "intro" });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-intro")).toBeInTheDocument();
    expect(screen.getByText(/Kasrlar Bahodiri awaits/i)).toBeInTheDocument();
    expect(screen.getByTestId("boss-begin")).toHaveTextContent(/Enter the arena/i);
  });

  it("disables the CTA + flips label to 'Opening the arena…' while startBoss is in flight", () => {
    seedBoss({ status: "intro", submitting: true });
    render(<BossArena onComplete={noop} />);

    const btn = screen.getByTestId("boss-begin");
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent(/Opening the arena/i);
  });
});

describe("fighting — question slot", () => {
  it("renders the server-generated question_text plus trials pill", () => {
    seedBoss({
      status: "fighting",
      trialsLeft: 4,
      currentQuestion: {
        question_id: "gbq_1",
        question_text: "Why does 1/2 ÷ 4 equal 1/8?",
        target_skill: "fraction_division",
        difficulty: "medium",
        why_this_question: "weak_topic",
        boss_session_id: "bs_1",
      },
    });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-fighting")).toBeInTheDocument();
    expect(screen.getByText(/Why does 1\/2 ÷ 4/)).toBeInTheDocument();
    expect(screen.getByTestId("boss-trials")).toHaveTextContent("Trials: 4 left");
    // Answer textarea + Attack button visible when no result is pending.
    expect(screen.getByTestId("boss-answer-input")).toBeInTheDocument();
    expect(screen.getByTestId("boss-attack")).toBeInTheDocument();
  });

  it("renders the loading skeleton while currentQuestion is null + loadingQuestion is true", () => {
    seedBoss({
      status: "fighting",
      currentQuestion: null,
      loadingQuestion: true,
    });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-loading-question")).toBeInTheDocument();
    expect(screen.getByText(/Loading the next question/i)).toBeInTheDocument();
    // No answer textarea while loading.
    expect(screen.queryByTestId("boss-answer-input")).not.toBeInTheDocument();
  });
});

describe("fighting — turn-result feedback", () => {
  function correctResult(): BossSubmitAnswerResponse {
    return {
      is_correct: true,
      score: 1.0,
      confidence: 0.95,
      feedback: "Solid reasoning.",
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
    };
  }

  function wrongResult(): BossSubmitAnswerResponse {
    return {
      is_correct: false,
      score: 0.2,
      confidence: 0.85,
      feedback: "Not quite — re-examine the operation.",
      damage: 0,
      hp: 100,
      trials_left: 4,
      current_difficulty: "medium",
      boss_status: "active",
      should_retry_same_skill: true,
      misconception_tags: ["misreads_question", "skips_step"],
      outcome: null,
      stars: null,
      outcome_xp: null,
    };
  }

  it("on a correct hit: renders the Hit pill + −damage label + Next question CTA", () => {
    seedBoss({
      status: "fighting",
      hp: 70,
      lastResult: correctResult(),
      currentQuestion: {
        question_id: "gbq_2",
        question_text: "Next question text.",
        target_skill: "s",
        difficulty: "medium",
        why_this_question: "",
        boss_session_id: "bs_1",
      },
    });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-turn-result")).toHaveTextContent(/Hit · −30 HP/);
    expect(screen.getByText(/Solid reasoning/)).toBeInTheDocument();
    // Plan-5 contract: "Next question →" replaces the legacy "Press the attack".
    expect(screen.getByTestId("boss-next")).toHaveTextContent(/Next question/);
    expect(screen.queryByText(/Press the attack/i)).not.toBeInTheDocument();
    // The answer textarea is suppressed once a result is on screen.
    expect(screen.queryByTestId("boss-answer-input")).not.toBeInTheDocument();
  });

  it("on a wrong answer: renders 'Wrong · moving on' pill + misconception tags + Next CTA", () => {
    seedBoss({
      status: "fighting",
      lastResult: wrongResult(),
      currentQuestion: {
        question_id: "gbq_3",
        question_text: "New framing.",
        target_skill: "s",
        difficulty: "medium",
        why_this_question: "same_skill_retry",
        boss_session_id: "bs_1",
      },
    });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-turn-result")).toHaveTextContent(/Wrong · moving on/);
    const tags = screen.getByTestId("boss-misconception-tags");
    expect(tags).toHaveTextContent("misreads_question");
    expect(tags).toHaveTextContent("skips_step");
    expect(screen.getByTestId("boss-next")).toBeInTheDocument();
  });
});

describe("fighting — 502 retry UX (Decision 3)", () => {
  it("first failure: shows the Try again button (consecutiveGenerateFailures=1)", () => {
    seedBoss({
      status: "fighting",
      currentQuestion: null,
      generateError: "The boss is regrouping — try again.",
      consecutiveGenerateFailures: 1,
    });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-generate-error")).toBeInTheDocument();
    expect(screen.getByTestId("boss-try-again")).toHaveTextContent(/Try again/);
    expect(screen.queryByTestId("boss-refresh")).not.toBeInTheDocument();
  });

  it("second failure in a row: escalates to the Refresh the page CTA", () => {
    seedBoss({
      status: "fighting",
      currentQuestion: null,
      generateError: "The boss is regrouping — try again.",
      consecutiveGenerateFailures: 2,
    });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-generate-error")).toHaveTextContent(
      /Boss generation is unavailable/i
    );
    expect(screen.getByTestId("boss-refresh")).toHaveTextContent(/Refresh the page/);
    expect(screen.queryByTestId("boss-try-again")).not.toBeInTheDocument();
  });
});

describe("terminal branches", () => {
  it("won: surfaces stars and the Claim the arc CTA", () => {
    seedBoss({
      status: "won",
      hp: 0,
      lastResult: {
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
      },
    });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-won")).toBeInTheDocument();
    expect(screen.getByLabelText("3 of 3 stars")).toBeInTheDocument();
    expect(screen.getByTestId("boss-finish")).toHaveTextContent(/Claim the arc/);
  });

  it("lost: surfaces the Face it again CTA", () => {
    seedBoss({
      status: "lost",
      hp: 40,
      trialsLeft: 0,
    });
    render(<BossArena onComplete={noop} />);

    expect(screen.getByTestId("boss-lost")).toBeInTheDocument();
    expect(screen.getByTestId("boss-retry")).toHaveTextContent(/Face it again/);
  });
});
