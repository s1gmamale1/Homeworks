// Original, synthesized Web Audio cues for the Learning Hub unlock reveal.
//
// Fully self-contained: no asset files, no network, no app imports — just the
// Web Audio API (oscillators + gain envelopes). The tones are an ORIGINAL,
// cheerful "Duolingo-style" celebration in vibe only; none of Duolingo's actual
// audio is used or reproduced.
//
// Contract every function honors:
//   • Never throws to the caller. If Web Audio is missing, blocked, or anything
//     errors, the function silently no-ops — the visual reveal works regardless.
//   • One shared AudioContext + one master GainNode at modest volume.
//   • Oscillators are stopped after their envelope so nothing leaks.
//   • Plays once per unlock; no global mute toggle (by design).

// --- Shared graph (created lazily on first use) -----------------------------

type AnyAudioContextCtor = typeof AudioContext;

let ctx: AudioContext | null = null;
let master: GainNode | null = null;

// Master peak. Per-note gains are kept well below this so overlapping notes
// (the fanfare arpeggio + sparkle) sum without clipping.
const MASTER_PEAK = 0.18;

/**
 * Resolve the AudioContext constructor with a typed webkit fallback, or null
 * if the environment has no Web Audio support.
 */
function getAudioContextCtor(): AnyAudioContextCtor | null {
  if (typeof window === 'undefined') return null;
  const w = window as Window &
    typeof globalThis & { webkitAudioContext?: AnyAudioContextCtor };
  return w.AudioContext ?? w.webkitAudioContext ?? null;
}

/**
 * Lazily build (and resume) the shared graph. Returns the AudioContext, or null
 * if Web Audio is unavailable or construction failed. Never throws.
 */
function ensureContext(): AudioContext | null {
  try {
    if (!ctx) {
      const Ctor = getAudioContextCtor();
      if (!Ctor) return null;
      ctx = new Ctor();
      master = ctx.createGain();
      master.gain.value = MASTER_PEAK;
      master.connect(ctx.destination);
    }
    // Autoplay policies start the context "suspended"; resume() is a no-op once
    // already running. Fire-and-forget; ignore the promise rejection.
    if (ctx.state === 'suspended') {
      void ctx.resume().catch(() => {});
    }
    return ctx;
  } catch {
    return null;
  }
}

// --- Note scheduler ---------------------------------------------------------

type ToneType = OscillatorType;

/**
 * Schedule a single enveloped tone on the shared graph.
 *
 * @param freq   frequency in Hz
 * @param start  absolute AudioContext time to begin (seconds)
 * @param dur    duration of the decay tail (seconds)
 * @param peak   peak gain for this note (relative to the master node)
 * @param type   oscillator waveform
 */
