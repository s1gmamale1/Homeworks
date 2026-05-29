import {interpolate, useCurrentFrame} from 'remotion';
import {EASE_SPRING, FONT, WHITE} from '../theme/tokens';

type Props = {label: string; delay?: number; tint: string};

export const ModeChip: React.FC<Props> = ({label, delay = 0, tint}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [delay, delay + 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const y = interpolate(frame, [delay, delay + 12], [16, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  return (
    <div
      style={{
        opacity: o,
        transform: `translateY(${y}px)`,
        padding: '14px 28px',
        borderRadius: 999,
        background: tint,
        color: WHITE,
        fontFamily: FONT.body,
        fontWeight: 700,
        fontSize: 28,
        boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
      }}
    >
      {label}
    </div>
  );
};
