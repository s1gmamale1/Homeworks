import {BRAND_RED, WHITE} from '../theme/tokens';

type Props = {
  size?: number;
  progress?: number; // 0..1 draw-in
  twinkle?: number; // 0..1 sparkle pulse phase
  bg?: string;
  corner?: number; // 0..1 fraction of size for rounded corner
};

export const ClassALogo: React.FC<Props> = ({
  size = 320,
  progress = 1,
  twinkle = 1,
  bg = BRAND_RED,
  corner = 0.14,
}) => {
  const aOpacity = Math.min(1, progress * 1.3);
  const aY = (1 - Math.min(1, progress * 1.3)) * 30;
  const sp = Math.max(0, (progress - 0.45) / 0.55); // sparkle comes in after the A
  const sparkleScale = sp * (1 + 0.12 * Math.sin(twinkle * Math.PI));
  return (
    <svg width={size} height={size} viewBox="0 0 200 200" fill="none">
      <rect x="0" y="0" width="200" height="200" rx={200 * corner} fill={bg} />
      {/* Bold A — outer silhouette with triangular counter + open bottom notch */}
      <g style={{opacity: aOpacity, transform: `translateY(${aY}px)`}}>
        <path
          fillRule="evenodd"
          fill={WHITE}
          d="M84 44 H116 L156 158 H120 L112 132 H88 L80 158 H44 Z
             M96 104 H104 L100 84 Z"
        />
        {/* bottom V-notch cut */}
        <path fill={bg} d="M92 158 L100 138 L108 158 Z" />
      </g>
      {/* 4-point concave sparkle, upper-right */}
      <g
        style={{
          transformOrigin: '156px 60px',
          transform: `scale(${sparkleScale})`,
          opacity: sp,
        }}
      >
        <path
          fill={WHITE}
          d="M156 30 C159 50 166 57 186 60 C166 63 159 70 156 90 C153 70 146 63 126 60 C146 57 153 50 156 30 Z"
        />
      </g>
    </svg>
  );
};
