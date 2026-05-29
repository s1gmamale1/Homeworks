import {AbsoluteFill, interpolate, spring, useCurrentFrame} from 'remotion';
import {KineticText} from '../components/KineticText';
import {DeviceFrame} from '../components/DeviceFrame';
import {UZ} from '../copy/uz';
import {INK, WHITE, PRODUCT_BLUE, EASE_SPRING, FONT, springBouncy} from '../theme/tokens';
import {Sequence} from 'remotion';

export const Scene3Teacher: React.FC = () => {
  const frame = useCurrentFrame();

  // Laptop slide in from left
  const laptopX = interpolate(frame, [0, 30], [-90, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const laptopOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Link pill scale-in via spring at ~frame 150
  const pillScale = spring({
    frame: frame - 150,
    fps: 30,
    config: springBouncy,
  });
  const pillOpacity = interpolate(frame, [150, 165], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Copied tag pop at ~frame 185
  const copiedScale = spring({
    frame: frame - 185,
    fps: 30,
    config: springBouncy,
  });
  const copiedOpacity = interpolate(frame, [185, 200], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Phone 1 fly from pill toward lower-right (~frames 200-240)
  const phone1Progress = interpolate(frame, [200, 240], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const phone1X = interpolate(phone1Progress, [0, 1], [0, 200]);
  const phone1Y = interpolate(phone1Progress, [0, 1], [0, 130]);
  const phone1Opacity = interpolate(frame, [200, 215], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Phone 2 fly staggered (~frames 220-260)
  const phone2Progress = interpolate(frame, [220, 260], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const phone2X = interpolate(phone2Progress, [0, 1], [0, 260]);
  const phone2Y = interpolate(phone2Progress, [0, 1], [0, 155]);
  const phone2Opacity = interpolate(frame, [220, 235], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  // Tag line fade in at ~frame 230
  const tagOpacity = interpolate(frame, [230, 255], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });
  const tagY = interpolate(frame, [230, 255], [18, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

  return (
    <AbsoluteFill
      style={{
        background: 'transparent',
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        paddingLeft: 120,
        paddingRight: 120,
        paddingTop: 80,
        paddingBottom: 80,
        gap: 0,
        overflow: 'hidden',
      }}
    >
      {/* LEFT COLUMN — Laptop device ~55% */}
      <div
        style={{
          width: '55%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: `translateX(${laptopX}px)`,
          opacity: laptopOpacity,
          flexShrink: 0,
        }}
      >
        <DeviceFrame src="f6-builder-editor.png" kind="laptop" width={900} radius={16} />
      </div>

      {/* RIGHT COLUMN — Value copy + share moment */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          paddingLeft: 64,
          gap: 0,
        }}
      >
        {/* Three headline lines */}
        <div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
          <KineticText
            text={UZ.teacher[0]}
            delay={10}
            fontSize={40}
            color={INK}
            align="left"
            font={FONT.body}
          />
          <KineticText
            text={UZ.teacher[1]}
            delay={42}
            fontSize={40}
            color={INK}
            align="left"
            font={FONT.body}
          />
          <KineticText
            text={UZ.teacher[2]}
            delay={74}
            fontSize={40}
            color={INK}
            align="left"
            font={FONT.body}
          />
        </div>

        {/* SHARE MOMENT — link pill + copied tag + phones */}
        <div
          style={{
            marginTop: 52,
            display: 'flex',
            flexDirection: 'column',
            gap: 20,
          }}
        >
          {/* Pill row */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              gap: 16,
              position: 'relative',
            }}
          >
            {/* Link pill */}
            <div
              style={{
                opacity: pillOpacity,
                transform: `scale(${pillScale})`,
                transformOrigin: 'left center',
                background: WHITE,
                borderRadius: 999,
                boxShadow: '0 8px 24px rgba(0,0,0,0.10)',
                padding: '14px 28px',
                display: 'inline-flex',
                alignItems: 'center',
              }}
            >
              <span
                style={{
                  fontFamily: FONT.body,
                  fontWeight: 700,
                  fontSize: 28,
                  color: PRODUCT_BLUE,
                  letterSpacing: '-0.02em',
                }}
              >
                class-a.uz/h/a1b2c3
              </span>
            </div>

            {/* Copied tag */}
            <div
              style={{
                opacity: copiedOpacity,
                transform: `scale(${copiedScale})`,
                transformOrigin: 'left center',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span
                style={{
                  fontFamily: FONT.body,
                  fontWeight: 600,
                  fontSize: 26,
                  color: '#28c840',
                }}
              >
                ✓ nusxa olindi
              </span>
            </div>
          </div>

          {/* Flying phones — positioned relative to pill area */}
          <div style={{position: 'relative', height: 0}}>
            {/* Phone 1 */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                transform: `translate(${phone1X}px, ${phone1Y}px)`,
                opacity: phone1Opacity,
              }}
            >
              <DeviceFrame src="hub-reveal-final.png" kind="phone" width={150} />
            </div>

            {/* Phone 2 */}
            <div
              style={{
                position: 'absolute',
                top: 20,
                left: 60,
                transform: `translate(${phone2X}px, ${phone2Y}px)`,
                opacity: phone2Opacity,
              }}
            >
              <DeviceFrame src="hub-reveal-final.png" kind="phone" width={150} />
            </div>
          </div>
        </div>

        {/* TAG LINE — Avtomatik baholanadi */}
        <div
          style={{
            marginTop: 220,
            opacity: tagOpacity,
            transform: `translateY(${tagY}px)`,
          }}
        >
          <KineticText
            text={UZ.teacherTag}
            delay={0}
            fontSize={34}
            color={PRODUCT_BLUE}
            weight={700}
            align="left"
            font={FONT.body}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
