// sfx — the app-wide UI sound engine. Built on the shared sfxCore graph (so the
// single mute toggle also silences these) and reuses the Hub's `tone()`
// scheduler + pentatonic family. Every cue is short, quiet, and synthesized
// (no asset files). For a LEARNING app the "wrong" cue is deliberately soft +
// non-punitive (a gentle descending pluck, never a harsh buzzer).
//
// Public API:
//   play(id)            — fire a named cue (mute-checked + debounced + safe).
//   initGlobalPrime()   — one-time pointer/touch listener to unblock autoplay.
//   isMuted/setMuted/subscribeMuted — re-exported from sfxCore for the toggle.
//
// Contract: never throws. Muted, debounced, jsdom (no AudioContext), or any
// error → silent no-op.

import { ensureContext, isMuted, masterNode, primeAudio, tone } from "./sfxCore";
import { playFireworkCrackle, playUnlockFanfare } from "./hubSound";

export { isMuted, setMuted, subscribeMuted } from "./sfxCore";

export type SfxId =
  | "tick" // any interactive tap/press (the curated "every click")
  | "submit" // an answer/action POSTs
  | "correct" // server confirms correct
  | "wrong" // server confirms wrong (soft, non-punitive)
  | "advance" // checkpoint → next checkpoint
  | "popup-open" // overlay/modal/nudge appears
  | "popup-close" // overlay/modal closes
  | "screen" // major screen transition
  | "complete" // a game / sub-task finished
  | "boss-win" // boss defeated (full fanfare)
  | "boss-lose" // boss failed (gentle deflate)
  | "error"; // network / submission failure

// Per-cue minimum spacing (ms). Rapid repeats inside the window are dropped so
// machine-gun tapping (or a double event) never blasts overlapping notes.
const DEBOUNCE_MS: Record<SfxId, number> = {
  tick: 55,
  submit: 120,
  correct: 140,
  wrong: 140,
  advance: 140,
  "popup-open": 90,
  "popup-close": 90,
  screen: 220,
  complete: 400,
  "boss-win": 800,
  "boss-lose": 800,
  error: 220,
};

const lastFired = new Map<SfxId, number>();

// A short frequency sweep (tone() is fixed-pitch). Routed through the shared
// master node so the global mute silences it; mirrors hubSound's whoosh.
function sweep(
  fromHz: number,
  toHz: number,
  dur: number,
  peak: number,
  type: OscillatorType,
): void {
  if (isMuted()) return;
  const ac = ensureContext();
  const m = masterNode();
  if (!ac || !m) return;
  try {
    const t0 = ac.currentTime;
    const osc = ac.createOscillator();
    const env = ac.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(fromHz, t0);
    osc.frequency.linearRampToValueAtTime(toHz, t0 + dur);
    env.gain.setValueAtTime(0.0001, t0);
    env.gain.exponentialRampToValueAtTime(peak, t0 + 0.012);
    env.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(env);
    env.connect(m);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
    osc.onended = () => {
      try {
        osc.disconnect();
        env.disconnect();
      } catch {
        /* already torn down */
      }
    };
  } catch {
    /* a bad sweep must never break the run */
  }
}

// Synthesize a single cue. Each cue stays under ~300ms (boss-win delegates to
// the existing ~1s fanfare). All peaks are well under MASTER_PEAK (0.18).
function synth(id: SfxId): void {
  const ac = ensureContext();
  if (!ac) return;
  const t = ac.currentTime;
  switch (id) {
    case "tick":
      // Ultra-light mechanical click — "registered" without demanding notice.
      tone(420, t, 0.055, 0.08, "triangle");
      break;
    case "submit":
      // Soft upward whoosh — "sent".
      sweep(300, 480, 0.09, 0.1, "sine");
      break;
    case "correct":
      // Warm major-third lift (C5 + E5) — "yes" without fanfare.
      tone(523.25, t, 0.22, 0.14, "triangle");
      tone(659.25, t + 0.005, 0.22, 0.1, "sine");
      break;
    case "wrong":
      // Quiet short descending pluck (A4 → G4) — "not quite", never punitive.
      tone(440, t, 0.15, 0.09, "triangle");
      tone(392, t + 0.06, 0.16, 0.08, "triangle");
      break;
    case "advance":
      // Gentle two-note climb (E5 → G5) — moving on.
      tone(659.25, t, 0.13, 0.12, "triangle");
      tone(783.99, t + 0.06, 0.16, 0.11, "triangle");
      break;
    case "popup-open":
      // Airy upward tick — arrival.
      sweep(880, 1046.5, 0.08, 0.09, "sine");
      break;
    case "popup-close":
      // Inverse — departure.
      sweep(1046.5, 880, 0.08, 0.08, "sine");
      break;
    case "screen":
      // Brief two-note chord (C5 + G5) — scene change.
      tone(523.25, t, 0.11, 0.11, "triangle");
      tone(783.99, t, 0.12, 0.09, "triangle");
      break;
    case "complete":
      // Miniature rising arpeggio (C5 → E5 → G5) — a milestone, not THE one.
      tone(523.25, t, 0.16, 0.15, "triangle");
      tone(659.25, t + 0.09, 0.16, 0.14, "triangle");
      tone(783.99, t + 0.18, 0.22, 0.14, "triangle");
      break;
    case "boss-win":
      // Maximum celebration — reuse the existing unlock fanfare + fireworks.
      playUnlockFanfare();
      playFireworkCrackle();
      break;
    case "boss-lose":
      // Gently deflating arpeggio (C5 → A4 → F4) — closure, not punishment.
      tone(523.25, t, 0.18, 0.1, "triangle");
      tone(440, t + 0.1, 0.18, 0.09, "triangle");
      tone(349.23, t + 0.2, 0.24, 0.08, "triangle");
      break;
    case "error":
      // Flat mechanical click — clearly not a game sound.
      tone(330, t, 0.09, 0.08, "sawtooth");
      break;
  }
}

/**
 * Fire a named UI cue. No-ops when muted, when fired again inside the cue's
 * debounce window, or when Web Audio is unavailable (jsdom/SSR). Never throws.
 *
 * Wiring-verification hook: when a test/e2e harness sets `window.__SFX_LOG = []`
 * the played id is pushed there — this lets a headless walk assert the RIGHT cue
 * fires at the right moment without any audio playback.
 */
export function play(id: SfxId): void {
  try {
    if (isMuted()) return;
    const now =
      typeof performance !== "undefined" ? performance.now() : Date.now();
    const min = DEBOUNCE_MS[id] ?? 80;
    if (now - (lastFired.get(id) ?? 0) < min) return;
    lastFired.set(id, now);

    // Deterministic wiring log for the e2e walk (opt-in; absent in prod).
    try {
      const log = (window as unknown as { __SFX_LOG?: SfxId[] }).__SFX_LOG;
      if (Array.isArray(log)) log.push(id);
    } catch {
      /* ignore */
    }

    synth(id);
  } catch {
    /* a cue must never break the UI */
  }
}

let primed = false;

/**
 * Register a one-time pointer/touch listener that resumes the AudioContext on
 * the visitor's first interaction (browsers start it suspended). Mount once at
 * the app root (V2FlowController). Idempotent; returns a cleanup fn.
 */
export function initGlobalPrime(): () => void {
  if (typeof window === "undefined" || primed) return () => {};
  primed = true;
  const prime = () => primeAudio();
  window.addEventListener("pointerdown", prime, { once: true, passive: true });
  window.addEventListener("keydown", prime, { once: true, passive: true });
  return () => {
    window.removeEventListener("pointerdown", prime);
    window.removeEventListener("keydown", prime);
  };
}
