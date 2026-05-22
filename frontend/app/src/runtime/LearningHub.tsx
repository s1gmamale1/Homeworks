import { useState, useRef, useEffect } from "react";
import { useRuntimeStore } from "./store";
import { useColorTrail } from "./hooks/useColorTrail";
import type { CbpGate, McGate } from "../shared/types";
import {
  primeAudio,
  playDotPop,
  playUnlockFanfare,
  playChainRattle,
  playChainSnap,
  playFireworkCrackle,
} from "./hubSound";
import HubChains, { type HubChainsPhase } from "./HubChains";
import s from "./LearningHub.module.css";

// ---- Reveal choreography timeline (ms) -------------------------------------
// The hidden→reveal sequence that plays the FIRST time the client sees the
// server flip practice_arc_unlocked → true (play-once, non-reduced-motion).
// Two layers drive it in lockstep: the shell's data-unlock="playing" attribute
// (path dots, glow ring, fireworks, CTA) AND a `chainPhase` state threaded into
// the Practices node + <HubChains> overlay (the chained→shake→break beats).
//
//   Beat 1 · Dots draw in    0 → ~900ms   five "trial" dots pop in one-by-one
//                                           toward the about-to-appear node;
//                                           playDotPop(i) fires as each lands.
//   Beat 2 · Node binds      ~900ms       node FADES IN grayed + chained
//                                           (chainPhase "bound", box grayscale).
//   Beat 3 · Chains rattle   ~1500ms      chains jitter + the node shakes;
//                                           playChainRattle() fires (chainPhase
//                                           "rattle").
//   Beat 4 · Chains SNAP     ~2050ms      links break + recoil, padlock drops,
//                                           node goes gray→full violet→green;
//                                           playChainSnap() (chainPhase "snap").
//   Beat 5 · Celebrate       ~2450ms      glow ring expands + fireworks burst +
//                                           CTA scales in; playUnlockFanfare() +
//                                           playFireworkCrackle().
//   Settle                   → ~3700ms    chainPhase "gone", clear playUnlock,
//                                           mark the play-once localStorage flag.
//
// CSS owns the visuals (delays/keyframes keyed off data-unlock="playing" + the
// node's data-chain attribute); JS only schedules the chainPhase transitions,
// the audio cues, and the end-of-sequence cleanup, so the two stay in lockstep.
// Numbers below MUST match LearningHub.module.css §REVEAL.
const REVEAL_DOT_COUNT = 5;
const REVEAL_DOT_START = 60; // first dot lands ~here
const REVEAL_DOT_STEP = 190; // per-dot stagger (matches CSS --d * step) — paced
//                              a touch slower so the dots "slowly pop up"
const REVEAL_CHAIN_BOUND = 900; // node fades in grayed + chained (chainPhase "bound")
const REVEAL_CHAIN_RATTLE = 1500; // chains jitter + node shakes (chainPhase "rattle")
const REVEAL_CHAIN_SNAP = 2050; // chains break, box gray→color (chainPhase "snap")
const REVEAL_CELEBRATE = 2450; // glow ring + fireworks + fanfare + crackle
const REVEAL_TOTAL = 3700; // full sequence length → clears playUnlock + flag

type SectionStatus = "notStarted" | "inProgress" | "passed";

function cbpStatus(g: CbpGate | undefined): SectionStatus {
  if (!g) return "notStarted";
  if (g.passed) return "passed";
  return g.checkpoints_correct > 0 ? "inProgress" : "notStarted";
}

function mcStatus(g: McGate | undefined): SectionStatus {
  if (!g) return "notStarted";
  if (g.passed) return "passed";
  return g.score_pct > 0 ? "inProgress" : "notStarted";
}

