// LivingBackdrop — the reusable Hub-DNA living backdrop, generalized from
// CbpBackdrop / ReflectionBackdrop / the Hub's HubBackdrop so any runtime
// surface can mount the same DNA:
//   • a breathing aurora wash + 5 blurred candy blobs (idle-float + parallax)
//   • a persisted-canvas pointer/touch color-trail (via useColorTrail)
//
// Both layers are pointer-events:none + z-index 0 (under content at z1), GPU-only
// (transform/opacity), and fully killed under prefers-reduced-motion (no input
// listeners attached → --bx/--by stay 0; the trail hook bails out). It can NEVER
// intercept a control. The ONLY thing that changes per surface is `variant` —
// the hue family (CSS --lb-* vars in LivingBackdrop.module.css) + the matching
// trail palette below. All motion numerics mirror the Hub/CBP backdrop verbatim.
//
// Mount it as the FIRST child of a `position: relative` surface root, with the
// surface's own content layered above it (z-index ≥ 1). See CbpBackdrop for the
// canonical example.

import { useEffect, useRef } from "react";
import { useColorTrail } from "./hooks/useColorTrail";
import s from "./LivingBackdrop.module.css";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export type LivingBackdropVariant = "blue" | "purple" | "gold" | "teal";

// The comet hue ring per variant — kept in the SAME family as the variant's
// aurora/blob CSS vars so the trace reads as a cousin of the surface accent.
// `blue` reuses the Hub's exact sky palette; the others trace their division
// accent (purple = --grad-game, gold = --grad-content, teal = --grad-language).
const TRAIL_PALETTES: Record<LivingBackdropVariant, string[]> = {
  blue: ["#6db8ef", "#79c7ec", "#5b9fe6", "#8aa6f5", "#aeb9ff"],
  purple: ["#b388eb", "#a06fd6", "#c39bf0", "#9d7ae0", "#8a5fc8"],
  gold: ["#ffd166", "#f6b94d", "#ffcf85", "#f4a261", "#ffe0a3"],
  teal: ["#74aa9c", "#5fb0a0", "#8fc7ba", "#4a8576", "#9ed3c6"],
};

export default function LivingBackdrop({
  variant = "blue",
}: {
  /** Hue family for the aurora/blobs + the matching trail palette. */
  variant?: LivingBackdropVariant;
}) {
  const layerRef = useRef<HTMLDivElement | null>(null);
  const trailRef = useRef<HTMLCanvasElement | null>(null);

  // ---- Parallax rAF: write smoothed --bx/--by on the backdrop layer ----------
  // Verbatim from CbpBackdrop/HubBackdrop: desktop = pointer parallax, mobile =
  // scroll. The CSS reads --bx/--by via translate3d; each blob multiplies by its
  // own depth. Critically-damped ease (0.08), idles the loop once settled. No
  // listeners under reduced motion → static backdrop.
  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    if (prefersReducedMotion()) return; // static backdrop, no input reactivity

    let targetX = 0;
    let targetY = 0;
    let curX = 0;
    let curY = 0;
    let raf = 0;
    let running = false;

    const tick = () => {
      curX += (targetX - curX) * 0.08;
      curY += (targetY - curY) * 0.08;
      layer.style.setProperty("--bx", curX.toFixed(4));
      layer.style.setProperty("--by", curY.toFixed(4));
      if (Math.abs(targetX - curX) > 0.0005 || Math.abs(targetY - curY) > 0.0005) {
        raf = requestAnimationFrame(tick);
      } else {
        running = false;
      }
    };
    const kick = () => {
      if (running) return;
      running = true;
      raf = requestAnimationFrame(tick);
    };

    const onPointer = (e: PointerEvent) => {
      if (e.pointerType === "touch") return; // touch handled by scroll instead
      const w = window.innerWidth || 1;
      const h = window.innerHeight || 1;
      targetX = (e.clientX / w) * 2 - 1;
      targetY = (e.clientY / h) * 2 - 1;
      kick();
    };

    const onScroll = () => {
      const doc = document.documentElement;
      const max = Math.max(1, doc.scrollHeight - doc.clientHeight);
      const p = Math.min(1, Math.max(0, (window.scrollY || 0) / max));
      targetY = p * 2 - 1;
      kick();
    };

    window.addEventListener("pointermove", onPointer, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onPointer);
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  // ---- Pointer/touch COLOR TRAIL ---------------------------------------------
  // Same persisted-canvas comet as the Hub (all Hub numerics preserved by the
  // hook defaults); only the hue palette changes per variant.
  useColorTrail(trailRef, layerRef, { palette: TRAIL_PALETTES[variant] });

  return (
    <div ref={layerRef} className={`${s.backdrop} ${s[variant]}`} aria-hidden="true">
      <div className={s.aurora} />
      <span className={`${s.blob} ${s.blob1}`} />
      <span className={`${s.blob} ${s.blob2}`} />
      <span className={`${s.blob} ${s.blob3}`} />
      <span className={`${s.blob} ${s.blob4}`} />
      <span className={`${s.blob} ${s.blob5}`} />
      {/* Pointer/touch color trail — layered above the aurora + blobs but still
          inside the backdrop (z-index 0 region), pointer-events:none. */}
      <canvas ref={trailRef} className={s.trail} aria-hidden="true" />
    </div>
  );
}
