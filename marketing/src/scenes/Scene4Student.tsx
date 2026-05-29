import {AbsoluteFill, interpolate, spring, useCurrentFrame} from 'remotion';
import {KineticText} from '../components/KineticText';
import {DeviceFrame} from '../components/DeviceFrame';
import {UZ} from '../copy/uz';
import {
  INK,
  WHITE,
  PRODUCT_BLUE,
  GRAD,
  grad,
  EASE_SPRING,
  FONT,
  springBouncy,
} from '../theme/tokens';

// ---------------------------------------------------------------------------
// Scene 4 — THE HERO. Two acts in 390 local frames @30fps, 1920x1080.
//   ACT A (~10–180): the product's signature LOCKED→UNLOCKED node choreography.
//   ACT B (~185–360): four game cards pop in beat-synced over a closing tagline.
// All motion is recreated deterministically from useCurrentFrame() — no
// Date.now / Math.random / CSS keyframes. Root AbsoluteFill is transparent so
// the global light pale-blue Backdrop shows through; dark elements on light.
// ---------------------------------------------------------------------------

const fps = 30;

// Reusable clamped-eased interpolate.
const ease = (
  frame: number,
  range: [number, number],
  out: [number, number]
) =>
  interpolate(frame, range, out, {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_SPRING,
  });

// Linear clamped (for raw geometric travel — sparks, lock drop).
const lin = (frame: number, range: [number, number], out: [number, number]) =>
  interpolate(frame, range, out, {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

// ----- ACT A: a single "trial dot" --------------------------------------
const TrialDot: React.FC<{frame: number; start: number; live: boolean}> = ({
  frame,
  start,
  live,
}) => {
  // 0 → 1.18 → 1 overshoot pop driven by springBouncy.
  const s = spring({frame: frame - start, fps, config: springBouncy});
  const scale = s; // springBouncy overshoots past 1 then settles, giving the 1.18 pop
  // Once the node goes live (frame >= 105), the dots flush from gray to blue.
  const tint = live ? PRODUCT_BLUE : '#bdbdbd';
  return (
    <div
      style={{
        width: 20,
        height: 20,
        borderRadius: '50%',
        background: tint,
        transform: `scale(${Math.max(scale, 0)})`,
        opacity: ease(frame - start, [0, 6], [0, 1]),
        transition: 'none',
      }}
    />
  );
};

// ----- ACT A: padlock glyph (body + arc shackle) -------------------------
const Padlock: React.FC<{frame: number}> = ({frame}) => {
  // Shackle pops open (rotate ~70deg about its left foot) over 105–122,
  // then the whole lock drops away + spins + fades over 110–140.
  const shackleOpen = lin(frame, [105, 122], [0, 70]);
  const dropY = lin(frame, [110, 140], [0, 130]);
  const dropRot = lin(frame, [110, 140], [0, 38]);
  const fade = lin(frame, [122, 140], [1, 0]);
  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: `translate(-50%,-50%) translateY(${dropY}px) rotate(${dropRot}deg)`,
        opacity: fade,
        width: 64,
        height: 78,
      }}
    >
      {/* Shackle (arc) — a thick-bordered half-ring; rotates open from its base */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: 2,
          transform: `translateX(-50%) rotate(${shackleOpen}deg)`,
          transformOrigin: 'left bottom',
          width: 34,
          height: 34,
          borderTopLeftRadius: 18,
          borderTopRightRadius: 18,
          border: '7px solid #8a8a8a',
          borderBottom: 'none',
          boxSizing: 'border-box',
        }}
      />
      {/* Body */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          bottom: 0,
          transform: 'translateX(-50%)',
          width: 56,
          height: 46,
          borderRadius: 12,
          background: '#9a9a9a',
          boxShadow: 'inset 0 -4px 0 rgba(0,0,0,0.18)',
        }}
      >
        {/* keyhole */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: 14,
            transform: 'translateX(-50%)',
            width: 9,
            height: 9,
            borderRadius: '50%',
            background: '#6a6a6a',
          }}
        />
      </div>
    </div>
  );
};

