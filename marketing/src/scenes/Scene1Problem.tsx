import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {KineticText} from '../components/KineticText';
import {UZ} from '../copy/uz';
import {INK, WHITE, BRAND_RED, EASE_SPRING, FONT} from '../theme/tokens';

export const Scene1Problem: React.FC = () => {
  const frame = useCurrentFrame();

  // Clock hand rotation: slow sweep over full scene
  const clockRotation = interpolate(frame, [0, 360], [0, 180], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Clock opacity: visible early, fades with problem lines
  const clockOpacity = interpolate(frame, [0, 20, 240, 280], [0, 0.6, 0.6, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Document rect 1: subtle drift
  const doc1Y = interpolate(frame, [0, 360], [0, -8], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const doc1X = interpolate(frame, [0, 360], [0, 4], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Document rect 2: slightly different drift
  const doc2Y = interpolate(frame, [0, 360], [0, 12], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const doc2X = interpolate(frame, [0, 360], [0, -6], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Document rect 3
  const doc3Y = interpolate(frame, [0, 360], [0, -5], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Background doc opacity: fade out with problem lines
  const docOpacity = interpolate(frame, [0, 30, 240, 270], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Turn line: scale + fade in at frame 260
  const turnScale = interpolate(frame, [260, 305], [0.9, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  const turnOpacity = interpolate(frame, [260, 300], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Accent dot under turn line: appears ~frame 300
  const accentOpacity = interpolate(frame, [300, 325], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  const accentScale = interpolate(frame, [300, 330], [0.6, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      {/* Subtle dark tint so content reads on the animated backdrop */}
      <AbsoluteFill style={{background: INK, opacity: 0.55}} />

      {/* Floating document rectangles — evoke dead worksheets */}
      <div
        style={{
          position: 'absolute',
          left: 160,
          top: 200,
          width: 320,
          height: 420,
          borderRadius: 12,
          background: 'rgba(255,255,255,0.05)',
          border: '1px solid rgba(255,255,255,0.08)',
          opacity: docOpacity,
          transform: `translate(${doc1X}px, ${doc1Y}px) rotate(-4deg)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          right: 200,
          top: 280,
          width: 280,
          height: 360,
          borderRadius: 10,
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.07)',
          opacity: docOpacity,
          transform: `translate(${doc2X}px, ${doc2Y}px) rotate(3deg)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 480,
          top: 600,
          width: 240,
          height: 300,
          borderRadius: 8,
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.06)',
          opacity: docOpacity,
          transform: `translate(0px, ${doc3Y}px) rotate(-1.5deg)`,
        }}
      />

      {/* Clock motif — top right, conveys "feedback too late" */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          right: 140,
          width: 120,
          height: 120,
          opacity: clockOpacity,
        }}
      >
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r="52"
            fill="none"
            stroke="rgba(255,255,255,0.12)"
            strokeWidth="1.5"
          />
          {/* Hour markers — subtle */}
          {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((deg, i) => {
            const rad = (deg * Math.PI) / 180;
            const isMajor = i % 3 === 0;
            const innerR = isMajor ? 44 : 47;
            return (
              <line
                key={deg}
                x1={60 + Math.cos(rad - Math.PI / 2) * innerR}
                y1={60 + Math.sin(rad - Math.PI / 2) * innerR}
                x2={60 + Math.cos(rad - Math.PI / 2) * 51}
                y2={60 + Math.sin(rad - Math.PI / 2) * 51}
                stroke="rgba(255,255,255,0.1)"
                strokeWidth={isMajor ? 1.5 : 0.8}
              />
            );
          })}
          {/* Clock hand */}
          <line
            x1="60"
            y1="60"
            x2={60 + Math.cos(((clockRotation - 90) * Math.PI) / 180) * 34}
            y2={60 + Math.sin(((clockRotation - 90) * Math.PI) / 180) * 34}
            stroke="rgba(255,255,255,0.22)"
            strokeWidth="2"
            strokeLinecap="round"
          />
          {/* Center dot */}
          <circle cx="60" cy="60" r="3" fill="rgba(255,255,255,0.18)" />
        </svg>
      </div>

      {/* Problem lines — stacked vertically, muted gray */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
          alignItems: 'center',
          zIndex: 1,
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '100%',
        }}
      >
        <KineticText
          text={UZ.problem[0]}
          delay={6}
          fontSize={64}
          color="#9aa3ad"
          font={FONT.body}
          weight={400}
          align="center"
          outAt={250}
        />
        <KineticText
          text={UZ.problem[1]}
          delay={46}
          fontSize={64}
          color="#9aa3ad"
          font={FONT.body}
          weight={400}
          align="center"
          outAt={250}
        />
        <KineticText
          text={UZ.problem[2]}
          delay={88}
          fontSize={64}
          color="#9aa3ad"
          font={FONT.body}
          weight={400}
          align="center"
          outAt={250}
        />
      </div>

      {/* Turn line — the emotional pivot */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: `translate(-50%, -50%) scale(${turnScale})`,
          opacity: turnOpacity,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 20,
          zIndex: 2,
        }}
      >
        <KineticText
          text={UZ.problemTurn}
          delay={0}
          fontSize={80}
          color={WHITE}
          font={FONT.display}
          weight={700}
          align="center"
        />

        {/* BRAND_RED accent underline */}
        <div
          style={{
            width: 180,
            height: 5,
            borderRadius: 3,
            background: BRAND_RED,
            opacity: accentOpacity,
            transform: `scaleX(${accentScale})`,
            transformOrigin: 'center',
            filter: `blur(1px) drop-shadow(0 0 20px ${BRAND_RED})`,
            boxShadow: `0 0 32px ${BRAND_RED}`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
