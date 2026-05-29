import { AbsoluteFill, interpolate, spring, useCurrentFrame } from 'remotion';
import { Wordmark } from '../components/Wordmark';
import { KineticText } from '../components/KineticText';
import { UZ } from '../copy/uz';
import { BRAND_RED, BRAND_RED_DEEP, WHITE, EASE_SPRING, FONT, springBouncy } from '../theme/tokens';

export const Scene8CTA: React.FC = () => {
  const frame = useCurrentFrame();

  // Background fade in 0→1 over frames 0–12
  const bgOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Background deepens toward BRAND_RED_DEEP over frames 78–90
  const bgDeepen = interpolate(frame, [78, 90], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Wordmark scale: 0.94→1 via spring over frames 0–25
  const wordmarkScale = interpolate(
    spring({ frame, fps: 30, config: springBouncy }),
    [0, 1],
    [0.94, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  // Wordmark opacity: 0→1 over frames 0–14
  const wordmarkOpacity = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Twinkle for Wordmark sparkle pulse
  const tw = interpolate(frame, [10, 45], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Pill spring (starts at frame ~40)
  const pillSpringRaw = spring({ frame: frame - 40, fps: 30, config: springBouncy });
  const pillScale = interpolate(pillSpringRaw, [0, 1], [0.85, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const pillOpacity = interpolate(frame, [40, 54], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Interpolate background color from BRAND_RED to BRAND_RED_DEEP
  // We use a layered approach: red base + dark overlay
  const darkOverlayOpacity = bgDeepen * 0.35;

  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        backgroundColor: BRAND_RED,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Dark overlay for gentle close */}
      <AbsoluteFill
        style={{
          backgroundColor: BRAND_RED_DEEP,
          opacity: darkOverlayOpacity,
          pointerEvents: 'none',
        }}
      />

      {/* Centered stack */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 36,
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Wordmark */}
        <div
          style={{
            transform: `scale(${wordmarkScale})`,
            opacity: wordmarkOpacity,
          }}
        >
          <Wordmark
            layout="col"
            color={WHITE}
            logoSize={160}
            fontSize={64}
            progress={1}
            twinkle={tw}
          />
        </div>

        {/* CTA Title */}
        <KineticText
          text={UZ.ctaTitle}
          color={WHITE}
          fontSize={44}
          align="center"
          delay={18}
          weight={700}
        />

        {/* CTA Pill */}
        <div
          style={{
            transform: `scale(${pillScale})`,
            opacity: pillOpacity,
          }}
        >
          <div
            style={{
              backgroundColor: WHITE,
              borderRadius: 999,
              paddingTop: 16,
              paddingBottom: 16,
              paddingLeft: 40,
              paddingRight: 40,
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              gap: 12,
              boxShadow: '0 8px 32px rgba(0,0,0,0.22), 0 2px 8px rgba(0,0,0,0.12)',
            }}
          >
            <span
              style={{
                fontFamily: FONT.body,
                fontWeight: 700,
                fontSize: 30,
                color: BRAND_RED,
                letterSpacing: '-0.01em',
              }}
            >
              {UZ.ctaSub}
            </span>
            <span
              style={{
                fontFamily: FONT.body,
                fontWeight: 700,
                fontSize: 30,
                color: BRAND_RED,
                opacity: 0.45,
              }}
            >
              ·
            </span>
            <span
              style={{
                fontFamily: FONT.body,
                fontWeight: 700,
                fontSize: 30,
                color: BRAND_RED,
                letterSpacing: '-0.01em',
              }}
            >
              {UZ.ctaUrl}
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
