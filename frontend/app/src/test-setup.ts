// Vitest setup — runs before every test file (see vite.config.ts `setupFiles`).
//
// Pulls in jest-dom matchers and stubs the few browser globals the v2 runtime
// touches at module/store level so jsdom doesn't throw: matchMedia (reduced-
// motion checks live in CSS, but components/libs may probe it), crypto.randomUUID
// (session + tutor turn ids), sessionStorage (session id persistence), and a
// default fetch mock (overridden per-test). Each test resets the fetch mock.

import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi } from "vitest";

// --- matchMedia (jsdom doesn't implement it) ---
if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false, // default: prefers-reduced-motion: no-preference
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

// --- crypto.randomUUID (used for session + tutor turn ids) ---
if (typeof globalThis.crypto === "undefined") {
  // @ts-expect-error — minimal shim for the test environment
  globalThis.crypto = {};
}
if (typeof globalThis.crypto.randomUUID !== "function") {
  let counter = 0;
  Object.defineProperty(globalThis.crypto, "randomUUID", {
    configurable: true,
    writable: true,
    value: () =>
      `00000000-0000-4000-8000-${(counter++).toString().padStart(12, "0")}` as `${string}-${string}-${string}-${string}-${string}`,
  });
}

// --- sessionStorage (jsdom usually provides it, but guard anyway) ---
if (typeof window.sessionStorage === "undefined") {
  const store = new Map<string, string>();
  Object.defineProperty(window, "sessionStorage", {
    configurable: true,
    value: {
      getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
      setItem: (k: string, v: string) => void store.set(k, String(v)),
      removeItem: (k: string) => void store.delete(k),
      clear: () => store.clear(),
      key: (i: number) => Array.from(store.keys())[i] ?? null,
      get length() {
        return store.size;
      },
    },
  });
}

// --- fetch — default mock; tests override via mockFetch() helpers ---
beforeEach(() => {
  if (!globalThis.fetch || !("mock" in (globalThis.fetch as object))) {
    globalThis.fetch = vi.fn();
  }
});

afterEach(() => {
  vi.restoreAllMocks();
  try {
    window.sessionStorage.clear();
  } catch {
    /* ignore */
  }
});
