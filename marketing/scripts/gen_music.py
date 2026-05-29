"""
Generate an ORIGINAL, license-clean ambient underscore for the Class A Education
marketing video (~75s). Output: marketing/public/audio/track.wav (then encoded to
.mp3 by the caller). 100% original/synthesized -> freely committable, no attribution.

Structure mirrors the video arc:
  0-17s   intro: minor pad (Am-ish), sparse, reflective ("the problem")
  17-29s  lift: brighter major movement + soft kick enters ("the reveal")
  29-72s  body: uplifting Am-F-C-G loop, gentle arp + kick ("the demos")
  72-75s  resolve + fade
"""
import math
import struct
import wave
import numpy as np

SR = 44100
DUR = 75.0
N = int(SR * DUR)
t = np.arange(N) / SR

# ---- chord progression (Am - F - C - G), 4s per chord, 16s loop ----
CHORDS = {
    "Am": [220.00, 261.63, 329.63],   # A3 C4 E4
    "F":  [174.61, 220.00, 261.63],   # F3 A3 C4
    "C":  [261.63, 329.63, 392.00],   # C4 E4 G4
    "G":  [196.00, 246.94, 293.66],   # G3 B3 D4
}
ROOT = {"Am": 110.00, "F": 87.31, "C": 130.81, "G": 98.00}
SEQ = ["Am", "F", "C", "G"]
CHORD_LEN = 4.0  # seconds


def adsr(env_len, a, d, s_level, r):
    """raised-cosine-ish attack/release envelope over env_len seconds."""
    n = int(SR * env_len)
    e = np.full(n, s_level)
    na, nr = int(SR * a), int(SR * r)
    if na > 0:
        e[:na] = np.linspace(0, 1, na) ** 1.5
        e[na:na + int(SR * d)] = np.linspace(1, s_level, int(SR * d))
    if nr > 0:
        e[-nr:] = np.linspace(s_level, 0, nr)
    return e


pad = np.zeros(N)
sub = np.zeros(N)
arp = np.zeros(N)

# build pad + sub by chord, crossfaded
xf = int(SR * 0.35)  # crossfade samples
chord_idx = 0
pos = 0
while pos < N:
    name = SEQ[chord_idx % len(SEQ)]
    seg = int(SR * CHORD_LEN)
    end = min(pos + seg + xf, N)
    L = end - pos
    seg_t = np.arange(L) / SR
    # pad: stacked detuned sines + soft 2nd harmonic, slow swell envelope
    env = np.hanning(L * 2)[:L] if L < seg else np.concatenate(
        [np.linspace(0, 1, xf) ** 1.2, np.ones(L - 2 * xf), np.linspace(1, 0, xf) ** 1.2]
    ) if L > 2 * xf else np.ones(L)
    voice = np.zeros(L)
    for f in CHORDS[name]:
        voice += np.sin(2 * math.pi * f * seg_t)
        voice += 0.5 * np.sin(2 * math.pi * f * 1.001 * seg_t)   # detune for width
        voice += 0.25 * np.sin(2 * math.pi * f * 2 * seg_t)      # soft octave
    voice /= (len(CHORDS[name]) * 1.75)
    pad[pos:end] += voice * env
    # sub bass
    rf = ROOT[name]
    sub[pos:end] += np.sin(2 * math.pi * rf * seg_t) * env * 0.6
    pos += seg
    chord_idx += 1

# ---- gentle arpeggio (eighth notes) during body (t > 14s) ----
bpm = 120.0
beat = 60.0 / bpm
eighth = beat / 2
note_i = 0
ts = 0.0
while ts < DUR:
    if ts > 13.0:
        name = SEQ[int(ts // CHORD_LEN) % len(SEQ)]
        notes = CHORDS[name]
        f = notes[note_i % len(notes)] * 2  # one octave up, sparkly
        start = int(ts * SR)
        dlen = int(SR * eighth * 0.9)
        if start + dlen < N:
            lt = np.arange(dlen) / SR
            decay = np.exp(-lt * 9)
            arp[start:start + dlen] += np.sin(2 * math.pi * f * lt) * decay * 0.18
    note_i += 1
    ts += eighth

# ---- soft kick pulse on the beat, entering at t=17s ----
kick = np.zeros(N)
ts = 0.0
while ts < DUR:
    if ts >= 16.5:
        start = int(ts * SR)
        dlen = int(SR * 0.18)
        if start + dlen < N:
            lt = np.arange(dlen) / SR
            fsweep = 110 * np.exp(-lt * 30) + 45
            body = np.sin(2 * math.pi * fsweep * lt) * np.exp(-lt * 14)
            amp = 0.5 if ts < 53 else 0.62
            kick[start:start + dlen] += body * amp
    ts += beat

# ---- section gains ----
gain = np.ones(N)
gain *= np.interp(t, [0, 16, 18, 53, 60], [0.55, 0.62, 0.85, 0.85, 1.0])

mix = (pad * 0.55 + sub * 0.5 + arp + kick) * gain

# master fade in/out
fin = int(SR * 2.5)
fout = int(SR * 3.0)
mix[:fin] *= np.linspace(0, 1, fin) ** 1.3
mix[-fout:] *= np.linspace(1, 0, fout) ** 1.3

# soft limit + normalize with headroom
mix = np.tanh(mix * 0.9)
mix /= (np.max(np.abs(mix)) + 1e-6)
mix *= 0.89

# subtle stereo width (Haas + detune already in pad)
delay = int(SR * 0.012)
left = mix.copy()
right = np.zeros(N)
right[delay:] = mix[:-delay]
stereo = np.stack([left, right], axis=1)

pcm = (stereo * 32767).astype(np.int16)

import os
out = os.path.join(os.path.dirname(__file__), "..", "public", "audio", "track.wav")
out = os.path.abspath(out)
os.makedirs(os.path.dirname(out), exist_ok=True)
with wave.open(out, "w") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", out, round(os.path.getsize(out) / 1e6, 2), "MB")
