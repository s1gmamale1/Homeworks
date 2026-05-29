import {interpolate, useCurrentFrame} from 'remotion';
import {EASE_SPRING, FONT, WHITE} from '../theme/tokens';

type Props = {
  text: string;
  /** local frame at which this line starts revealing */
  delay?: number;
  perWord?: number; // frames between words
  fontSize?: number;
  weight?: number;
  color?: string;
  font?: string;
  /** local frame at which the line begins to fade out (optional) */
  outAt?: number;
  align?: 'left' | 'center';
  highlight?: string[]; // words to color with `highlightColor`
  highlightColor?: string;
};

export const KineticText: React.FC<Props> = ({
  text,
  delay = 0,
  perWord = 4,
  fontSize = 64,
  weight = 700,
  color = WHITE,
  font = FONT.display,
  outAt,
  align = 'center',
  highlight = [],
  highlightColor,
}) => {
  const frame = useCurrentFrame();
  const words = text.split(' ');
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0 0.28em',
        justifyContent: align === 'center' ? 'center' : 'flex-start',
        fontFamily: font,
        fontSize,
        fontWeight: weight,
        color,
        lineHeight: 1.1,
        letterSpacing: '-0.01em',
        maxWidth: '80%',
      }}
    >
      {words.map((w, i) => {
        const start = delay + i * perWord;
        const o = interpolate(frame, [start, start + 12], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: EASE_SPRING,
        });
        const y = interpolate(frame, [start, start + 12], [22, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: EASE_SPRING,
        });
        const outO =
          outAt === undefined
            ? 1
            : interpolate(frame, [outAt, outAt + 14], [1, 0], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              });
        const isHi = highlight.includes(w.replace(/[.,]/g, ''));
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity: o * outO,
              transform: `translateY(${y}px)`,
              color: isHi && highlightColor ? highlightColor : color,
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};