// Pull a string field off content_json.meta (typed `unknown` — extra="allow" on
// the backend Meta model lets `topic` ride alongside the declared
// subject_display/section). Returns a trimmed non-empty string or undefined.
function metaStr(meta: unknown, key: string): string | undefined {
  if (meta && typeof meta === "object" && key in (meta as Record<string, unknown>)) {
    const v = (meta as Record<string, unknown>)[key];
    if (typeof v === "string" && v.trim() !== "") return v.trim();
  }
  return undefined;
}

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// The Learning Hub — a Duolingo-flavored, full-screen, mobile-first winding PATH
// of big tactile 3D "pebble" nodes (NOT a card grid). Three stations descend the
// column, gently offset left/right so the eye travels:
//
//   01 · Case-Study        (orange clay 3D-press button)   <- startCbp
//   02 · Flash cards       (blue clay 3D-press button)     <- enterFlashcards
//   03 · Homework Practices (single node — HIDDEN entirely  <- enterPracticeArc
//        while gate.practice_arc_unlocked === false)          (once unlocked)
//
// The whole node IS the button — colored candy fill + a hard colored bottom-edge
// "lip" (box-shadow, no layout shift) that depresses on :active. Status (locked /
// active / done) reads off the server gate via cbpStatus/mcStatus — the hub only
// renders state, it never decides unlock.
//
// CONTRAST CONTRACT (the prior rejection fix preserved): every title is hard ink
// #1d1d1f / white-on-saturated-fill, and the theme-flipping --v2-text* tokens are
// pinned LIGHT on the .shell so a dark-OS visitor can't wash out the headings.
//
// HIDDEN → REVEAL MODEL (the centerpiece). Three render states:
//   • LOCKED  (practice_arc_unlocked === false): the Practices node AND its
//     path-connector segment are FULLY HIDDEN — the winding path simply ends at
//     Flash cards. No chains, no padlock, no grayed placeholder.
//   • UNLOCKING: the first time the hub sees the server flip the boolean → true
//     (per-homework localStorage play-once flag unset, NOT reduced-motion), a
//     single ~3.7s reveal plays — driven by the shell's data-unlock="playing"
//     attribute AND a `chainPhase` threaded into the node + <HubChains> overlay:
//     path dots draw in one-by-one → the node FADES IN grayed + wrapped in
//     chains (bound) → the chains rattle + the node shakes (rattle) → the chains
//     SNAP and the node goes gray→full color (snap) → a glow ring pulses + a
//     firework burst fires + the CTA scales in (celebrate). JS schedules the
//     chainPhase transitions + the audio cues (playDotPop per dot,
//     playChainRattle/Snap, playUnlockFanfare + playFireworkCrackle) + the
//     end-of-sequence cleanup; CSS owns the visuals.
//   • OPEN on return (flag set, OR unlocked under reduced-motion): node + its
//     path segment render STATIC + visible — no draw-in, no fireworks, no sound.
// The localStorage flag is ONLY for animation-play-once; the unlock truth is
// always the server boolean. prefers-reduced-motion skips straight to OPEN.
export function LearningHub() {
  const payload = useRuntimeStore((st) => st.payload);
  const gate = useRuntimeStore((st) => st.gateState);
  const hwId = useRuntimeStore((st) => st.hwId);
  const startCbp = useRuntimeStore((st) => st.startCbp);
  const enterFlashcards = useRuntimeStore((st) => st.enterFlashcards);
  const enterPracticeArc = useRuntimeStore((st) => st.enterPracticeArc);

  const cbp = cbpStatus(gate?.cbp);
  const mc = mcStatus(gate?.mc);
  const unlocked = gate?.practice_arc_unlocked ?? false;
  const mcThreshold = gate?.mc.threshold_pct ?? 60;

  // Additive completion indicator (server-set flags). When the whole journey is
  // done the "X/3 cleared" chip flips to a "Done ✓ / Needs Retry" badge. These
  // flags are optional + additive to gate_state — absent on older payloads, in
  // which case the chip stays in its "X/3 cleared" form. Minimal additive touch.
  const allDone = gate?.all_divisions_complete ?? false;
  const reflectionPassed = gate?.reflection_passed ?? false;

  // ---- Homework-theme header (subject eyebrow · real title · topic) ----
  const meta = payload?.content_json.meta;
  const subjectEyebrow =
    metaStr(meta, "subject_display") ?? payload?.subject?.trim() ?? undefined;
  const homeworkTitle = payload?.title?.trim() || "Your homework";
  const themeSub = metaStr(meta, "topic") ?? metaStr(meta, "section") ?? undefined;

  // Overall "stations cleared" chip.
  const cleared = (cbp === "passed" ? 1 : 0) + (mc === "passed" ? 1 : 0) + (unlocked ? 1 : 0);

  // The single next actionable LEARNING node gets the idle bob (max one animated
  // node per view). Case-Study leads; once it's passed, Flash cards leads.
  const nextNode: "case" | "flash" | null =
    cbp !== "passed" ? "case" : mc !== "passed" ? "flash" : null;

  // ---- Prime audio on first hub interaction ----------------------------------
  // Browsers block auto-fired audio until a user gesture. The reveal fanfare
  // fires automatically (off the server gate flip), so we resume/create the
  // shared AudioContext on the visitor's FIRST pointer/touch — a one-time
  // listener, removed on unmount. primeAudio() is a safe no-op if audio is
  // unavailable, so this never affects the visuals.
  useEffect(() => {
    const prime = () => primeAudio();
    window.addEventListener("pointerdown", prime, { once: true, passive: true });
    return () => window.removeEventListener("pointerdown", prime);
  }, []);

  // ---- Fresh server gate on every hub entry (stale-gate fix) -----------------
  // The hub renders status + unlock STRICTLY off the server gate. Refetch it on
  // mount so returning to the hub after a checkpoint (or a sibling tab) always
  // reflects the authoritative state — fixes "checkpoint not marked but D3
  // opened" where a stale in-memory gate let the reveal/unlock fire early. The
  // unlock truth stays the server boolean; this only keeps it current.
  useEffect(() => {
    void useRuntimeStore.getState().refreshGateState();
  }, []);

  // ---- Hidden → reveal: one play-once flag per homework, animation-only -------
  // The flag NEVER decides unlock — that's `unlocked` (server truth). It only
  // gates whether the celebration plays. Key matches the brief exactly.
  const seenKey = `nets_hub_unlock_played_${hwId || "_"}`;
  const [playUnlock, setPlayUnlock] = useState(false);
  // The chained→shake→break choreography phase, threaded into the Practices
  // node + the decorative <HubChains> overlay. Default "gone" = no chains (the
  // static OPEN node + reduced-motion both render with chains absent).
  const [chainPhase, setChainPhase] = useState<HubChainsPhase>("gone");

  useEffect(() => {
    if (!unlocked) return;
    let seen = false;
    try {
      seen = localStorage.getItem(seenKey) === "1";
    } catch {
      seen = false; // private mode / blocked storage → just play it, harmless
    }
    if (seen) return; // already celebrated on this device → render OPEN (static)
    if (prefersReducedMotion()) {
      try {
        localStorage.setItem(seenKey, "1");
      } catch {
        /* ignore */
      }
      // reduced motion → skip the whole sequence: no chains, no glow/fireworks,
      // straight to the static OPEN node. chainPhase stays "gone" and playUnlock
      // stays false, so HubChains renders nothing and the celebration layer
      // never mounts.
      return;
    }

    setPlayUnlock(true); // arm the timeline (CSS plays off data-unlock="playing")

    // Schedule the chainPhase transitions + audio cues to land WITH their visual
    // beats. Each audio call is a safe no-op if audio is unavailable — the
    // visuals never wait on them.
    const timers: ReturnType<typeof setTimeout>[] = [];

    // Beat 1 — path "trial" dots pop in one-by-one (paced slowly).
    for (let i = 0; i < REVEAL_DOT_COUNT; i++) {
      timers.push(
        setTimeout(() => playDotPop(i), REVEAL_DOT_START + i * REVEAL_DOT_STEP),
      );
    }

    // Beat 2 — node fades in grayed + chained.
    timers.push(setTimeout(() => setChainPhase("bound"), REVEAL_CHAIN_BOUND));

    // Beat 3 — chains rattle + the node shakes.
    timers.push(
      setTimeout(() => {
        setChainPhase("rattle");
        playChainRattle();
      }, REVEAL_CHAIN_RATTLE),
    );

    // Beat 4 — chains SNAP; the node transitions gray→full violet→green.
    timers.push(
      setTimeout(() => {
        setChainPhase("snap");
        playChainSnap();
      }, REVEAL_CHAIN_SNAP),
    );

    // Beat 5 — glow ring + fireworks burst + fanfare/crackle.
    timers.push(
      setTimeout(() => {
        playUnlockFanfare();
        playFireworkCrackle();
      }, REVEAL_CELEBRATE),
    );

    // End of sequence → drop the chains, return to the static OPEN state + mark
    // the play-once flag.
    const done = setTimeout(() => {
      setChainPhase("gone");
      setPlayUnlock(false);
      try {
        localStorage.setItem(seenKey, "1"); // mark seen at sequence end
      } catch {
        /* ignore */
      }
    }, REVEAL_TOTAL);
    timers.push(done);

    return () => timers.forEach(clearTimeout);
  }, [unlocked, seenKey]);

  // The shell's single source of animation truth. Three states:
  //   "playing" → the reveal is running (dots/pop/glow/fireworks)
  //   "open"    → unlocked + static (return visit, or reduced-motion)
  //   "locked"  → not unlocked → node + its path segment render NOTHING
  const unlockState = playUnlock ? "playing" : unlocked ? "open" : "locked";

  return (
    <main
      className={s.shell}
      data-hub-theme="light"
      data-unlock={unlockState}
      data-testid="screen-hub"
    >
      {/* Interactive candy backdrop — drifting blobs + living aurora, behind
          everything and pointer-events:none. Never intercepts node taps. */}
      <HubBackdrop />

      {/* Soft luminous backdrop — kept subtle so ink always wins on contrast. */}
      <div className={s.heroGlow} aria-hidden="true" />

      {/* ---- Homework-theme header: subject eyebrow · real title · topic ---- */}
      <header className={s.intro}>
        {subjectEyebrow && <p className={s.eyebrow}>{subjectEyebrow}</p>}
        <h1 className={s.pageTitle}>{homeworkTitle}</h1>
        {themeSub && <p className={s.pageSub}>{themeSub}</p>}
        {allDone ? (
          <p
            className={`${s.progressChip} ${reflectionPassed ? s.progressChipDone : s.progressChipRetry}`}
            data-testid="hub-completion-badge"
            data-complete={reflectionPassed ? "passed" : "needs_retry"}
            aria-label={reflectionPassed ? "Homework complete — passed" : "Homework complete — needs retry"}
          >
            {reflectionPassed ? <CheckGlyph /> : <CrownGlyph />}
            <strong>{reflectionPassed ? "Done" : "Needs Retry"}</strong>
            {reflectionPassed && <span aria-hidden="true">✓</span>}
          </p>
        ) : (
          <p className={s.progressChip} aria-label={`${cleared} of 3 stations cleared`}>
            <CrownGlyph />
            <strong>{cleared}</strong>
            <span>/ 3 cleared</span>
          </p>
        )}
      </header>

      {/* ---- The winding path: connector layer behind, nodes stacked above ---- */}
      <div className={s.path}>
        <PathConnectors
          cbpPassed={cbp === "passed"}
          mcPassed={mc === "passed"}
          unlocked={unlocked}
          revealing={playUnlock}
        />

        {/* ---- 01 · Case-Study (orange clay 3D-press node) ---- */}
        <LearningNode
          num="01"
          title="Case-Study"
          lead="Step into the role. A real scenario, three calls — apply the lesson before the test."
          variant="case"
          status={cbp}
          isNext={nextNode === "case"}
          pct={pctFromCbp(gate?.cbp)}
          meta={`${gate?.cbp.checkpoints_correct ?? 0}/${gate?.cbp.checkpoints_total ?? 3} checkpoints`}
          ctaLabel={cbp === "passed" ? "Review →" : cbp === "inProgress" ? "Continue →" : "Start →"}
          align="left"
          onClick={startCbp}
          testid="hub-start-cbp"
        />

        {/* ---- 02 · Flash cards (blue clay 3D-press node) ---- */}
        <LearningNode
          num="02"
          title="Flash cards"
          lead={`Drill the deck, then prove recall on the Memory Check. Hit ${mcThreshold}% to clear.`}
          variant="flash"
          status={mc}
          isNext={nextNode === "flash"}
          pct={gate?.mc.score_pct ?? 0}
          meta={`${gate?.mc.score_pct ?? 0}% recall`}
          ctaLabel={mc === "passed" ? "Review →" : mc === "inProgress" ? "Continue →" : "Start →"}
          align="right"
          onClick={enterFlashcards}
          testid="hub-start-fc"
        />

        {/* ---- 03 · Homework Practices — HIDDEN while locked; reveals on unlock ---- */}
        {/* While locked the node renders NOTHING (the path ends at Flash cards).
            Once unlocked it appears — fading in grayed + chained during the
            reveal, then breaking free, or static on a return visit. `revealing`
            drives the firework/glow markup; `chainPhase` drives the chain
            overlay + the gray→color transition. The CTA enters the Practice Arc
            (server re-checks the gate + fails closed). */}
        {unlocked && (
          <PracticesNode
            revealing={playUnlock}
            chainPhase={chainPhase}
            onEnter={enterPracticeArc}
          />
        )}
      </div>
    </main>
  );
}

