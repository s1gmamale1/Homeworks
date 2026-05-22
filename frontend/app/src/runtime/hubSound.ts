// Original, synthesized Web Audio cues for the Learning Hub unlock reveal.
//
// The shared engine — AudioContext lifecycle, master gain, the `tone()`
// scheduler, and the global mute — now lives in `sfxCore.ts`, so these Hub
// reveal cues and the app-wide UI sounds (`sfx.ts`) share ONE audio graph and
// ONE mute toggle. This file keeps only the Hub-specific musical material and
// the cue functions. Behavior is unchanged from the original self-contained
// version (every numeric preserved); the cues are an ORIGINAL, cheerful
// celebration in vibe only — none of Duolingo's actual audio is used.
//
// Contract every function still honors: never throws, silently no-ops if Web
// Audio is missing/blocked/muted, oscillators stopped after their envelope.

import { ensureContext, isMuted, masterNode, primeAudio, tone } from "./sfxCore";

// Re-exported so existing importers (`LearningHub.tsx`) keep `from "./hubSound"`.
export { primeAudio };

// C-major pentatonic across two octaves (C5, D5, E5, G5, A5, C6, D6, E6).
// Pleasant, "no wrong notes" scale. Exported so sfx.ts can reuse the same
// tonal family for its checkpoint-advance climb.
export const PENTATONIC: readonly number[] = [
  523.25, // C5
  587.33, // D5
  659.25, // E5
  783.99, // G5
  880.0, // A5
  1046.5, // C6
  1174.66, // D6
  1318.51, // E6
];

/**
 * A soft ascending pluck/pop as each path "trial" dot appears during the
 * draw-in. Sequential calls climb the pentatonic scale (wrapping after the
 * 8-step run). `index` is the 0-based dot order.
 */
export function playDotPop(index: number): void {
  try {
    const ac = ensureContext();
    if (!ac) return;
    const step =
      ((index % PENTATONIC.length) + PENTATONIC.length) % PENTATONIC.length;
    tone(PENTATONIC[step], ac.currentTime, 0.14, 0.16, "triangle");
  } catch {
    /* no-op on any failure */
  }
}

/**
 * The celebratory moment — a bright rising pentatonic arpeggio capped with a
 * fast high sparkle. ~1.0s total. Plays once.
 */
export function playUnlockFanfare(): void {
  try {
    const ac = ensureContext();
    if (!ac) return;
    const t0 = ac.currentTime;

    const arp: readonly number[] = [523.25, 659.25, 783.99, 1046.5];
    const stepDur = 0.095;
    arp.forEach((freq, i) => {
      tone(freq, t0 + i * stepDur, 0.34, 0.17, "triangle");
    });

    const sparkleStart = t0 + arp.length * stepDur + 0.02;
    const sparkle: readonly number[] = [1318.51, 1567.98, 2093.0, 1567.98];
    sparkle.forEach((freq, i) => {
      tone(freq, sparkleStart + i * 0.07, 0.18, 0.1, "sine");
    });
  } catch {
    /* no-op on any failure */
  }
}

/**
 * Metallic chain-rattle: 8 short, bright, slightly-detuned clicks. Total ~450ms.
 */
export function playChainRattle(): void {
  try {
    const ac = ensureContext();
    if (!ac) return;
    const t0 = ac.currentTime;

    const clickCount = 8;
    const baseSpacing = 0.055;
    const baseFreqs: readonly number[] = [
      2200, 3100, 1900, 2800, 2400, 3300, 2050, 2700,
    ];
    const types: readonly OscillatorType[] = [
      "square", "sawtooth", "square", "sawtooth",
      "square", "sawtooth", "square", "sawtooth",
    ];

    let cursor = 0;
    for (let i = 0; i < clickCount; i++) {
      const jitterSign = i % 2 === 0 ? 1 : -1;
      const jitter = jitterSign * (((i * 17 + 3) % 15) * 0.001);
      const start = t0 + cursor + jitter;
      cursor += baseSpacing;
      const detune = ((i * 13 + 7) % 80) - 40;
      const freq = baseFreqs[i] + detune;
      const dur = 0.03 + ((i * 7 + 2) % 25) * 0.001;
      const peak = 0.08 + ((i * 11 + 5) % 3) * 0.01;
      tone(freq, start, dur, peak, types[i]);
    }
  } catch {
    /* no-op on any failure */
  }
}

/**
 * Metallic chain-SNAP: a sharp ~3.5kHz crack + a low ~130Hz thud. ~250ms.
 */
export function playChainSnap(): void {
  try {
    const ac = ensureContext();
    if (!ac) return;
    const t0 = ac.currentTime;
    tone(3500, t0, 0.045, 0.1, "sawtooth");
    tone(130, t0 + 0.018, 0.22, 0.09, "triangle");
  } catch {
    /* no-op on any failure */
  }
}

/**
 * Celebratory firework underlay meant to play with playUnlockFanfare(). A quick
 * rising whoosh + 6 scattered crackle-pops. ~800ms total.
 */
export function playFireworkCrackle(): void {
  try {
    const ac = ensureContext();
    if (!ac) return;
    const t0 = ac.currentTime;

    // Swept whoosh — managed directly (tone() only sets a fixed freq). Routed
    // through the shared master node, so the global mute (master gain ramp)
    // silences it; we also short-circuit when already muted.
    try {
      const m = masterNode();
      if (!isMuted() && m) {
        const whoosh = ac.createOscillator();
        const whooshEnv = ac.createGain();
        whoosh.type = "sawtooth";
        whoosh.frequency.setValueAtTime(300, t0);
        whoosh.frequency.linearRampToValueAtTime(2400, t0 + 0.2);
        whooshEnv.gain.setValueAtTime(0.0001, t0);
        whooshEnv.gain.exponentialRampToValueAtTime(0.07, t0 + 0.012);
        whooshEnv.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.2);
        whoosh.connect(whooshEnv);
        whooshEnv.connect(m);
        whoosh.start(t0);
        whoosh.stop(t0 + 0.22);
        whoosh.onended = () => {
          try {
            whoosh.disconnect();
            whooshEnv.disconnect();
          } catch {
            /* already torn down */
          }
        };
      }
    } catch {
      /* whoosh failure must not abort the crackle pops */
    }

    const crackleFreqs: readonly number[] = [3200, 2800, 3600, 2600, 3000, 3400];
    const crackleTimes: readonly number[] = [0.22, 0.34, 0.44, 0.56, 0.66, 0.76];
    const crackleTypes: readonly OscillatorType[] = [
      "sine", "triangle", "sine", "triangle", "sine", "triangle",
    ];
    crackleFreqs.forEach((freq, i) => {
      const start = t0 + crackleTimes[i];
      const dur = 0.04 + i * 0.005;
      const peak = 0.07 + (i % 2) * 0.015;
      tone(freq, start, dur, peak, crackleTypes[i]);
    });
  } catch {
    /* no-op on any failure */
  }
}
