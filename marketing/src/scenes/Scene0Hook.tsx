import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {KineticText} from '../components/KineticText';
import {UZ} from '../copy/uz';
import {BRAND_RED, INK} from '../theme/tokens';

export const Scene0Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const darken = interpolate(frame, [0, 20], [1, 0.82], {extrapolateRight: 'clamp'});
  // a faint red spark pulse near the bottom
  const spark = interpolate(frame, [60, 110], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <AbsoluteFill style={{background: INK, opacity: darken}} />
      <div style={{display: 'flex', flexDirection: 'column', gap: 24, zIndex: 1}}>
        <KineticText text={UZ.hook[0]} delay={6} fontSize={72} />
        <KineticText text={UZ.hook[1]} delay={26} fontSize={72} outAt={130} />
      </div>
      <div
        style={{
          position: 'absolute',
          bottom: 120,
          width: 220,
          height: 6,
          borderRadius: 3,
          background: BRAND_RED,
          opacity: spark,
          filter: 'blur(2px)',
          boxShadow: `0 0 40px ${BRAND_RED}`,
        }}
      />
    </AbsoluteFill>
  );
};