// ----- ACT A: the burst + radial sparks at unlock ------------------------
const UnlockBurst: React.FC<{frame: number}> = ({frame}) => {
  const burstScale = lin(frame, [105, 140], [0.2, 1.3]);
  const burstOpacity = lin(frame, [105, 140], [0.85, 0]);
  const dist = lin(frame, [105, 140], [0, 110]);
  const sparkFade = lin(frame, [120, 140], [1, 0]);
  return (
    <>
      {/* radial burst circle */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 220,
          height: 220,
          borderRadius: '50%',
          transform: `translate(-50%,-50%) scale(${burstScale})`,
          background:
            'radial-gradient(circle, rgba(91,108,255,0.55) 0%, rgba(91,108,255,0) 70%)',
          opacity: burstOpacity,
        }}
      />
      {/* 4 spark dots fanning out radially */}
      {[0, 1, 2, 3].map((i) => {
        const angle = (i / 4) * Math.PI * 2;
        const x = Math.cos(angle) * dist;
        const y = Math.sin(angle) * dist;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              width: 16,
              height: 16,
              borderRadius: '50%',
              background: '#5b6cff',
              transform: `translate(-50%,-50%) translate(${x}px, ${y}px)`,
              opacity: sparkFade,
            }}
          />
        );
      })}
    </>
  );
};

// ----- ACT A: celebratory glow ring (140–180) ----------------------------
const GlowRing: React.FC<{frame: number}> = ({frame}) => {
  const ringScale = ease(frame, [140, 180], [0.5, 2.2]);
  // opacity pulses 0 → 0.6 → 0
  const ringOpacity = interpolate(
    frame,
    [140, 158, 180],
    [0, 0.6, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        width: 240,
        height: 240,
        borderRadius: '50%',
        border: '6px solid #5b6cff',
        transform: `translate(-50%,-50%) scale(${ringScale})`,
        opacity: ringOpacity,
      }}
    />
  );
};

// ----- ACT A: the node card (LOCKED → LIVE) ------------------------------
const NodeCard: React.FC<{frame: number}> = ({frame}) => {
  // Bind-in 50–80: scale 0.92→1, opacity 0→1.
  const bindScale = ease(frame, [50, 80], [0.92, 1]);
  const bindOpacity = ease(frame, [50, 70], [0, 1]);

  // Decaying shake 80–105.
  const shakeAmp = lin(frame, [80, 105], [5, 0]);
  const shakeX =
    frame >= 80 && frame <= 105 ? Math.sin((frame - 80) * 1.6) * shakeAmp : 0;

  // Gray → live color transition at unlock (105→125).
  const live = frame >= 105;
  const liveMix = ease(frame, [105, 125], [0, 1]);
  const fill = live ? PRODUCT_BLUE : '#e5e5e5';
  const lip = live ? '#0058b8' : '#bdbdbd';

  // Check/sparkle reveal on the live node (pops in just after unlock).
  const checkPop = spring({frame: frame - 116, fps, config: springBouncy});
  const checkOpacity = ease(frame, [114, 128], [0, 1]);

  return (
    <div
      style={{
        position: 'relative',
        width: 220,
        height: 220,
        opacity: bindOpacity,
        transform: `translateX(${shakeX}px) scale(${bindScale})`,
      }}
    >
      <GlowRing frame={frame} />
      {/* the pebble button */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 26,
          background: fill,
          boxShadow: `0 6px 0 ${lip}`,
          overflow: 'hidden',
        }}
      >
        {/* subtle top sheen on the live state */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 26,
            background:
              'linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0) 55%)',
            opacity: liveMix,
          }}
        />
        {/* white check mark — drawn as two rotated bars, springs in on unlock */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: `translate(-50%,-50%) scale(${Math.max(checkPop, 0)})`,
            opacity: checkOpacity,
            width: 96,
            height: 96,
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: 18,
              top: 50,
              width: 34,
              height: 12,
              borderRadius: 6,
              background: WHITE,
              transform: 'rotate(45deg)',
              transformOrigin: 'left center',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: 40,
              top: 58,
              width: 58,
              height: 12,
              borderRadius: 6,
              background: WHITE,
              transform: 'rotate(-50deg)',
              transformOrigin: 'left center',
            }}
          />
        </div>
      </div>
      {/* lock glyph sits over the gray state, then pops open + drops */}
      <Padlock frame={frame} />
      {/* burst + sparks at the unlock instant */}
      <UnlockBurst frame={frame} />
    </div>
  );
};

