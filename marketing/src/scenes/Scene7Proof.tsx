import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { ProofCard } from '../components/ProofCard';
import { UZ } from '../copy/uz';
import { INK, PRODUCT_BLUE, ACCENT, EASE_SPRING, FONT } from '../theme/tokens';

export const Scene7Proof: React.FC = () => {
  const frame = useCurrentFrame();

  const eyebrowOpacity = interpolate(frame, [4, 18], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const eyebrowY = interpolate(frame, [4, 18], [14, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  const topRuleOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  const cardsOpacity = interpolate(frame, [8, 28], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  const delays = [8, 22, 36, 50];

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at 50% 40%, #ffffff, #eef4ff)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Thin top accent rule — brand red bookend */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 4,
          background: '#C8102E',
          opacity: topRuleOpacity,
        }}
      />

      {/* Eyebrow label */}
      <div
        style={{
          position: 'absolute',
          top: 96,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
          opacity: eyebrowOpacity,
          transform: `translateY(${eyebrowY}px)`,
        }}
      >
        <span
          style={{
            fontFamily: FONT.body,
            fontWeight: 800,
            fontSize: 22,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: ACCENT,
          }}
        >
          {UZ.proofEyebrow}
        </span>
        {/* Thin underline accent */}
        <div
          style={{
            width: 40,
            height: 3,
            borderRadius: 2,
            background: PRODUCT_BLUE,
          }}
        />
      </div>

      {/* Proof cards row */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 64,
          opacity: cardsOpacity,
        }}
      >
        {UZ.proof.map((p, i) => (
          <ProofCard
            key={i}
            value={p.value}
            label={p.label}
            suffix={p.suffix}
            color={INK}
            delay={delays[i]}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};