// ---- Interactive decorative backdrop -------------------------------------
// A purely cosmetic layer behind the path: a living aurora wash + 5 soft,
// blurred candy blobs in the blue-brand palette that idle-drift forever (CSS),
// AND react to input via a tiny rAF parallax that writes smoothed offsets to
// two CSS custom properties (--bx / --by) the CSS reads via translate3d:
//   • desktop  → pointer move (parallax follows the cursor, eased)
//   • mobile   → scroll position (no hover on touch, so scroll drives drift)
// Everything is transform/opacity only and the layer is pointer-events:none,
// so it can NEVER block a node tap or the unlock choreography. Under
// prefers-reduced-motion we attach NO listeners and emit a static backdrop.
function HubBackdrop() {
  const layerRef = useRef<HTMLDivElement | null>(null);
  const trailRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    if (prefersReducedMotion()) return; // static backdrop, no input reactivity

    // Target (input-driven) vs. current (smoothed) offsets, normalized -1..1.
    let targetX = 0;
    let targetY = 0;
    let curX = 0;
    let curY = 0;
    let raf = 0;
    let running = false;

    const tick = () => {
      // Critically-damped ease toward target (no spring overshoot, calm feel).
      curX += (targetX - curX) * 0.08;
      curY += (targetY - curY) * 0.08;
      layer.style.setProperty("--bx", curX.toFixed(4));
      layer.style.setProperty("--by", curY.toFixed(4));
      // Keep animating until we've effectively settled, then idle the loop.
      if (Math.abs(targetX - curX) > 0.0005 || Math.abs(targetY - curY) > 0.0005) {
        raf = requestAnimationFrame(tick);
      } else {
        running = false;
      }
    };
    const kick = () => {
      if (running) return;
      running = true;
      raf = requestAnimationFrame(tick);
    };

    // Desktop: pointer parallax. Map cursor → -1..1 about viewport center.
    const onPointer = (e: PointerEvent) => {
      if (e.pointerType === "touch") return; // touch handled by scroll instead
      const w = window.innerWidth || 1;
      const h = window.innerHeight || 1;
      targetX = (e.clientX / w) * 2 - 1;
      targetY = (e.clientY / h) * 2 - 1;
      kick();
    };

    // Mobile: scroll parallax. Map scroll progress → a gentle -1..1 sweep.
    const onScroll = () => {
      const doc = document.documentElement;
      const max = Math.max(1, doc.scrollHeight - doc.clientHeight);
      const p = Math.min(1, Math.max(0, (window.scrollY || 0) / max));
      targetY = p * 2 - 1;
      kick();
    };

    window.addEventListener("pointermove", onPointer, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onPointer);
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  // ---- Pointer/touch COLOR TRAIL --------------------------------------------
  // The glowing comet/ink trail (persisted-canvas technique) now lives in the
  // reusable useColorTrail hook — lifted VERBATIM from here, every numeric
  // preserved (EASE 0.2, IDLE 120, fade rgba(0,0,0,0.05), alphas .20/.50/.70,
  // burst seed 2.4 / growth 2.7, DPR cap 2). We pass the SAME NETS blue-brand
  // cool palette the hub always used (sky → light azure → soft cornflower →
  // soft indigo → periwinkle) so the trail looks + behaves IDENTICALLY. The
  // canvas is pointer-events:none + inside the z0 backdrop, so it can NEVER
  // intercept a node tap or the unlock choreography; the hook bails out under
  // reduced motion (no listeners, no rAF) and cleans up fully on unmount.
  useColorTrail(trailRef, layerRef, {
    palette: ["#6db8ef", "#79c7ec", "#5b9fe6", "#8aa6f5", "#aeb9ff"],
  });

  return (
    <div ref={layerRef} className={s.backdrop} aria-hidden="true">
      <div className={s.aurora} />
      <span className={`${s.blob} ${s.blob1}`} />
      <span className={`${s.blob} ${s.blob2}`} />
      <span className={`${s.blob} ${s.blob3}`} />
      <span className={`${s.blob} ${s.blob4}`} />
      <span className={`${s.blob} ${s.blob5}`} />
      {/* Pointer/touch color trail — layered above the aurora + blobs but still
          inside the backdrop (z-index 0 region), pointer-events:none. */}
      <canvas ref={trailRef} className={s.trail} aria-hidden="true" />
    </div>
  );
}

