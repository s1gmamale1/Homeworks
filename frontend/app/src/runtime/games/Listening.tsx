import { useMemo, useRef, useState, useCallback } from "react";
import { useRuntimeStore } from "../store";
import type { GameProps } from "../GameHost";
import { Eyebrow, Title, Lead, Button, FeatureCard } from "../../shared/ui/primitives";
import s from "./Listening.module.css";

// ---------------------------------------------------------------------------
// Listening — a Practice Arc game. Plays an audio clip, then (the "one rule")
// reveals the transcript only AFTER the student has played the audio, and asks
// comprehension checkpoints.
//
// Content lives at content_json.listening (ListeningPhase): { title, audio_url,
// transcript, checkpoints[] }. The runtime redactor strips the `ans` field from
// every checkpoint before this payload reaches the client (no answer leak), so
// the checkpoints here are answered + self-checked, not auto-graded — the
// optional `fb` note is shown as a model answer once the student has written
// theirs. (Server-side grading is a follow-up: it needs a `listening` branch in
// /api/ai/check-answer.)
//
// Empty content_json.listening → graceful skip card so the arc stays walkable.
// ---------------------------------------------------------------------------

interface ListeningCheckpoint {
  prompt?: string;
  fb?: string;
}

interface ListeningContent {
  title?: string;
  audio_url?: string;
  transcript?: string;
  checkpoints?: ListeningCheckpoint[];
}

// Allow http(s) audio sources and same-origin uploaded files (/media/…) — never
// javascript:/data: from authored URLs.
function safeAudioUrl(raw: string | undefined): string {
  const v = (raw ?? "").trim();
  if (/^https?:\/\//i.test(v)) return v;
  if (v.startsWith("/media/")) return v;
  return "";
}

// ── Waveform bar heights (28 bars, pseudo-random but fixed shape) ──────────
const BAR_HEIGHTS = [32, 55, 72, 48, 88, 40, 95, 60, 35, 78, 52, 82, 30, 68, 90, 58, 44, 86, 50, 72, 38, 62, 92, 54, 70, 44, 80, 58];

function fmt(secs: number): string {
  if (!isFinite(secs) || secs < 0) return "0:00";
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface AudioPlayerProps {
  src: string;
  onPlay: () => void;
  onError: () => void;
  onLoadedOk: () => void;
}

function AudioPlayer({ src, onPlay, onError, onLoadedOk }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const toggle = useCallback(() => {
    const a = audioRef.current;
    if (!a) return;
    if (playing) a.pause();
    else a.play();
  }, [playing]);

  const seek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const a = audioRef.current;
    if (!a) return;
    a.currentTime = Number(e.target.value);
    setCurrentTime(Number(e.target.value));
  }, []);

  const progress = duration > 0 ? currentTime / duration : 0;

  return (
    <div className={s.player}>
      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        onPlay={() => { setPlaying(true); onPlay(); }}
        onPause={() => setPlaying(false)}
        onEnded={() => { setPlaying(false); }}
        onError={onError}
        onLoadedMetadata={() => {
          setDuration(audioRef.current?.duration ?? 0);
          onLoadedOk();
        }}
        onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime ?? 0)}
        data-testid="listening-audio"
      />

      {/* Glow backdrop */}
      <div className={s.playerGlow} />

      {/* Play / Pause button */}
      <button
        className={`${s.playBtn} ${playing ? s.playBtnPaused : ""}`}
        onClick={toggle}
        aria-label={playing ? "Pause" : "Play"}
      >
        {playing ? (
          <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26" aria-hidden>
            <rect x="5" y="3" width="5" height="18" rx="2.5" />
            <rect x="14" y="3" width="5" height="18" rx="2.5" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26" aria-hidden>
            <path d="M7 4.5v15l12-7.5L7 4.5z" />
          </svg>
        )}
      </button>

      {/* Waveform + progress */}
      <div className={s.waveWrap}>
        <div className={s.waveform} aria-hidden>
          {BAR_HEIGHTS.map((h, i) => {
            const barProgress = i / BAR_HEIGHTS.length;
            const played = barProgress < progress;
            return (
              <span
                key={i}
                className={`${s.bar} ${playing ? s.barPlaying : ""} ${played ? s.barPlayed : ""}`}
                style={{
                  "--bar-h": `${h}%`,
                  "--bar-delay": `${((i * 137) % 800) / 1000}s`,
                  "--bar-dur": `${0.55 + (i % 7) * 0.07}s`,
                } as React.CSSProperties}
              />
            );
          })}
        </div>

        <div className={s.scrubRow}>
          <span className={s.time}>{fmt(currentTime)}</span>
          <input
            type="range"
            className={s.scrubber}
            min={0}
            max={duration || 100}
            step={0.05}
            value={currentTime}
            onChange={seek}
            aria-label="Seek audio"
          />
          <span className={s.time}>{fmt(duration)}</span>
        </div>
      </div>
    </div>
  );
}

