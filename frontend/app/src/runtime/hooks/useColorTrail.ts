// useColorTrail — the persisted-canvas pointer/touch color-trail extracted
// VERBATIM from LearningHub's HubBackdrop (the trail useEffect). Every numeric
// is preserved exactly so the Hub looks + behaves identically after the
// refactor (guarded by a before/after screenshot):
//   • EASE 0.2 (head-toward-target)            • IDLE_FRAMES 120 (~2s @60fps)
//   • fade rgba(0,0,0,0.05) destination-out     • halo alpha 0.20 / core 0.50
//   • burst ring alpha 0.70, seed r 2.4, growth 2.7, life decay 0.03
//   • hue advance segLen * 0.006               • lineWidth 14 + segLen*0.5 cap 20
//   • halo lineWidth = core + 12                • DPR cap 2
//
// The hue glides through a caller-supplied `palette` as the pointer travels;
// pointerdown jumps the hue + spawns an expanding burst ring. Under reduced
// motion the effect bails out entirely (no listeners, no rAF). Full cleanup on
// unmount: removeEventListener, cancelAnimationFrame, ResizeObserver.disconnect.

import { useEffect } from "react";
import type { RefObject } from "react";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export interface ColorTrailAlphas {
  /** Soft glow halo stroke alpha (wide, low). Hub default 0.20. */
  halo: number;
  /** Bright core stroke alpha. Hub default 0.50. */
  core: number;
  /** Click/tap burst ring peak alpha. Hub default 0.70. */
  burst: number;
}

export interface ColorTrailOptions {
  /** Hue ring the trail glides through as the pointer travels (hex strings). */
  palette: string[];
  /** Head-toward-target easing. Hub default 0.2 (smooth comet, no twitch). */
  ease?: number;
  /** Stroke alphas (halo / core / burst). Hub defaults 0.20 / 0.50 / 0.70. */
  alphas?: ColorTrailAlphas;
  /** Quiet frames before clearRect + idle. Hub default 120 (~2s @60fps). */
  idleFrames?: number;
  /** Per-frame destination-out erase color. Hub default "rgba(0, 0, 0, 0.05)". */
  fade?: string;
}

const DEFAULT_ALPHAS: ColorTrailAlphas = { halo: 0.2, core: 0.5, burst: 0.7 };

/**
 * Mount the persisted-canvas color-trail onto `canvasRef`, sized against
 * `layerRef` (the backdrop box). Pass the surface's hue palette + optional
 * numeric overrides (all default to the exact Hub values).
 */