// CBP "progress" fraction → 0..100, used to fill the conic ring on the badge.
function pctFromCbp(g: CbpGate | undefined): number {
  if (!g) return 0;
  if (g.passed) return 100;
  const total = g.checkpoints_total || 3;
  return Math.max(0, Math.min(100, Math.round((g.checkpoints_correct / total) * 100)));
}

// ---- A single learning station = the pressable 3D "pebble" button ----------
function LearningNode({
  num,
  title,
  lead,
  variant,
  status,
  isNext,
  pct,
  meta,
  ctaLabel,
  align,
  onClick,
  testid,
}: {
  num: string;
  title: string;
  lead: string;
  variant: "case" | "flash";
  status: SectionStatus;
  isNext: boolean;
  pct: number;
  meta: string;
  ctaLabel: string;
  align: "left" | "right";
  onClick: () => void;
  testid: string;
}) {
  // `passed` recolors to the green "done" face regardless of base variant.
  const faceClass =
    status === "passed"
      ? s.nodeDone
      : variant === "case"
      ? s.nodeCase
      : s.nodeFlash;
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testid}
      data-status={status}
      className={[
        s.node,
        faceClass,
        align === "left" ? s.alignLeft : s.alignRight,
        isNext ? s.isNext : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span className={s.nodeTopline}>
        {/* Number badge with the conic progress ring (transform/opacity only). */}
        <span
          className={`${s.numRing} ${status === "passed" ? s.numRingDone : ""}`}
          style={{ ["--pct" as string]: status === "passed" ? 100 : pct }}
          aria-hidden="true"
        >
          <span className={s.numInner}>
            {status === "passed" ? <CheckGlyph /> : <span className={s.nodeNum}>{num}</span>}
          </span>
        </span>
        <span className={s.statusGlyph} aria-hidden="true">
          {status === "passed" ? (
            <span className={s.crownStamp}>
              <CrownGlyph />
            </span>
          ) : status === "inProgress" ? (
            <span className={s.dot} />
          ) : null}
        </span>
      </span>

      <span className={s.nodeTitle}>{title}</span>
      <span className={s.nodeLead}>{lead}</span>

      <span className={s.nodeFoot}>
        <span className={s.meta}>{meta}</span>
        <span className={s.ctaLabel}>{ctaLabel}</span>
      </span>
    </button>
  );
}