const ActA: React.FC<{frame: number}> = ({frame}) => {
  // Whole act fades out as Act B takes over (~178–192).
  const actOpacity = lin(frame, [178, 192], [1, 0]);
  const live = frame >= 105;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: 360,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 40,
        opacity: actOpacity,
      }}
    >
      {/* three staggered trial dots (left → right), ~8f apart */}
      <div style={{display: 'flex', gap: 26, height: 24, alignItems: 'center'}}>
        <TrialDot frame={frame} start={10} live={live} />
        <TrialDot frame={frame} start={18} live={live} />
        <TrialDot frame={frame} start={26} live={live} />
      </div>
      <NodeCard frame={frame} />
    </div>
  );
};

// ----- ACT B: a single game card ----------------------------------------
type GameCard = {src: string; gradient: readonly [string, string]; delay: number};

const GAME_CARDS: GameCard[] = [
  {src: 'f4-practice-arc.png', gradient: GRAD.game, delay: 185},
  {src: 'final-arc-darkOS.png', gradient: GRAD.interaction, delay: 217},
  {src: 'arc-ttt-question.png', gradient: GRAD.game, delay: 249},
  {
    src: 'living-backdrop-2-flashcards-gold.png',
    gradient: GRAD.content,
    delay: 281,
  },
];

const MontageCard: React.FC<{frame: number; card: GameCard}> = ({
  frame,
  card,
}) => {
  const s = spring({frame: frame - card.delay, fps, config: springBouncy});
  const scale = interpolate(s, [0, 1], [0.8, 1]);
  const opacity = ease(frame - card.delay, [0, 10], [0, 1]);
  const ty = interpolate(s, [0, 1], [30, 0]);
  return (
    <div
      style={{
        opacity,
        transform: `translateY(${ty}px) scale(${Math.max(scale, 0)})`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
      }}
    >
      {/* 6px top accent bar in the category gradient */}
      <div
        style={{
          height: 6,
          borderTopLeftRadius: 8,
          borderTopRightRadius: 8,
          background: grad(card.gradient),
          marginBottom: -2,
          marginLeft: 6,
          marginRight: 6,
        }}
      />
      <DeviceFrame src={card.src} kind="browser" width={420} />
    </div>
  );
};

const ActB: React.FC<{frame: number}> = ({frame}) => {
  // Bind-in from the moment the first card can pop.
  const actOpacity = ease(frame, [183, 195], [0, 1]);
  return (
    <div
      style={{
        position: 'absolute',
        left: 100,
        right: 100,
        top: 250,
        display: 'flex',
        justifyContent: 'center',
        gap: 36,
        opacity: actOpacity,
      }}
    >
      {GAME_CARDS.map((card) => (
        <MontageCard key={card.src} frame={frame} card={card} />
      ))}
    </div>
  );
};

export const Scene4Student: React.FC = () => {
  const frame = useCurrentFrame();
  const showActA = frame < 192;
  const showActB = frame >= 183;

  return (
    <AbsoluteFill style={{background: 'transparent'}}>
      {/* Title — top-center, dark ink on the light backdrop */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 70,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <KineticText
          text={UZ.studentTitle}
          color={INK}
          fontSize={46}
          delay={6}
          outAt={330}
        />
      </div>

      {showActA && <ActA frame={frame} />}
      {showActB && <ActB frame={frame} />}

      {/* Closing tagline — PRODUCT_BLUE, bold, bottom, in from ~frame 300 */}
      {frame >= 296 && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 90,
            display: 'flex',
            justifyContent: 'center',
            fontFamily: FONT.display,
          }}
        >
          <KineticText
            text={UZ.studentTag}
            color={PRODUCT_BLUE}
            fontSize={34}
            weight={800}
            delay={300}
          />
        </div>
      )}
    </AbsoluteFill>
  );
};
