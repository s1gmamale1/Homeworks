import {AbsoluteFill, interpolate, spring, useCurrentFrame} from 'remotion';
import {Wordmark} from '../components/Wordmark';
import {DeviceFrame} from '../components/DeviceFrame';
import {KineticText} from '../components/KineticText';
import {UZ} from '../copy/uz';
import {BRAND_RED, WHITE, INK, EASE_SPRING, springBouncy} from '../theme/tokens';

export const Scene2Reveal: React.FC = () => {
  const frame = useCurrentFrame();

  // ── Phase 1: SMASH-IN (0–18) ─────────────────────────────────────────────
  // Red flood fades in hard from the previous dark scene
  const bgOpacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // ── Phase 3: HANDOFF background tint (300–359) ───────────────────────────
  // Fade red slightly toward INK to ease into the next light scene
  const bgDarken = interpolate(frame, [300, 359], [0, 0.28], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Background color blending: BRAND_RED darkens toward INK
  // We use an overlay approach — INK overlay on top of red
  const bgOverlayOpacity = bgDarken;

  // ── Phase 2: WORDMARK (18–230) ────────────────────────────────────────────
  // Logo "A" draws in via spring from frame 20
  const rawProgress = spring({
    frame: Math.max(frame - 20, 0),
    fps: 30,
    config: springBouncy,
  });
  const logoProgress = Math.min(Math.max(rawProgress, 0), 1);

  // Sparkle twinkle oscillation: pulses between frames 60–180
  const twinkle = interpolate(frame, [60, 120, 180], [0, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // ── Phase 3: HANDOFF (240–359) ────────────────────────────────────────────
  // Wordmark shrinks and moves up
  const wordmarkScale = interpolate(frame, [240, 310], [1, 0.45], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  const wordmarkTranslateY = interpolate(frame, [240, 310], [0, -300], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // KineticText caption fade out during handoff
  const captionOutAt = 240;

  // Device frame slides up from below
  const deviceTranslateY = interpolate(frame, [250, 330], [500, 120], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  const deviceOpacity = interpolate(frame, [250, 310], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  return (
    <AbsoluteFill
      style={{
        background: BRAND_RED,
        opacity: bgOpacity,
        overflow: 'hidden',
      }}
    >
      {/* Dark overlay for handoff tint */}
      <AbsoluteFill
        style={{
          background: INK,
          opacity: bgOverlayOpacity,
          pointerEvents: 'none',
        }}
      />

      {/* ── Wordmark group (center → shrinks to top) ── */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 32,
          transform: `scale(${wordmarkScale}) translateY(${wordmarkTranslateY}px)`,
          transformOrigin: 'center center',
        }}
      >
        <Wordmark
          color={WHITE}
          layout="col"
          logoSize={200}
          fontSize={80}
          progress={logoProgress}
          twinkle={twinkle}
        />

        {/* Caption — appears at delay:150, fades out at handoff */}
        <KineticText
          text={UZ.revealLine}
          delay={150}
          fontSize={42}
          color={WHITE}
          align="center"
          outAt={captionOutAt}
        />
      </AbsoluteFill>

      {/* ── Device frame slides up from below during handoff ── */}
      <AbsoluteFill
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'center',
          paddingBottom: 0,
          opacity: deviceOpacity,
          transform: `translateY(${deviceTranslateY}px)`,
          pointerEvents: 'none',
        }}
      >
        <DeviceFrame
          src="hub-r2-darkOS.png"
          kind="browser"
          width={1100}
          radius={18}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