// ---- 03 · Homework Practices: the REVEALED node ----------------------------
// Only mounted once `unlocked` is true (locked state renders nothing at all).
// `revealing` is true ONLY during the first-time celebration window; it adds the
// glow ring + firework particles. `chainPhase` drives the decorative <HubChains>
// chain-wrap overlay AND (via the node's data-chain attribute) the gray→color
// transition: the node reads grayscale while "bound"/"rattle", then snaps to the
// full violet→green .practicesOpen fill at "snap". On a return visit (or under
// reduced motion) chainPhase is "gone" and revealing is false → static node, no
// chains, no celebration.
const FIREWORK_COUNT = 12; // particles flung radially; matches CSS --i count

function PracticesNode({
  revealing,
  chainPhase,
  onEnter,
}: {
  revealing: boolean;
  chainPhase: HubChainsPhase;
  onEnter: () => void;
}) {
  return (
    <article
      data-testid="hub-division-3"
      data-chain={chainPhase}
      className={[s.node, s.nodePractices, s.alignCenter, s.practicesOpen]
        .filter(Boolean)
        .join(" ")}
    >
      {/* Decorative chain-wrap overlay (absolute inset:0, pointer-events:none,
          aria-hidden, reduced-motion-safe internally). Renders nothing when
          chainPhase === "gone". Sits ABOVE the node content but never blocks
          taps. */}
      <HubChains phase={chainPhase} className={s.chains} />
      {/* Reveal-only celebration layer: a bright pulsing glow ring + a radial
          firework burst in the hub blue/indigo/gold family. Transform/opacity
          only; pointer-events:none so it never blocks the CTA. Mounted just for
          the celebration window, then unmounted with `revealing`. */}
      {revealing && (
        <span className={s.celebrate} aria-hidden="true">
          <span className={s.glowRing} />
          <span className={s.fireworks}>
            {Array.from({ length: FIREWORK_COUNT }, (_, i) => (
              <span
                key={i}
                className={s.spark}
                style={{ ["--i" as string]: i, ["--n" as string]: FIREWORK_COUNT }}
              />
            ))}
          </span>
        </span>
      )}

      <div className={s.practiceScope} data-testid="hub-practice-scope" aria-live="polite">
        <span className={s.nodeTopline}>
          <span className={`${s.numRing} ${s.numRingOpen}`} aria-hidden="true">
            <span className={s.numInner}>
              <span className={s.nodeNum}>03</span>
            </span>
          </span>
        </span>

        <span className={s.nodeTitle}>Homework Practices</span>

        {/* What's inside the Practice Arc. */}
        <ul className={s.subItems}>
          <li className={s.subItem}>
            <GameGlyph />
            <span>Gamified drills</span>
          </li>
          <li className={s.subItem}>
            <GamepadGlyph />
            <span>Interactive games</span>
          </li>
          <li className={`${s.subItem} ${s.subItemBoss}`}>
            <BossGlyph />
            <span>Boss fight</span>
          </li>
        </ul>

        <div className={s.nodeFoot}>
          <button
            type="button"
            className={`${s.enterCta} ${s.ctaBtn}`}
            onClick={onEnter}
            data-testid="hub-enter-practice"
          >
            Enter Practice Arc →
          </button>
        </div>
      </div>
    </article>
  );
}

