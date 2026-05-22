import { useEffect, useRef } from "react";
import { FeatureCard, Pill, Button, Lead } from "../shared/ui/primitives";
import type { IntegrityNudge as IntegrityNudgeData } from "../shared/types";
import s from "./IntegrityNudge.module.css";

// ---------------------------------------------------------------------------
// IntegrityNudge — soft-friction component for the process-supervision
// anti-cheat system.
//
// RESEARCH CONTRACT (docs/NETS_Academic_Integrity_AntiCheat_Research.md):
//   • A nudge is ADVISORY teacher intelligence surfaced as a small, dismissible
//     card. It NEVER blocks, gates, penalizes, re-grades, or unlocks.
//   • It mounts BESIDE the existing feedback / turn-result area — it never
//     replaces Continue / Next, so progress is never gated by it.
//   • Dismiss + Respond are no-ops on flow control. A respond posts an advisory
//     signal upstream (caller's `onRespond`); it never flips correctness, hp,
//     gate, or unlock state.
//   • `message` is rendered as TEXT only (never dangerouslySetInnerHTML).
//
// Renders nothing when `nudge` is null, so it is always safe to mount.
// ---------------------------------------------------------------------------

export interface IntegrityNudgeProps {
  nudge: IntegrityNudgeData | null;
  /** Advisory respond — posts the student's choice as a signal. Non-blocking. */
  onRespond?: (choice: string) => void;
  /** Dismiss the nudge. Non-blocking; flow continues regardless. */
  onDismiss?: () => void;
}

export default function IntegrityNudge({
  nudge,
  onRespond,
  onDismiss,
}: IntegrityNudgeProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  // Esc dismisses (focusable card). Keydown is scoped to the card so it never
  // swallows global shortcuts.
  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onDismiss?.();
    }
  };

  // Move focus to the card when a nudge appears so screen-reader + keyboard
  // users land on it (it's role="status" / aria-live polite, non-modal).
  useEffect(() => {
    if (nudge) cardRef.current?.focus();
  }, [nudge]);

  // Safe to always mount — render nothing when there's no flag.
  if (!nudge) return null;

  return (
    <FeatureCard className={s.nudge}>
      <div
        ref={cardRef}
        className={s.body}
        role="status"
        aria-live="polite"
        tabIndex={-1}
        onKeyDown={onKeyDown}
        data-testid="integrity-nudge"
      >
        {/* Security-category gradient top-accent bar. */}
        <span className={s.accent} aria-hidden="true" />
        <span className={s.glow} aria-hidden="true" />

        <Pill tone="warn" className={s.tag}>
          {nudge.type ? prettyType(nudge.type) : "Heads up"}
        </Pill>

        {/* TEXT ONLY — never dangerouslySetInnerHTML. The testid lives on a
            wrapper since the Lead primitive doesn't forward arbitrary props. */}
        <span data-testid="integrity-nudge-message">
          <Lead className={s.message}>{nudge.message}</Lead>
        </span>

        <div className={s.actions}>
          <Button
            variant="blue"
            onClick={() => onRespond?.("explain")}
            data-testid="integrity-nudge-respond"
          >
            Explain my reasoning
          </Button>
          <Button
            variant="outline"
            onClick={() => onDismiss?.()}
            data-testid="integrity-nudge-dismiss"
          >
            Dismiss
          </Button>
        </div>
      </div>
    </FeatureCard>
  );
}

// Turn a snake/kebab `type` token into a friendly chip label.
function prettyType(type: string): string {
  const cleaned = type.replace(/[_-]+/g, " ").trim();
  if (!cleaned) return "Heads up";
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}
