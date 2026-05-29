import {interpolate, useCurrentFrame} from 'remotion';
import {EASE_SPRING, FONT, WHITE} from '../theme/tokens';

type Props = {
  value: number;
  label: string;
  suffix?: string;
  delay?: number;
  color?: string;
};

export const ProofCard: React.FC<Props> = ({
  value,
  label,
  suffix = '',
  delay = 0,
  color = WHITE,
}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 24], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const shown = Math.round(value * t);
  const scale = interpolate(frame, [delay, delay + 18], [0.8, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  return (
    <div style={{transform: `scale(${scale})`, opacity: t, textAlign: 'center', minWidth: 220}}>
      <div style={{fontFamily: FONT.display, fontWeight: 700, fontSize: 96, color, lineHeight: 1}}>
        {shown}
        {suffix}
      </div>
      <div style={{fontFamily: FONT.body, fontSize: 26, color, opacity: 0.85, marginTop: 8}}>
        {label}
      </div>
    </div>
  );
};