// The winding path connector. A thick rounded stroke snakes node→node; each
// segment recolors green once its upstream node is passed. Resolution-independent
// 0..1000 viewBox stretched to the column (preserveAspectRatio="none").
//
// The node-2 → node-3 segment is HIDDEN while locked — the winding path simply
// ends at Flash cards. It appears only once unlocked, and during the reveal its
// "trial" dots pop in one-by-one toward the about-to-appear node before the
// solid stroke settles in.
const TRIAL_DOTS = 5; // dots that draw in along the node-2 → node-3 segment

// Cubic-Bezier sample points down the node-2 → node-3 curve (the same control
// points as the stroke `d` below), used to place the draw-in "trial" dots.
const SEG3_DOTS = [
  { x: 695, y: 580 },
  { x: 660, y: 650 },
  { x: 590, y: 700 },
  { x: 530, y: 760 },
  { x: 505, y: 825 },
];

function PathConnectors({
  cbpPassed,
  mcPassed,
  unlocked,
  revealing,
}: {
  cbpPassed: boolean;
  mcPassed: boolean;
  unlocked: boolean;
  revealing: boolean;
}) {
  return (
    <svg
      className={s.connectors}
      viewBox="0 0 1000 1000"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {/* node 1 (left) → node 2 (right) */}
      <path
        className={`${s.line} ${cbpPassed ? s.lineLive : ""}`}
        d="M300 150 C 320 320, 700 360, 700 500"
        fill="none"
        strokeWidth="11"
        strokeLinecap="round"
        strokeDasharray="2 26"
      />

      {/* node 2 (right) → node 3 (center) — HIDDEN while locked. Rendered once
          unlocked; during the reveal the stroke fades in AFTER the trial dots. */}
      {unlocked && (
        <path
          className={`${s.line} ${s.lineLive} ${revealing ? s.lineReveal : ""}`}
          d="M700 540 C 700 720, 500 700, 500 860"
          fill="none"
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray="2 26"
        />
      )}

      {/* Draw-in "trial" dots along the segment — only during the reveal. Each
          pops in staggered (CSS keyed off --d) toward the appearing node. */}
      {revealing &&
        SEG3_DOTS.slice(0, TRIAL_DOTS).map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r="12"
            className={s.trialDot}
            style={{ ["--d" as string]: i }}
          />
        ))}

      {/* faint "all done" glow once everything is cleared */}
      {cbpPassed && mcPassed && unlocked && <circle cx="500" cy="870" r="10" className={s.lineGoal} />}
    </svg>
  );
}

