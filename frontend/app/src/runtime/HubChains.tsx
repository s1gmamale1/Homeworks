/**
 * HubChains — decorative chain-wrap + chain-break overlay for the Division-3
 * "Homework Practices" hub node.
 *
 * This is a PURELY DECORATIVE overlay. The box itself (the violet→green
 * unlocked node) is rendered by the parent; this component sits ON TOP as an
 * absolutely-positioned, `pointer-events:none`, `aria-hidden` layer that wraps
 * the box in real-looking interlocking metallic chains + a padlock, then breaks
 * them free.
 *
 * USAGE — mount inside `.nodePractices` (the parent positions it via `inset:0`):
 *
 *   import HubChains from "./HubChains";
 *   // ...inside the Practices node, after the node's own content:
 *   <HubChains phase={chainPhase} />
 *
 * The parent drives `phase` along its own unlock timeline, e.g.:
 *   "bound"  → fade the wrapped+locked chains in (settled tension)
 *   "rattle" → chains jitter in place (~250–400ms of building tension)
 *   "snap"   → links break, halves recoil, padlock pops + drops (~900ms)
 *   "gone"   → render nothing; the box is free
 *
 * Honors `prefers-reduced-motion: reduce` (renders transparent — no chains, no
 * animation) entirely in CSS, so no JS media-query branch is needed here.
 *
 * Performance: transform/opacity-only animations, `will-change` only on the
 * moving parts. No layout-affecting properties animate.
 */
import styles from "./HubChains.module.css";

export type HubChainsPhase = "bound" | "rattle" | "snap" | "gone";

export interface HubChainsProps {
  /** Phase of the wrap→break choreography, driven by the parent timeline. */
  phase: HubChainsPhase;
  /** Optional extra class merged onto the root overlay. */
  className?: string;
}

/**
 * A single metallic chain link drawn as a rounded-rect ring with a gradient
 * sheen. `vertical` flips the long axis so adjacent links read as interlocking.
 */
function ChainLink({
  vertical = false,
  className,
}: {
  vertical?: boolean;
  className?: string;
}) {
  return (
    <span
      className={[
        styles.link,
        vertical ? styles.linkV : styles.linkH,
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <svg viewBox="0 0 28 40" className={styles.linkSvg} aria-hidden="true">
        {/* outer metal ring: thick stroke = the link body */}
        <rect
          x="4"
          y="4"
          width="20"
          height="32"
          rx="10"
          className={styles.linkRing}
        />
        {/* top-left bevel highlight: a thin bright stroke catching the light */}
        <rect
          x="4"
          y="4"
          width="20"
          height="32"
          rx="10"
          className={styles.linkSheen}
        />
      </svg>
    </span>
  );
}

/** One diagonal run of interlocking links (a "half" of the wrapping chain). */
function ChainRun({ side }: { side: "left" | "right" }) {
  const linkClass = side === "left" ? styles.runLeft : styles.runRight;
  return (
    <div className={[styles.run, linkClass].join(" ")}>
      {[0, 1, 2, 3, 4].map((i) => (
        <ChainLink key={i} vertical={i % 2 === 1} />
      ))}
    </div>
  );
}

/** Metallic padlock: gradient body, hinged shackle (pops open on snap), keyhole. */
function Padlock() {
  return (
    <div className={styles.padlock} aria-hidden="true">
      <svg viewBox="0 0 64 80" className={styles.padlockSvg}>
        {/* shackle — the U-bar; rotates up + the body drops on snap */}
        <path
          d="M18 34 V24 a14 14 0 0 1 28 0 V34"
          className={styles.shackle}
        />
        {/* body */}
        <rect
          x="10"
          y="34"
          width="44"
          height="38"
          rx="9"
          className={styles.lockBody}
        />
        {/* body top sheen */}
        <rect
          x="10"
          y="34"
          width="44"
          height="38"
          rx="9"
          className={styles.lockSheen}
        />
        {/* keyhole */}
        <circle cx="32" cy="50" r="5" className={styles.keyhole} />
        <rect x="30" y="52" width="4" height="11" rx="2" className={styles.keyhole} />
      </svg>
    </div>
  );
}

export default function HubChains({ phase, className }: HubChainsProps) {
  if (phase === "gone") return null;

  return (
    <div
      className={[styles.overlay, className ?? ""].filter(Boolean).join(" ")}
      data-phase={phase}
      aria-hidden="true"
    >
      {/* glow burst behind the break point (only visible on snap) */}
      <span className={styles.burst} />

      {/* two diagonal chain runs crossing the box, X-wrapped over the center */}
      <ChainRun side="left" />
      <ChainRun side="right" />

      {/* central padlock binding the cross */}
      <Padlock />

      {/* spark shards flung from the break point */}
      <span className={[styles.spark, styles.spark1].join(" ")} />
      <span className={[styles.spark, styles.spark2].join(" ")} />
      <span className={[styles.spark, styles.spark3].join(" ")} />
      <span className={[styles.spark, styles.spark4].join(" ")} />
    </div>
  );
}