export function useColorTrail(
  canvasRef: RefObject<HTMLCanvasElement | null>,
  layerRef: RefObject<HTMLElement | null>,
  options: ColorTrailOptions
): void {
  const {
    palette,
    ease = 0.2,
    alphas = DEFAULT_ALPHAS,
    idleFrames = 120,
    fade = "rgba(0, 0, 0, 0.05)",
  } = options;

  // Stringify the palette so the effect re-runs only when the colors actually
  // change, not on every render (a fresh array literal would otherwise churn).
  const paletteKey = palette.join("|");

  useEffect(() => {
    const canvas = canvasRef.current;
    const layer = layerRef.current;
    if (!canvas || !layer) return;
    if (prefersReducedMotion()) return; // no trail under reduced motion

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    // Caller-supplied hue ring — the hue glides through this family as the
    // pointer travels so the trail shifts color with travel distance.
    const PALETTE = palette;
    const hexToRgb = (hex: string): [number, number, number] => {
      const n = parseInt(hex.slice(1), 16);
      return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    };
    const RGB = PALETTE.map(hexToRgb);
    // Continuous palette sample: `pos` is a float position around the ring,
    // lerped between adjacent swatches so the color slides smoothly.
    const sampleColor = (pos: number): [number, number, number] => {
      const len = RGB.length;
      const t = ((pos % len) + len) % len;
      const i = Math.floor(t);
      const f = t - i;
      const a = RGB[i];
      const b = RGB[(i + 1) % len];
      return [
        Math.round(a[0] + (b[0] - a[0]) * f),
        Math.round(a[1] + (b[1] - a[1]) * f),
        Math.round(a[2] + (b[2] - a[2]) * f),
      ];
    };

    // DPR-aware sizing against the backdrop layer (== the shell box). The
    // backing store scales with devicePixelRatio; we draw in CSS pixels.
    let dpr = Math.min(window.devicePixelRatio || 1, 2); // cap at 2 for phones
    let cssW = 0;
    let cssH = 0;
    const resize = () => {
      const r = layer.getBoundingClientRect();
      cssW = Math.max(1, r.width);
      cssH = Math.max(1, r.height);
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(layer);

    // Live click/tap bursts — expanding rings that grow + fade then retire.
    type Burst = { x: number; y: number; r: number; hue: number; life: number };
    let bursts: Burst[] = [];

    let huePos = 0; // float position around the palette ring

    // Target = latest input position (set by handlers, never drawn directly).
    // Head = smoothed position eased toward the target each frame (what we draw
    // the comet at). prevHead = the head from the previous frame; each frame we
    // stroke the NEW segment prevHead → head only.
    let tx = 0;
    let ty = 0;
    let haveTarget = false; // a target has been set at least once
    let hx = 0;
    let hy = 0;
    let phx = 0;
    let phy = 0;
    let haveHead = false; // head has been seeded (skip the first phantom segment)
    const EASE = ease; // head-toward-target easing (smooth comet, no twitch)

    // Frames since the last input event — drives the eased fade-out + idle. The
    // loop keeps running after input stops until the streak has fully faded.
    let framesSinceInput = 0;
    const IDLE_FRAMES = idleFrames; // ~2s at 60fps: well past a full fade → safe to clear

    let raf2 = 0;
    let running2 = false;

    // Map a client (viewport) coord to canvas-local CSS pixels.
    const toLocal = (clientX: number, clientY: number) => {
      const r = layer.getBoundingClientRect();
      return { x: clientX - r.left, y: clientY - r.top };
    };

    // Handlers ONLY set the target + reset the idle counter — no drawing here.
    const setTarget = (clientX: number, clientY: number) => {
      const { x, y } = toLocal(clientX, clientY);
      tx = x;
      ty = y;
      if (!haveTarget) {
        // First input: seed the head AT the target so the comet starts there
        // rather than easing in from (0,0).
        hx = x;
        hy = y;
        phx = x;
        phy = y;
        haveHead = true;
      }
      haveTarget = true;
      framesSinceInput = 0;
      kick2();
    };

    const onMove = (e: PointerEvent) => {
      setTarget(e.clientX, e.clientY);
    };
    const onTouchMove = (e: TouchEvent) => {
      const t = e.touches[0];
      if (t) setTarget(t.clientX, t.clientY);
    };
    const onDown = (e: PointerEvent) => {
      const { x, y } = toLocal(e.clientX, e.clientY);
      huePos += 1; // jump the hue a full swatch on click/tap
      bursts.push({ x, y, r: 2.4, hue: huePos, life: 1 });
      // Snap both the target AND the head to the tap so the burst + trail share
      // an origin (no easing streak from wherever the head last sat).
      tx = x;
      ty = y;
      hx = x;
      hy = y;
      phx = x;
      phy = y;
      haveTarget = true;
      haveHead = true;
      framesSinceInput = 0;
      kick2();
    };

    const draw = () => {
      framesSinceInput++;

      // Eased, slow fade-out: erase a thin slice of the canvas's existing alpha
      // each frame (destination-out → fades to TRANSPARENT, not toward white).
      // A small alpha (~0.05) decays exponentially → reads as ease-out (fast
      // then slow) over ~1s, which is the requested "slow fade when stopped".
      ctx.globalCompositeOperation = "destination-out";
      ctx.fillStyle = fade;
      ctx.fillRect(0, 0, cssW, cssH);

      // Glowing comet body adds light (lighter blend) for a luminous streak.
      ctx.globalCompositeOperation = "lighter";

      // Ease the smoothed head toward the latest target.
      if (haveHead) {
        hx += (tx - hx) * EASE;
        hy += (ty - hy) * EASE;

        // New segment travelled this frame.
        const dx = hx - phx;
        const dy = hy - phy;
        const segLen = Math.hypot(dx, dy);

        // Advance the hue proportional to travel → colors glide along the trail.
        huePos += segLen * 0.006;

        // Draw ONLY the new segment as a single round-cap stroked line. The
        // canvas persists frame-to-frame, so the comet body is the accumulation
        // of past segments (NO redraw of past points → no overlap flicker).
        if (segLen > 0.01) {
          const [r, g, b] = sampleColor(huePos);
          // Width eases a touch with speed for a comet-like taper, clamped so a
          // fast flick doesn't blow out.
          const lineWidth = Math.min(20, 14 + segLen * 0.5);

          // A soft glow halo first (wider, low alpha), then the bright core.
          ctx.lineCap = "round";
          ctx.lineJoin = "round";

          ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alphas.halo})`;
          ctx.lineWidth = lineWidth + 12;
          ctx.beginPath();
          ctx.moveTo(phx, phy);
          ctx.lineTo(hx, hy);
          ctx.stroke();

          ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alphas.core})`;
          ctx.lineWidth = lineWidth;
          ctx.beginPath();
          ctx.moveTo(phx, phy);
          ctx.lineTo(hx, hy);
          ctx.stroke();
        }

        phx = hx;
        phy = hy;
      }

      // Expanding click/tap rings, fading as they grow.
      for (let i = 0; i < bursts.length; i++) {
        const bu = bursts[i];
        bu.r += 2.7;
        bu.life -= 0.03;
        const [r, g, b] = sampleColor(bu.hue);
        const ringAlpha = Math.max(0, bu.life) * alphas.burst;
        const grad = ctx.createRadialGradient(
          bu.x,
          bu.y,
          Math.max(0, bu.r - 8.4),
          bu.x,
          bu.y,
          bu.r,
        );
        grad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0)`);
        grad.addColorStop(0.7, `rgba(${r}, ${g}, ${b}, ${ringAlpha})`);
        grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(bu.x, bu.y, bu.r, 0, Math.PI * 2);
        ctx.fill();
      }
      bursts = bursts.filter((bu) => bu.life > 0 && bu.r < Math.max(cssW, cssH));

      // Keep ticking while input is recent OR a burst is still alive (the alpha
      // decay handles the visible fade — no hard point removal, no snap). Once
      // it's been quiet long enough for the streak to have fully faded, do one
      // clearRect and idle the loop (re-kicked by the next input).
      if (framesSinceInput < IDLE_FRAMES || bursts.length > 0) {
        raf2 = requestAnimationFrame(draw);
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.clearRect(0, 0, cssW, cssH);
        running2 = false;
      }
    };
    function kick2() {
      if (running2) return;
      running2 = true;
      raf2 = requestAnimationFrame(draw);
    }

    // Passive listeners on window — the canvas itself is pointer-events:none, so
    // taps still reach the nodes; these only OBSERVE motion, never block it.
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", onDown, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });

    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("touchmove", onTouchMove);
      ro.disconnect();
      cancelAnimationFrame(raf2);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasRef, layerRef, paletteKey, ease, idleFrames, fade, alphas.halo, alphas.core, alphas.burst]);
}
