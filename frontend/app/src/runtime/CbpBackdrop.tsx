// CbpBackdrop — the living, full-bleed backdrop behind the Case-Based Preview,
// mirroring the Hub's HubBackdrop structure so the CBP gains the same Hub DNA:
//   • a breathing aurora wash + 5 blurred candy blobs (idle-float + parallax)
//   • a persisted-canvas pointer/touch color-trail (via useColorTrail)
//
// Both layers are pointer-events:none + z-index 0 (under content at z1), GPU-only
// (transform/opacity), and fully killed under prefers-reduced-motion (no input
// listeners attached → --bx/--by stay 0; the trail hook bails out). It can NEVER
// intercept a CBP control. The only difference from the Hub is the palette: a
// cohesive INTERACTION-BLUE family (the CBP category accent) instead of the Hub's
// airy sky-blue set.

import { useEffect, useRef } from "react";
import { useColorTrail } from "./hooks/useColorTrail";
import s from "./CaseBasedPreview.module.css";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export default function CbpBackdrop() {
  const layerRef = useRef<HTMLDivElement | null>(null);
  const trailRef = useRef<HTMLCanvasElement | null>(null);

  // ---- Parallax rAF: write smoothed --bx/--by on the backdrop layer ----------
  // Identical to HubBackdrop: desktop = pointer parallax, mobile = scroll. The
  // CSS reads --bx/--by via translate3d; each blob multiplies by its own depth.
  // Critically-damped ease (0.08), idles the loop once settled. No listeners
  // under reduced motion → static backdrop.
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
  // hook defaults), but colored by a CBP interaction-blue palette so the trace
  // reads as a cousin of the §3 interaction accent rather than the Hub's sky.
  useColorTrail(trailRef, layerRef, {
    palette: ["#5e9ed6", "#4677b8", "#6db8ef", "#7aa5e8", "#9fb6f0"],
  });

  return (
    <div ref={layerRef} className={s.backdrop} aria-hidden="true">
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