function tone(
  freq: number,
  start: number,
  dur: number,
  peak: number,
  type: ToneType,
): void {
  if (!ctx || !master) return;
  try {
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, start);

    // Quick attack, exponential decay to (near) silence. exponentialRampToValue
    // cannot target 0, so we ramp to a tiny floor then hard-stop.
    const attack = 0.012;
    env.gain.setValueAtTime(0.0001, start);
    env.gain.exponentialRampToValueAtTime(peak, start + attack);
    env.gain.exponentialRampToValueAtTime(0.0001, start + dur);

    osc.connect(env);
    env.connect(master);

    osc.start(start);
    osc.stop(start + dur + 0.02);
    // Defensive cleanup; modern browsers GC stopped nodes, but disconnect early.
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

// --- Musical material -------------------------------------------------------

// C-major pentatonic across two octaves (C5, D5, E5, G5, A5, C6, D6, E6).
// Pleasant, "no wrong notes" scale — used for the rising dot-pop run.
const PENTATONIC: readonly number[] = [
  523.25, // C5
  587.33, // D5
  659.25, // E5
  783.99, // G5
  880.0, // A5
  1046.5, // C6
  1174.66, // D6
  1318.51, // E6
];

// --- Public API -------------------------------------------------------------

/**
 * Create/resume the shared AudioContext on a user gesture. Call this on the
 * first hub pointer/touch so the later auto-fired fanfare isn't autoplay-blocked.
 * Idempotent and safe to call repeatedly.
 */
export function primeAudio(): void {
  ensureContext();
}

/**
 * A soft ascending pluck/pop as each path "trial" dot appears during the
 * draw-in. Sequential calls climb the pentatonic scale (wrapping after the
 * 8-step run) so the dots read as a gentle rising melody. `index` is the
 * 0-based dot order.
 */
export function playDotPop(index: number): void {
  try {
    const ac = ensureContext();
    if (!ac) return;

    const step = ((index % PENTATONIC.length) + PENTATONIC.length) %
      PENTATONIC.length;
    const freq = PENTATONIC[step];

    // Triangle = soft, slightly hollow pluck. Short tail (~140ms), gentle gain.
    tone(freq, ac.currentTime, 0.14, 0.16, 'triangle');
  } catch {
    /* no-op on any failure */
  }
}

/**
 * The celebratory moment — a bright rising pentatonic arpeggio capped with a
 * fast high sparkle, fired when the Homework Practices node pops in and the
 * fireworks burst. ~1.0s total. Plays once.
 */
export function playUnlockFanfare(): void {
  try {
    const ac = ensureContext();
    if (!ac) return;

    const t0 = ac.currentTime;

    // 1) Rising arpeggio: C5 - E5 - G5 - C6 (a bright major triad + octave),
    //    staggered ~95ms apart, triangle for warmth. Slightly longer tails so
    //    the run rings together.
    const arp: readonly number[] = [523.25, 659.25, 783.99, 1046.5];
    const stepDur = 0.095;
    arp.forEach((freq, i) => {
      const start = t0 + i * stepDur;
      tone(freq, start, 0.34, 0.17, 'triangle');
    });

    // 2) Sparkle/shimmer: a few high, fast, decaying sine notes laid over the
    //    tail of the arpeggio. Sine keeps the highs sweet rather than harsh.
    const sparkleStart = t0 + arp.length * stepDur + 0.02;
    const sparkle: readonly number[] = [
      1318.51, // E6
      1567.98, // G6
      2093.0, // C7
      1567.98, // G6
    ];
    sparkle.forEach((freq, i) => {
      const start = sparkleStart + i * 0.07;
      tone(freq, start, 0.18, 0.1, 'sine');
    });
  } catch {
    /* no-op on any failure */
  }
}

/**
 * Metallic chain-rattle: 8 short, bright, slightly-detuned clicks that
 * simulate interlocking links shifting against each other. Square/sawtooth
 * oscillators in the 1.8-3.5 kHz range, very short tails, low gain, with
 * deterministic timing jitter so successive clicks don't pulse metronomically.
 * Total duration ~450-500ms.
 */
export function playChainRattle(): void {
  try {
    const ac = ensureContext();
    if (!ac) return;

    const t0 = ac.currentTime;

    const clickCount = 8;
    const baseSpacing = 0.055; // ~55ms average spacing
    const baseFreqs: readonly number[] = [
      2200, 3100, 1900, 2800, 2400, 3300, 2050, 2700,
    ];
    const types: readonly OscillatorType[] = [
      'square', 'sawtooth', 'square', 'sawtooth',
      'square', 'sawtooth', 'square', 'sawtooth',
    ];

    let cursor = 0;
    for (let i = 0; i < clickCount; i++) {
      // Deterministic jitter ±14ms so clicks feel organic without Math.random.
      const jitterSign = i % 2 === 0 ? 1 : -1;
      const jitter = jitterSign * (((i * 17 + 3) % 15) * 0.001);
      const start = t0 + cursor + jitter;
      cursor += baseSpacing;

      // Slight detuning per link (±40Hz around the base).
      const detune = ((i * 13 + 7) % 80) - 40;
      const freq = baseFreqs[i] + detune;

      // Very short tail (30-54ms), low peak so it clicks not drones.
      const dur = 0.030 + ((i * 7 + 2) % 25) * 0.001;
      const peak = 0.08 + ((i * 11 + 5) % 3) * 0.01; // 0.08-0.10

      tone(freq, start, dur, peak, types[i]);
    }
  } catch {
    /* no-op on any failure */
  }
}

/**
 * Metallic chain-SNAP: the sound of chains breaking. A sharp bright transient
 * at ~3.5kHz (the metal crack) immediately followed by a low thud/fall at
 * ~130Hz (mass dropping). Two notes total, ~250ms combined.
 */
export function playChainSnap(): void {
  try {
    const ac = ensureContext();
    if (!ac) return;

    const t0 = ac.currentTime;

    // 1) Bright crack: short sawtooth burst at ~3.5kHz, very fast decay.
    tone(3500, t0, 0.045, 0.10, 'sawtooth');

    // 2) Low thud: triangle at ~130Hz, slightly delayed, longer tail.
    //    Triangle keeps it thumpy rather than buzzy.
    tone(130, t0 + 0.018, 0.22, 0.09, 'triangle');
  } catch {
    /* no-op on any failure */
  }
}

/**
 * Celebratory firework underlay meant to play simultaneously with
 * playUnlockFanfare(). A quick rising whoosh (swept oscillator) followed by
 * 6 scattered high crackle-pops at staggered times. Peaks are kept modest
 * (0.07-0.085) so the layer sits beneath the fanfare arpeggio. ~800ms total.
 */
export function playFireworkCrackle(): void {
  try {
    const ac = ensureContext();
    if (!ac) return;

    const t0 = ac.currentTime;

    // 1) Rising whoosh: sawtooth swept from ~300Hz to ~2400Hz over 200ms.
    //    We manage the oscillator directly here (tone() only sets fixed freq),
    //    but follow the same envelope + cleanup pattern.
    try {
      if (ctx && master) {
        const whoosh = ctx.createOscillator();
        const whooshEnv = ctx.createGain();
        whoosh.type = 'sawtooth';
        whoosh.frequency.setValueAtTime(300, t0);
        whoosh.frequency.linearRampToValueAtTime(2400, t0 + 0.20);
        whooshEnv.gain.setValueAtTime(0.0001, t0);
        whooshEnv.gain.exponentialRampToValueAtTime(0.07, t0 + 0.012);
        whooshEnv.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.20);
        whoosh.connect(whooshEnv);
        whooshEnv.connect(master);
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

    // 2) Crackle pops: 6 high sine/triangle blips staggered across 220-780ms.
    //    Peaks are modest (0.07-0.085) so the layer stays under the fanfare.
    const crackleFreqs: readonly number[] = [
      3200, 2800, 3600, 2600, 3000, 3400,
    ];
    const crackleTimes: readonly number[] = [
      0.22, 0.34, 0.44, 0.56, 0.66, 0.76,
    ];
    const crackleTypes: readonly OscillatorType[] = [
      'sine', 'triangle', 'sine', 'triangle', 'sine', 'triangle',
    ];
    crackleFreqs.forEach((freq, i) => {
      const start = t0 + crackleTimes[i];
      const dur = 0.040 + i * 0.005; // 40-65ms
      const peak = 0.07 + (i % 2) * 0.015; // 0.07 / 0.085 alternating
      tone(freq, start, dur, peak, crackleTypes[i]);
    });
  } catch {
    /* no-op on any failure */
  }
}
