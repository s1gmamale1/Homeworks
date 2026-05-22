import { describe, it, expect, beforeEach } from "vitest";
import { play, isMuted, setMuted } from "./sfx";

// Guards the sfx engine contract: it must NEVER throw (jsdom has no real
// AudioContext, so every cue silently no-ops), the mute toggle must round-trip
// + persist to localStorage, and the wiring hook (window.__SFX_LOG) must record
// the played cue id when present (this is what the e2e walk asserts against).

describe("sfx engine", () => {
  beforeEach(() => {
    try {
      localStorage.clear();
    } catch {
      /* private mode */
    }
    setMuted(false); // reset module-level mute between tests
    delete (window as unknown as { __SFX_LOG?: unknown }).__SFX_LOG;
  });

  it("play() never throws in jsdom (no AudioContext → silent no-op)", () => {
    expect(() => play("tick")).not.toThrow();
    expect(() => play("correct")).not.toThrow();
    expect(() => play("wrong")).not.toThrow();
    expect(() => play("boss-win")).not.toThrow();
    expect(() => play("screen")).not.toThrow();
  });

  it("mute toggles + persists to localStorage", () => {
    setMuted(true);
    expect(isMuted()).toBe(true);
    expect(localStorage.getItem("nets_sfx_muted")).toBe("1");
    setMuted(false);
    expect(isMuted()).toBe(false);
    expect(localStorage.getItem("nets_sfx_muted")).toBe("0");
  });

  it("records the cue id to window.__SFX_LOG when unmuted (wiring hook)", () => {
    (window as unknown as { __SFX_LOG: string[] }).__SFX_LOG = [];
    // Use a cue not played by the earlier test (the per-cue debounce is
    // module-level state that persists across test cases).
    play("popup-open");
    expect(
      (window as unknown as { __SFX_LOG: string[] }).__SFX_LOG,
    ).toContain("popup-open");
  });

  it("does NOT record (no cue) while muted", () => {
    (window as unknown as { __SFX_LOG: string[] }).__SFX_LOG = [];
    setMuted(true);
    play("tick");
    expect(
      (window as unknown as { __SFX_LOG: string[] }).__SFX_LOG.length,
    ).toBe(0);
  });
});