export default function Listening({ onComplete }: GameProps) {
  const payload = useRuntimeStore((st) => st.payload);
  const listening =
    (payload?.content_json as { listening?: ListeningContent } | null)?.listening ?? null;

  const audioUrl = useMemo(() => safeAudioUrl(listening?.audio_url), [listening?.audio_url]);
  const transcript = (listening?.transcript ?? "").trim();
  const checkpoints = useMemo<ListeningCheckpoint[]>(
    () => (Array.isArray(listening?.checkpoints) ? listening!.checkpoints! : []),
    [listening]
  );

  // The audio must be played before the transcript unlocks (the "one rule").
  const [played, setPlayed] = useState(false);
  const [audioErr, setAudioErr] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [answers, setAnswers] = useState<string[]>(() => checkpoints.map(() => ""));
  const [revealed, setRevealed] = useState<boolean[]>(() => checkpoints.map(() => false));

  // Empty content → skip card.
  const hasContent = Boolean(audioUrl || transcript || checkpoints.length);
  if (!listening || !hasContent) {
    return (
      <FeatureCard>
        <Eyebrow>Listening</Eyebrow>
        <Title size="section">Nothing to listen to here.</Title>
        <Lead>This homework has no Listening activity — skip ahead.</Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete} data-testid="listening-skip">
            Skip →
          </Button>
        </div>
      </FeatureCard>
    );
  }

  const transcriptUnlocked = played || !audioUrl;
  const allAnswered = checkpoints.every((_, i) => (answers[i] ?? "").trim().length > 0);
  const canContinue = (!audioUrl || played) && allAnswered;

  const setAnswer = (i: number, v: string) =>
    setAnswers((prev) => prev.map((a, j) => (j === i ? v : a)));
  const reveal = (i: number) =>
    setRevealed((prev) => prev.map((r, j) => (j === i ? true : r)));

  return (
    <FeatureCard>
      <div className={s.wrap} data-testid="listening-game">
        <div>
          <Eyebrow>Listening</Eyebrow>
          <Title size="section">{listening.title || "Listen and answer"}</Title>
        </div>

        {audioUrl && (
          <>
            <AudioPlayer
              src={audioUrl}
              onPlay={() => setPlayed(true)}
              onError={() => setAudioErr(true)}
              onLoadedOk={() => setAudioErr(false)}
            />
            {audioErr && (
              <p className={s.hint} style={{ color: "#c0392b" }}>
                Couldn't load the audio. Try refreshing — if it persists, the
                audio source may be unavailable.
              </p>
            )}
          </>
        )}

        {transcript && (
          <div className={s.transcriptBlock}>
            <button
              type="button"
              className={s.transcriptToggle}
              disabled={!transcriptUnlocked}
              onClick={() => setShowTranscript((v) => !v)}
              data-testid="listening-transcript-toggle"
            >
              {showTranscript ? "Hide transcript" : "Show transcript"}
            </button>
            {!transcriptUnlocked && (
              <p className={s.hint}>Play the audio to unlock the transcript.</p>
            )}
            {showTranscript && transcriptUnlocked && (
              <div className={s.transcript} data-testid="listening-transcript">
                {transcript}
              </div>
            )}
          </div>
        )}

        {checkpoints.length > 0 && (
          <div className={s.cpList}>
            {checkpoints.map((cp, i) => (
              <div className={s.cp} key={i}>
                <span className={s.cpIndex}>Question {i + 1}</span>
                <span className={s.cpPrompt}>{cp.prompt || `Question ${i + 1}`}</span>
                <textarea
                  className={s.cpInput}
                  rows={2}
                  value={answers[i] ?? ""}
                  placeholder="Type your answer…"
                  onChange={(e) => setAnswer(i, e.target.value)}
                  data-testid={`listening-answer-${i}`}
                />
                {cp.fb &&
                  ((answers[i] ?? "").trim().length > 0 ? (
                    revealed[i] ? (
                      <div className={s.cpNote} data-testid={`listening-note-${i}`}>
                        {cp.fb}
                      </div>
                    ) : (
                      <button type="button" className={s.revealBtn} onClick={() => reveal(i)}>
                        Reveal model answer
                      </button>
                    )
                  ) : null)}
              </div>
            ))}
          </div>
        )}

        <div className={s.actions}>
          <Button
            variant="blue"
            onClick={onComplete}
            disabled={!canContinue}
            data-testid="listening-continue"
          >
            Continue →
          </Button>
        </div>
        {!canContinue && (
          <p className={s.lockNote}>
            {!played && audioUrl
              ? "Play the audio, then answer every question to continue."
              : "Answer every question to continue."}
          </p>
        )}
      </div>
    </FeatureCard>
  );
}