const CheckGlyph = () => (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="3"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

const CrownGlyph = () => (
  // Award medal: a star-burst medallion on two ribbon tails. Distinct
  // achievement mark (NOT a crown). Single-color fill so it inherits the
  // themed gold and stays crisp at 16px inside the .crownStamp disk and on
  // the white progress chip alike.
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
  >
    {/* two ribbon tails dropping from behind the medallion */}
    <path d="M9.2 13.4 6.6 21.8l3.2-1.7L11.1 22l1-2.6zm5.6 0L13 19.4l1 2.6 1.3-1.9 3.2 1.7z" />
    {/* 10-point star-burst medallion (alternating long/short rays) */}
    <path d="M12 1.5l1.7 2.3 2.7-1 .2 2.9 2.8.8-1.4 2.5 1.4 2.5-2.8.8-.2 2.9-2.7-1L12 16.8 10.3 14.5l-2.7 1-.2-2.9-2.8-.8 1.4-2.5L4.6 6.8l2.8-.8.2-2.9 2.7 1z" />
  </svg>
);

const GameGlyph = () => (
  // Four-point sparkle with a small twinkle — an original "drills / play"
  // mark, clearly distinct from a five-point star. Line-icon (strokeWidth 1.8).
  <svg
    className={s.subGlyph}
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {/* main four-point sparkle with concave sides */}
    <path d="M11 3c.4 3.3 1.7 4.6 5 5-3.3.4-4.6 1.7-5 5-.4-3.3-1.7-4.6-5-5 3.3-.4 4.6-1.7 5-5z" />
    {/* small accent twinkle */}
    <path d="M18 14c.2 1.7.9 2.4 2.6 2.6C18.9 16.8 18.2 17.5 18 19.2c-.2-1.7-.9-2.4-2.6-2.6 1.7-.2 2.4-.9 2.6-2.6z" />
  </svg>
);

const GamepadGlyph = () => (
  <svg
    className={s.subGlyph}
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <line x1="6" y1="11" x2="10" y2="11" />
    <line x1="8" y1="9" x2="8" y2="13" />
    <line x1="15" y1="12" x2="15.01" y2="12" />
    <line x1="18" y1="10" x2="18.01" y2="10" />
    <rect x="2" y="6" width="20" height="12" rx="5" />
  </svg>
);

const BossGlyph = () => (
  // Crested shield with a star — the "boss / peak guardian" mark. Distinct
  // from a crown; line-icon to match the other sub-glyphs (strokeWidth 1.8).
  <svg
    className={s.subGlyph}
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {/* shield body: shoulders → tapering to a point at the base */}
    <path d="M12 2.5 19 5v6.2c0 4.3-2.8 7.6-7 9.3-4.2-1.7-7-5-7-9.3V5z" />
    {/* star emblem centered on the shield */}
    <path d="M12 7.6l1.1 2.3 2.5.3-1.9 1.7.5 2.5L12 13.4 9.8 14.7l.5-2.5-1.9-1.7 2.5-.3z" />
  </svg>
);
