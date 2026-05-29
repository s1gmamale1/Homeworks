import {AbsoluteFill, interpolate, spring, useCurrentFrame} from 'remotion';
import {DeviceFrame} from '../components/DeviceFrame';
import {ModeChip} from '../components/ModeChip';
import {KineticText} from '../components/KineticText';
import {UZ} from '../copy/uz';
import {INK, WHITE, PRODUCT_BLUE, GRAD, EASE_SPRING, FONT, springBouncy} from '../theme/tokens';

export const Scene5Tutor: React.FC = () => {
  const frame = useCurrentFrame();

  // --- Device frame spring (frames 0–25) ---
  const deviceScale = spring({frame, fps: 30, config: springBouncy});
  const deviceScaleVal = interpolate(deviceScale, [0, 1], [0.9, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const deviceTranslateY = interpolate(frame, [0, 25], [30, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const deviceOpacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // --- Chat bubble slide-in (frames 8–35) ---
  const bubbleOpacity = interpolate(frame, [8, 28], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const bubbleTranslateX = interpolate(frame, [8, 35], [-40, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // --- Typewriter: character reveal frames 25–120 ---
  const tutorLine = UZ.tutorLine;
  const charsShown = Math.floor(
    interpolate(frame, [25, 120], [0, tutorLine.length], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    })
  );
  const shown = tutorLine.slice(0, charsShown);
  const isTypingComplete = frame >= 120;

  // Deterministic blinking caret (no Date.now / Math.random)
  const caretOpacity = Math.floor(frame / 10) % 2 === 0 ? 1 : 0.25;

  // --- "3 rejim" label fade-in (frame 122) ---
  const labelOpacity = interpolate(frame, [122, 138], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  return (
    <AbsoluteFill style={{background: 'transparent'}}>
      {/* LEFT side — chat bubble + mode chips */}
      <div
        style={{
          position: 'absolute',
          left: 110,
          top: 0,
          bottom: 0,
          width: 820,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 0,
        }}
      >
        {/* Chat bubble */}
        <div
          style={{
            opacity: bubbleOpacity,
            transform: `translateX(${bubbleTranslateX}px)`,
            background: WHITE,
            borderRadius: 22,
            boxShadow: '0 10px 30px rgba(0,0,0,0.12)',
            padding: '24px 30px',
            maxWidth: 620,
            borderLeft: `4px solid ${PRODUCT_BLUE}`,
            marginBottom: 36,
          }}
        >
          <div
            style={{
              fontFamily: FONT.body,
              fontSize: 34,
              fontWeight: 500,
              color: INK,
              lineHeight: 1.45,
              letterSpacing: '-0.01em',
              minHeight: 50,
              display: 'flex',
              alignItems: 'center',
              flexWrap: 'wrap',
            }}
          >
            <span>{shown}</span>
            {!isTypingComplete && (
              <span
                style={{
                  display: 'inline-block',
                  width: 2,
                  height: 34,
                  background: PRODUCT_BLUE,
                  marginLeft: 3,
                  borderRadius: 1,
                  opacity: caretOpacity,
                  verticalAlign: 'middle',
                }}
              />
            )}
          </div>
        </div>

        {/* "3 rejim" label */}
        <div
          style={{
            opacity: labelOpacity,
            fontFamily: FONT.body,
            fontSize: 22,
            fontWeight: 500,
            color: `${INK}99`,
            letterSpacing: '0.03em',
            textTransform: 'uppercase',
            marginBottom: 16,
          }}
        >
          3 rejim
        </div>

        {/* Mode chips row */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'row',
            gap: 16,
            alignItems: 'center',
          }}
        >
          <ModeChip
            label={UZ.tutorModes[0]}
            delay={130}
            tint={GRAD.interaction[0]}
          />
          <ModeChip
            label={UZ.tutorModes[1]}
            delay={142}
            tint={GRAD.game[0]}
          />
          <ModeChip
            label={UZ.tutorModes[2]}
            delay={154}
            tint={GRAD.boss[0]}
          />
        </div>
      </div>

      {/* RIGHT side — DeviceFrame */}
      <div
        style={{
          position: 'absolute',
          right: 80,
          top: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          opacity: deviceOpacity,
          transform: `scale(${deviceScaleVal}) translateY(${deviceTranslateY}px)`,
          transformOrigin: 'center right',
        }}
      >
        <DeviceFrame src="f5-tutor-open.png" kind="browser" width={820} radius={14} />
      </div>
    </AbsoluteFill>
  );
};
