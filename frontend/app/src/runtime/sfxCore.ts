// sfxCore — the shared Web-Audio engine core, extracted VERBATIM from
// hubSound.ts so the Hub unlock cues and the new app-wide UI sounds (sfx.ts)
// share ONE AudioContext, ONE master gain, ONE `tone()` scheduler, and ONE
// global mute. Extracting it (rather than duplicating) means a single mute
// toggle silences EVERYTHING — clicks, answer feedback, AND the unlock fanfare.
//
// Contract (inherited from hubSound.ts, unchanged):
//   • Never throws to the caller — any failure silently no-ops.
//   • Lazily built on first use; one shared AudioContext + master GainNode.
//   • Oscillators are stopped after their envelope so nothing leaks.
//   • In jsdom/SSR (no AudioContext) every call no-ops — tests stay silent.
//
// NEW vs the old hubSound internals: a module-level `muted` flag (localStorage
// persisted, prefers-reduced-motion-aware default) that `tone()` honors, plus a
// master-gain ramp so even the inline (non-`tone`) oscillators go quiet on mute.

type AnyAudioContextCtor = typeof AudioContext;

const MUTE_KEY = "nets_sfx_muted";

// Master peak. Per-note gains are kept well below this so overlapping notes sum
// without clipping. (Same value the Hub fanfare was tuned against.)
export const MASTER_PEAK = 0.18;

let ctx: AudioContext | null = null;
let master: GainNode | null = null;

// --- Mute state (shared by hubSound + sfx) ----------------------------------

const muteListeners = new Set<(muted: boolean) => void>();

function readInitialMuted(): boolean {
  try {
    if (typeof localStorage !== "undefined") {
      const stored = localStorage.getItem(MUTE_KEY);
      if (stored === "1") return true;
      if (stored === "0") return false;
    }
    // No stored preference → ON by default, EXCEPT auto-mute when the OS asks
    // for reduced motion (a conservative proxy for "minimize sensory output";
    // the user can still unmute — this is an initial default, not a lock).
    if (
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return true;
    }
  } catch {
    /* private-mode / no matchMedia → fall through to default-on */
  }
  return false;
}

let muted = readInitialMuted();

export function isMuted(): boolean {
  return muted;
}

/**
 * Set the global mute. Persists to localStorage, ramps the live master gain
 * (so an in-flight inline oscillator also goes quiet), resumes the context on
 * unmute, and notifies subscribers (the toggle UI). Never throws.
 */
export function setMuted(next: boolean): void {
  muted = next;
  try {
    localStorage.setItem(MUTE_KEY, next ? "1" : "0");
  } catch {
    /* private mode — in-memory only */
  }
  try {
    if (master && ctx) {
      const now = ctx.currentTime;
      master.gain.cancelScheduledValues(now);
      master.gain.setValueAtTime(master.gain.value, now);
      master.gain.linearRampToValueAtTime(next ? 0.0001 : MASTER_PEAK, now + 0.04);
    }
  } catch {
    /* ignore */
  }
  if (!next) ensureContext(); // unmute on a gesture → make sure ctx is live
  muteListeners.forEach((fn) => {
    try {
      fn(next);
    } catch {
      /* a bad listener must not break the toggle */
    }
  });
}

/** Subscribe to mute changes (for the toggle UI). Returns an unsubscribe fn. */
export function subscribeMuted(fn: (muted: boolean) => void): () => void {
  muteListeners.add(fn);
  return () => muteListeners.delete(fn);
}

// --- AudioContext lifecycle -------------------------------------------------

/**
 * Resolve the AudioContext constructor with a typed webkit fallback, or null if
 * the environment has no Web Audio support (SSR, and jsdom under vitest — where
 * neither AudioContext nor webkitAudioContext exists → every sound no-ops).
 */
function getAudioContextCtor(): AnyAudioContextCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window &
    typeof globalThis & { webkitAudioContext?: AnyAudioContextCtor };
  return w.AudioContext ?? w.webkitAudioContext ?? null;
}

/**
 * Lazily build (and resume) the shared graph. Returns the AudioContext, or null
 * if Web Audio is unavailable or construction failed. Never throws.
 */
export function ensureContext(): AudioContext | null {
  try {
    if (!ctx) {
      const Ctor = getAudioContextCtor();
      if (!Ctor) return null;
      ctx = new Ctor();
      master = ctx.createGain();
      master.gain.value = muted ? 0.0001 : MASTER_PEAK;
      master.connect(ctx.destination);
    }
    // Autoplay policies start the context "suspended"; resume() is a no-op once
    // already running. Fire-and-forget; ignore the promise rejection.
    if (ctx.state === "suspended") {
      void ctx.resume().catch(() => {});
    }
    return ctx;
  } catch {
    return null;
  }
}

/** The live master node (for callers that schedule their own oscillators). */
export function masterNode(): GainNode | null {
  return master;
}

/**
 * Create/resume the shared AudioContext on a user gesture. Call this on the
 * first pointer/touch (see sfx.initGlobalPrime / the Hub) so later auto-fired
 * sounds aren't autoplay-blocked. Idempotent and safe to call repeatedly.
 */
export function primeAudio(): void {
  ensureContext();
}

// --- Note scheduler ---------------------------------------------------------

type ToneType = OscillatorType;

/**
 * Schedule a single enveloped tone on the shared graph. No-ops when muted or
 * when the context is unavailable. Quick attack, exponential decay to a tiny
 * floor, then a hard stop; nodes self-disconnect on ended.
 */
export function tone(
  freq: number,
  start: number,
  dur: number,
  peak: number,
  type: ToneType,
): void {
  if (muted) return;
  if (!ctx || !master) return;
  try {
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, start);

    const attack = 0.012;
    env.gain.setValueAtTime(0.0001, start);
    env.gain.exponentialRampToValueAtTime(peak, start + attack);
    env.gain.exponentialRampToValueAtTime(0.0001, start + dur);

    osc.connect(env);
    env.connect(master);

    osc.start(start);
    osc.stop(start + dur + 0.02);
    osc.onended = () => {
      try {
        osc.disconnect();
        env.disconnect();
      } catch {
        /* already torn down */
      }
    };
  } catch {
    /* a single bad note must never break the run */
  }
}
