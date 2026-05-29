import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {DeviceFrame} from '../components/DeviceFrame';
import {UZ} from '../copy/uz';
import {INK, PRODUCT_BLUE, EASE_SPRING, FONT} from '../theme/tokens';

// ---------------------------------------------------------------------------
// Scene 6 — "Outcomes + integrity" (local 0–209, ~7s @ 30fps, 1920x1080)
// Three crossfading sub-beats, each featuring a centered DeviceFrame + caption.
//   Beat A (frames  0– 80): f4-boss-arena.png
//   Beat B (frames 66–150): reflection-debrief-desktop-light.png
//   Beat C (frames136–209): integrity-3-nudge.png
// Root AbsoluteFill is transparent — global light Backdrop shows through.
// ---------------------------------------------------------------------------

const easeClamp = (
  frame: number,
  inputRange: number[],
  outputRange: number[],
) =>
  interpolate(frame, inputRange, outputRange, {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

// Beat opacity: fade-in over [inStart..inEnd], hold, fade-out over [outStart..outEnd].
// When outStart === outEnd (beat C has no explicit out), the 4-point array collapses to
// a hold — pass outStart = outEnd = 209 to hold through the end.
const beatOpacity = (
  frame: number,
  inStart: number,
  inEnd: number,
  outStart: number,
  outEnd: number,
): number => {
  // No fade-out window (beat holds through the end): collapse to a 2-point ramp.
  if (outEnd <= outStart) {
    return interpolate(frame, [inStart, inEnd], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
  }
  return interpolate(frame, [inStart, inEnd, outStart, outEnd], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
};

// Gentle push-in scale for a device frame over its in-window.
const beatScale = (frame: number, inStart: number, inEnd: number): number =>
  easeClamp(frame, [inStart, inEnd], [0.97, 1]);

interface BeatProps {
  frame: number;
  src: string;
  caption: string;
  inStart: number;
  inEnd: number;
  outStart: number;
  outEnd: number;
}

const Beat: React.FC<BeatProps> = ({
  frame,
  src,
  caption,
  inStart,
  inEnd,
  outStart,
  outEnd,
}) => {
  const opacity = beatOpacity(frame, inStart, inEnd, outStart, outEnd);
  const scale = beatScale(frame, inStart, inEnd);

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        paddingLeft: 120,
        paddingRight: 120,
        opacity,
        pointerEvents: 'none',
      }}
    >
      {/* Device frame with push-in scale */}
      <div
        style={{
          transform: `scale(${scale})`,
          transformOrigin: 'center center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <DeviceFrame src={src} kind="browser" width={900} radius={12} />

        {/* Caption fades with the beat */}
        <div
          style={{
            marginTop: 28,
            fontFamily: FONT.display,
            fontSize: 44,
            fontWeight: 700,
            color: INK,
            textAlign: 'center',
            letterSpacing: '-0.01em',
            maxWidth: 900,
          }}
        >
          {caption}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const Scene6Outcomes: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{background: 'transparent'}}>
      {/* Beat A: AI Boss arena */}
      <Beat
        frame={frame}
        src="f4-boss-arena.png"
        caption={UZ.outcomes[0]}
        inStart={0}
        inEnd={14}
        outStart={66}
        outEnd={80}
      />

      {/* Beat B: Reflection debrief */}
      <Beat
        frame={frame}
        src="reflection-debrief-desktop-light.png"
        caption={UZ.outcomes[1]}
        inStart={66}
        inEnd={82}
        outStart={136}
        outEnd={150}
      />

      {/* Beat C: Integrity nudge — holds through end */}
      <Beat
        frame={frame}
        src="integrity-3-nudge.png"
        caption={UZ.outcomes[2]}
        inStart={136}
        inEnd={152}
        outStart={209}
        outEnd={209}
      />
    </AbsoluteFill>
  );
};
