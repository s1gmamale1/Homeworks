import {
  AbsoluteFill,
  interpolate,
  interpolateColors,
  useCurrentFrame,
} from 'remotion';
import {
  BRAND_RED,
  INK,
  PAGE_LIGHT_BOT,
  PAGE_LIGHT_TOP,
  PRODUCT_BLUE,
} from '../theme/tokens';

const BG_KEYS = [0, 150, 510, 870, 1200, 2010, 2160, 2250];
const BG_COLORS = [
  INK,
  INK,
  BRAND_RED,
  PAGE_LIGHT_TOP,
  PAGE_LIGHT_TOP,
  PAGE_LIGHT_BOT,
  BRAND_RED,
  BRAND_RED,
];

export const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const bg = interpolateColors(frame, BG_KEYS, BG_COLORS);
  const drift = interpolate(frame, [0, 2250], [0, 1]);
  const blob = (cx: number, cy: number, r: number, color: string, phase: number) => {
    const x = cx + Math.sin(drift * Math.PI * 2 + phase) * 60;
    const y = cy + Math.cos(drift * Math.PI * 2 + phase) * 40;
    return <circle cx={x} cy={y} r={r} fill={color} />;
  };
  return (
    <AbsoluteFill style={{backgroundColor: bg}}>
      <AbsoluteFill style={{filter: 'blur(80px)', opacity: 0.5}}>
        <svg width="1920" height="1080" viewBox="0 0 1920 1080">
          {blob(500, 300, 280, PRODUCT_BLUE, 0)}
          {blob(1450, 700, 320, '#5b6cff', 1.5)}
          {blob(1100, 200, 220, '#8a5fc8', 3)}
          {blob(700, 900, 260, '#0e8c7d', 4.5)}
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
