// SoundToggle — the persistent mute control for the app-wide UI sounds. A small
// glass button in the fixed bottom-right utility column (above the docked
// TutorWidget launcher). Reflects + flips the shared mute state in sfxCore
// (localStorage-persisted), and primes the AudioContext on its own click so the
// very next cue is audible. aria-pressed reflects the muted state.

import { useEffect, useState } from "react";
import { isMuted, setMuted, subscribeMuted } from "./sfx";
import s from "./SoundToggle.module.css";

export default function SoundToggle() {
  const [muted, setMutedState] = useState<boolean>(() => isMuted());

  // Stay in sync if mute changes elsewhere (e.g. another tab via storage, or a
  // future settings surface). subscribeMuted returns an unsubscribe fn.
  useEffect(() => subscribeMuted(setMutedState), []);

  const toggle = () => setMuted(!muted);

  return (
    <button
      type="button"
      className={s.toggle}
      onClick={toggle}
      aria-pressed={muted}
      aria-label={muted ? "Unmute sounds" : "Mute sounds"}
      title={muted ? "Unmute sounds" : "Mute sounds"}
      data-testid="sound-toggle"
      data-muted={muted ? "1" : "0"}
    >
      {muted ? <SpeakerOff /> : <SpeakerOn />}
    </button>
  );
}

function SpeakerOn() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 9v6h4l5 4V5L8 9H4z"
        fill="currentColor"
      />
      <path
        d="M16.5 8.5a4 4 0 0 1 0 7M18.8 6.2a7 7 0 0 1 0 11.6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

function SpeakerOff() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
      <path
        d="M16 9l5 6M21 9l-5 6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
