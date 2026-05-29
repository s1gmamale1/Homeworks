# Class A Education Marketing Video — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a ~75s, 1920×1080 @30fps marketing video for Class A Education (the company behind the NETS Homeworks gamified-homework platform) in Remotion, and render it to `out/classa-marketing-75s.mp4`.

**Architecture:** Isolated `marketing/` Remotion project (does not touch product code). A single **continuous animated background** spans the whole timeline (smooth section-to-section color/aurora morph → no hard cuts), and **9 foreground scenes** are plain `<Sequence>` overlays. A frozen contract (`theme/tokens.ts` + `copy/uz.ts` + shared components) is built first; the 9 scenes are file-disjoint and built in parallel against that contract. Real product screenshots are composited in device frames via `<Img staticFile()>` (no flicker). Brand bookends are Class-A red; product demos are the cool-blue UI.

**Tech Stack:** Remotion 4.x, React 18.3, TypeScript, `@remotion/cli`, `@remotion/google-fonts` (Onest/Fredoka/Nunito), `@remotion/transitions` (optional fades), Node 24 / npm 11 (already installed).

**Verification model:** each task ends with `npm run typecheck` (tsc --noEmit) passing, and visual tasks additionally render a still via `npx remotion still ClassAMarketing out/check-<scene>.png --frame=<f>` and the frame is eyeballed against the storyboard. Final task renders the full MP4.

---

## File structure (decomposition locked here)

```
marketing/
  package.json
  remotion.config.ts
  tsconfig.json
  out/                       # render output (gitignored)
  public/
    shots/                   # ~15 hero screenshots copied from docs/screenshots/
    audio/                   # CC0 music bed (track.mp3)
    brand/                   # optional exact logo PNG drop-in
  src/
    index.ts                 # registerRoot
    Root.tsx                 # <Composition id="ClassAMarketing">
    theme/tokens.ts          # CONTRACT: colors, fonts, easing, frame constants, SCENES table
    copy/uz.ts               # CONTRACT: all Uzbek caption strings
    components/
      ClassALogo.tsx         # CONTRACT: animatable vector logo (A + sparkle)
      Wordmark.tsx           # CONTRACT: logo + "Class A Education"
      KineticText.tsx        # CONTRACT: word/line spring caption primitive
      DeviceFrame.tsx        # CONTRACT: browser/laptop/phone frame around an <Img>
      Backdrop.tsx           # CONTRACT: continuous aurora+blobs + section bg morph
      ProofCard.tsx          # CONTRACT: count-up proof card
      ModeChip.tsx           # CONTRACT: tutor mode pill
    scenes/
      Scene0Hook.tsx
      Scene1Problem.tsx
      Scene2Reveal.tsx
      Scene3Teacher.tsx
      Scene4Student.tsx
      Scene5Tutor.tsx
      Scene6Outcomes.tsx
      Scene7Proof.tsx
      Scene8CTA.tsx
    Marketing.tsx            # stitches Backdrop + all 9 scenes
```

**Scene frame table (absolute frames @30fps, total 2250 = 75s):**

| Scene | from | duration | seconds |
|-------|------|----------|---------|
| Hook | 0 | 150 | 0:00–0:05 |
| Problem | 150 | 360 | 0:05–0:17 |
| Reveal | 510 | 360 | 0:17–0:29 |
| Teacher | 870 | 330 | 0:29–0:40 |
| Student | 1200 | 390 | 0:40–0:53 |
| Tutor | 1590 | 210 | 0:53–1:00 |
| Outcomes | 1800 | 210 | 1:00–1:07 |
| Proof | 2010 | 150 | 1:07–1:12 |
| CTA | 2160 | 90 | 1:12–1:15 |

---

## Task 0: Scaffold the Remotion project

**Files:**
- Create: `marketing/package.json`, `marketing/remotion.config.ts`, `marketing/tsconfig.json`, `marketing/.gitignore`, `marketing/src/index.ts`, `marketing/src/Root.tsx`, `marketing/src/Marketing.tsx` (stub)

- [ ] **Step 1: Create `marketing/package.json`**

```json
{
  "name": "classa-marketing",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "remotion studio",
    "render": "remotion render ClassAMarketing out/classa-marketing-75s.mp4 --concurrency=50%",
    "still": "remotion still",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@remotion/cli": "^4.0.0",
    "@remotion/google-fonts": "^4.0.0",
    "@remotion/transitions": "^4.0.0",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "remotion": "^4.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 2: Create `marketing/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "lib": ["DOM", "ESNext"]
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create `marketing/remotion.config.ts`**

```ts
import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// If frames flicker on Windows, drop concurrency: Config.setConcurrency(1);
```

- [ ] **Step 4: Create `marketing/.gitignore`**

```
node_modules/
out/
.remotion/
```

- [ ] **Step 5: Create `marketing/src/index.ts`**

```ts
import {registerRoot} from 'remotion';
import {RemotionRoot} from './Root';

registerRoot(RemotionRoot);
```

- [ ] **Step 6: Create `marketing/src/Marketing.tsx` (stub — replaced in Task 9)**

```tsx
import {AbsoluteFill} from 'remotion';

export const Marketing: React.FC<{lang: 'uz'}> = () => {
  return <AbsoluteFill style={{backgroundColor: '#0B0B0D'}} />;
};
```

- [ ] **Step 7: Create `marketing/src/Root.tsx`**

```tsx
import {Composition} from 'remotion';
import {Marketing} from './Marketing';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ClassAMarketing"
      component={Marketing}
      durationInFrames={2250}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{lang: 'uz' as const}}
    />
  );
};
```

- [ ] **Step 8: Install dependencies**

Run (in `marketing/`): `npm install`
Expected: completes; `node_modules/` populated; no peer-dep errors that block (warnings OK).

- [ ] **Step 9: Verify it boots**

Run: `npm run typecheck`
Expected: PASS (no TS errors).
Run: `npx remotion still ClassAMarketing out/boot.png --frame=0`
Expected: writes `out/boot.png` (a black 1920×1080 frame), no errors.

- [ ] **Step 10: Commit**

```bash
git add marketing/package.json marketing/tsconfig.json marketing/remotion.config.ts marketing/.gitignore marketing/src/index.ts marketing/src/Root.tsx marketing/src/Marketing.tsx
git commit -m "feat(marketing): scaffold Remotion project for Class A video"
```

---

## Task 1: Theme tokens (the contract) + Uzbek copy

**Files:**
- Create: `marketing/src/theme/tokens.ts`, `marketing/src/copy/uz.ts`

- [ ] **Step 1: Create `marketing/src/theme/tokens.ts`**

```ts
import {Easing} from 'remotion';

// ---- Canvas ----
export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const DURATION_IN_FRAMES = 2250; // 75s

// ---- Class A brand (bookends) ----
export const BRAND_RED = '#F40B16';      // single source of truth — tune to exact hex
export const BRAND_RED_DEEP = '#C0070F';
export const INK = '#0B0B0D';
export const WHITE = '#FFFFFF';

// ---- NETS Homeworks product palette (demo beats) ----
export const PRODUCT_BLUE = '#0a72e0';
export const ACCENT = '#0066CC';
export const PAGE_LIGHT_TOP = '#f5f9ff';
export const PAGE_LIGHT_BOT = '#e9f1fe';

export const GRAD = {
  game: ['#b388eb', '#8a5fc8'],
  content: ['#ffd166', '#f4a261'],
  language: ['#74aa9c', '#4a8576'],
  boss: ['#e26d6d', '#c93a3a'],
  interaction: ['#5e9ed6', '#4677b8'],
} as const;

export const grad = (pair: readonly [string, string]) =>
  `linear-gradient(135deg, ${pair[0]}, ${pair[1]})`;

// ---- Type ----
export const FONT = {
  display: '"Fredoka", "Onest", system-ui, sans-serif',
  body: '"Onest", system-ui, sans-serif',
  hubBody: '"Nunito", "Onest", system-ui, sans-serif',
};

// ---- Motion ----
export const EASE_SPRING = Easing.bezier(0.16, 1, 0.3, 1); // product signature
export const springCfg = {damping: 200, mass: 1, stiffness: 100} as const;
export const springBouncy = {damping: 14, mass: 0.8, stiffness: 120} as const;

// ---- Scene boundaries (absolute frames) ----
export const SCENES = {
  hook:     {from: 0,    duration: 150},
  problem:  {from: 150,  duration: 360},
  reveal:   {from: 510,  duration: 360},
  teacher:  {from: 870,  duration: 330},
  student:  {from: 1200, duration: 390},
  tutor:    {from: 1590, duration: 210},
  outcomes: {from: 1800, duration: 210},
  proof:    {from: 2010, duration: 150},
  cta:      {from: 2160, duration: 90},
} as const;
```

- [ ] **Step 2: Create `marketing/src/copy/uz.ts`** (Uzbek captions — DRAFT pending native proofread)

```ts
export const UZ = {
  hook: ['Uy vazifasidan o‘quvchilar bezgan.', 'Tekshiruvdan o‘qituvchilar charchagan.'],
  problem: ['Jonsiz varaqalar.', 'Ko‘chirilgan javoblar.', 'Juda kech keladigan izoh.'],
  problemTurn: 'Yaxshiroq yo‘l bor.',
  revealMeet: 'Class A Education',
  revealLine: 'Har bir dars — qiziqarli o‘yinga aylanadi.',
  teacher: ['Daqiqalar ichida tayyorlang.', 'Kod kerak emas. LMS kerak emas.', 'Bitta havola orqali ulashing.'],
  teacherTag: 'Avtomatik baholanadi.',
  studentTitle: 'O‘quvchilar bajarishni istaydigan 8 xil o‘yin.',
  studentTag: 'Har bir javob — shu zahoti baholanadi.',
  tutorLine: 'Jonli AI-repetitor: yo‘l ko‘rsatadi, javobni aytmaydi.',
  tutorModes: ['Tanishuv', 'Mashq', 'Boss'],
  outcomes: ['AI-bossni yenging.', 'Nimani o‘zlashtirganini aniq ko‘ring.', 'Halol mehnat — beozor nazorat.'],
  proof: [
    {value: 3, label: 'til'},
    {value: 8, label: 'o‘yin turi'},
    {value: 0, label: 'o‘rnatish (havola orqali)'},
    {value: 2, label: 'soniyada AI baholash', suffix: 's'},
  ],
  ctaTitle: 'Class A Education’ni maktabingizga olib keling.',
  ctaSub: 'Demo uchun bog‘laning',
  ctaUrl: 'classaedu.uz', // placeholder — confirm real URL
} as const;
```

- [ ] **Step 3: Verify**

Run: `npm run typecheck`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add marketing/src/theme/tokens.ts marketing/src/copy/uz.ts
git commit -m "feat(marketing): theme tokens + Uzbek copy contract"
```

---

## Task 2: Fonts loader + KineticText primitive

**Files:**
- Create: `marketing/src/theme/fonts.ts`, `marketing/src/components/KineticText.tsx`

- [ ] **Step 1: Create `marketing/src/theme/fonts.ts`**

```ts
import {loadFont as loadOnest} from '@remotion/google-fonts/Onest';
import {loadFont as loadFredoka} from '@remotion/google-fonts/Fredoka';
import {loadFont as loadNunito} from '@remotion/google-fonts/Nunito';

loadOnest();
loadFredoka();
loadNunito();
```

(Import this once in `Marketing.tsx` so fonts are ready before render.)

- [ ] **Step 2: Create `marketing/src/components/KineticText.tsx`**

```tsx
import {interpolate, useCurrentFrame} from 'remotion';
import {EASE_SPRING, FONT, WHITE} from '../theme/tokens';

type Props = {
  text: string;
  /** local frame at which this line starts revealing */
  delay?: number;
  perWord?: number;       // frames between words
  fontSize?: number;
  weight?: number;
  color?: string;
  font?: string;
  /** local frame at which the line begins to fade out (optional) */
  outAt?: number;
  align?: 'left' | 'center';
  highlight?: string[];   // words to color with `highlightColor`
  highlightColor?: string;
};

export const KineticText: React.FC<Props> = ({
  text, delay = 0, perWord = 4, fontSize = 64, weight = 700,
  color = WHITE, font = FONT.display, outAt, align = 'center',
  highlight = [], highlightColor,
}) => {
  const frame = useCurrentFrame();
  const words = text.split(' ');
  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', gap: '0 0.28em',
      justifyContent: align === 'center' ? 'center' : 'flex-start',
      fontFamily: font, fontSize, fontWeight: weight, color, lineHeight: 1.1,
      letterSpacing: '-0.01em', maxWidth: '80%',
    }}>
      {words.map((w, i) => {
        const start = delay + i * perWord;
        const o = interpolate(frame, [start, start + 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_SPRING});
        const y = interpolate(frame, [start, start + 12], [22, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_SPRING});
        const outO = outAt === undefined ? 1 : interpolate(frame, [outAt, outAt + 14], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        const isHi = highlight.includes(w.replace(/[.,]/g, ''));
        return (
          <span key={i} style={{
            display: 'inline-block', opacity: o * outO, transform: `translateY(${y}px)`,
            color: isHi && highlightColor ? highlightColor : color,
          }}>{w}</span>
        );
      })}
    </div>
  );
};
```

- [ ] **Step 3: Verify**

Run: `npm run typecheck`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add marketing/src/theme/fonts.ts marketing/src/components/KineticText.tsx
git commit -m "feat(marketing): font loader + KineticText primitive"
```

---

## Task 3: ClassALogo + Wordmark (brand-critical vector)

**Files:**
- Create: `marketing/src/components/ClassALogo.tsx`, `marketing/src/components/Wordmark.tsx`

- [ ] **Step 1: Create `marketing/src/components/ClassALogo.tsx`**

The logo = red square + bold white "A" (flat apex, triangular counter, open bottom notch) + 4-point concave sparkle upper-right. `progress` 0→1 drives draw-in; `twinkle` 0→1 drives sparkle pulse.

```tsx
import {BRAND_RED, WHITE} from '../theme/tokens';

type Props = {size?: number; progress?: number; twinkle?: number; bg?: string; corner?: number};

export const ClassALogo: React.FC<Props> = ({size = 320, progress = 1, twinkle = 1, bg = BRAND_RED, corner = 0.14}) => {
  const aOpacity = Math.min(1, progress * 1.3);
  const aY = (1 - Math.min(1, progress * 1.3)) * 30;
  const sp = Math.max(0, (progress - 0.45) / 0.55); // sparkle comes in after the A
  const sparkleScale = sp * (1 + 0.12 * Math.sin(twinkle * Math.PI));
  return (
    <svg width={size} height={size} viewBox="0 0 200 200" fill="none">
      <rect x="0" y="0" width="200" height="200" rx={200 * corner} fill={bg} />
      {/* Bold A — outer silhouette with triangular counter + open bottom notch (even-odd) */}
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
      <g style={{transformOrigin: '156px 60px', transform: `scale(${sparkleScale})`, opacity: sp}}>
        <path fill={WHITE} d="M156 30 C159 50 166 57 186 60 C166 63 159 70 156 90 C153 70 146 63 126 60 C146 57 153 50 156 30 Z" />
      </g>
    </svg>
  );
};
```

> NOTE (fidelity step): open `out/logo.png` (Step 3) beside the reference and nudge the `d=` path coordinates + `BRAND_RED`/`corner` until it matches. This is expected hand-tuning, not a placeholder.

- [ ] **Step 2: Create `marketing/src/components/Wordmark.tsx`**

```tsx
import {FONT, INK, WHITE} from '../theme/tokens';
import {ClassALogo} from './ClassALogo';

type Props = {logoSize?: number; color?: string; fontSize?: number; progress?: number; twinkle?: number; layout?: 'row' | 'col'};

export const Wordmark: React.FC<Props> = ({logoSize = 140, color = WHITE, fontSize = 56, progress = 1, twinkle = 1, layout = 'row'}) => (
  <div style={{display: 'flex', flexDirection: layout === 'row' ? 'row' : 'column', alignItems: 'center', gap: layout === 'row' ? 28 : 18}}>
    <ClassALogo size={logoSize} progress={progress} twinkle={twinkle} />
    <div style={{fontFamily: FONT.display, fontWeight: 700, fontSize, color, letterSpacing: '-0.02em', lineHeight: 1}}>
      Class A <span style={{opacity: 0.85}}>Education</span>
    </div>
  </div>
);
```

- [ ] **Step 3: Verify (visual)**

Temporarily render the logo: add to `Marketing.tsx` stub a `<ClassALogo size={400}/>` centered, then:
Run: `npx remotion still ClassAMarketing out/logo.png --frame=1`
Expected: red square, white A, sparkle. Eyeball vs the brand PNG; tune path if needed. Revert the stub edit after.

- [ ] **Step 4: Commit**

```bash
git add marketing/src/components/ClassALogo.tsx marketing/src/components/Wordmark.tsx
git commit -m "feat(marketing): Class A logo + wordmark (animatable vector)"
```

---

## Task 4: Backdrop (continuous aurora + section color morph)

**Files:**
- Create: `marketing/src/components/Backdrop.tsx`

- [ ] **Step 1: Create `marketing/src/components/Backdrop.tsx`**

Spans the full 2250 frames. Interpolates the page background through the sections (dark → red → light → red) and floats soft aurora blobs (recreated from the product's living-backdrop). Driven entirely by the GLOBAL frame (use `useCurrentFrame()` at the Marketing level — Backdrop is NOT inside a Sequence).

```tsx
import {AbsoluteFill, interpolate, interpolateColors, useCurrentFrame} from 'remotion';
import {BRAND_RED, INK, PAGE_LIGHT_TOP, PAGE_LIGHT_BOT, PRODUCT_BLUE} from '../theme/tokens';

const BG_KEYS =   [0,   150,  510,      870,           1200,          2010,     2160, 2250];
const BG_COLORS = [INK, INK,  BRAND_RED, PAGE_LIGHT_TOP, PAGE_LIGHT_TOP, PAGE_LIGHT_BOT, BRAND_RED, BRAND_RED];

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
```

- [ ] **Step 2: Verify**

Run: `npm run typecheck` → PASS.
(Visual check happens in Task 9 once scenes overlay it.)

- [ ] **Step 3: Commit**

```bash
git add marketing/src/components/Backdrop.tsx
git commit -m "feat(marketing): continuous aurora backdrop with section color morph"
```

---

## Task 5: DeviceFrame + ProofCard + ModeChip helpers

**Files:**
- Create: `marketing/src/components/DeviceFrame.tsx`, `marketing/src/components/ProofCard.tsx`, `marketing/src/components/ModeChip.tsx`

- [ ] **Step 1: Create `marketing/src/components/DeviceFrame.tsx`**

```tsx
import {Img, staticFile} from 'remotion';

type Props = {src: string; kind?: 'browser' | 'laptop' | 'phone'; width: number; radius?: number};

export const DeviceFrame: React.FC<Props> = ({src, kind = 'browser', width, radius = 18}) => {
  const bar = kind === 'phone' ? 0 : 36;
  return (
    <div style={{
      width, borderRadius: radius + 8, background: '#1d1d1f', padding: 10,
      boxShadow: '0 40px 120px rgba(0,0,0,0.45)',
    }}>
      {bar > 0 && (
        <div style={{height: bar, display: 'flex', alignItems: 'center', gap: 8, padding: '0 14px'}}>
          {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
            <span key={c} style={{width: 12, height: 12, borderRadius: '50%', background: c}} />
          ))}
        </div>
      )}
      <Img src={staticFile(`shots/${src}`)} style={{width: '100%', display: 'block', borderRadius: radius, objectFit: 'cover'}} />
    </div>
  );
};
```

- [ ] **Step 2: Create `marketing/src/components/ProofCard.tsx`**

```tsx
import {interpolate, useCurrentFrame} from 'remotion';
import {EASE_SPRING, FONT, INK, WHITE} from '../theme/tokens';

type Props = {value: number; label: string; suffix?: string; delay?: number; color?: string};

export const ProofCard: React.FC<Props> = ({value, label, suffix = '', delay = 0, color = WHITE}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 24], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_SPRING});
  const shown = Math.round(value * t);
  const scale = interpolate(frame, [delay, delay + 18], [0.8, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_SPRING});
  return (
    <div style={{transform: `scale(${scale})`, opacity: t, textAlign: 'center', minWidth: 220}}>
      <div style={{fontFamily: FONT.display, fontWeight: 700, fontSize: 96, color, lineHeight: 1}}>{shown}{suffix}</div>
      <div style={{fontFamily: FONT.body, fontSize: 26, color, opacity: 0.85, marginTop: 8}}>{label}</div>
    </div>
  );
};
```

- [ ] **Step 3: Create `marketing/src/components/ModeChip.tsx`**

```tsx
import {interpolate, useCurrentFrame} from 'remotion';
import {EASE_SPRING, FONT, WHITE} from '../theme/tokens';

type Props = {label: string; delay?: number; tint: string};

export const ModeChip: React.FC<Props> = ({label, delay = 0, tint}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [delay, delay + 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_SPRING});
  const y = interpolate(frame, [delay, delay + 12], [16, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_SPRING});
  return (
    <div style={{
      opacity: o, transform: `translateY(${y}px)`, padding: '14px 28px', borderRadius: 999,
      background: tint, color: WHITE, fontFamily: FONT.body, fontWeight: 700, fontSize: 28,
      boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
    }}>{label}</div>
  );
};
```

- [ ] **Step 4: Verify** — `npm run typecheck` → PASS.

- [ ] **Step 5: Commit**

```bash
git add marketing/src/components/DeviceFrame.tsx marketing/src/components/ProofCard.tsx marketing/src/components/ModeChip.tsx
git commit -m "feat(marketing): DeviceFrame, ProofCard, ModeChip helpers"
```

---

## Task 6: Copy hero screenshots into public/shots + source music

**Files:**
- Create: `marketing/public/shots/*.png` (copied), `marketing/public/audio/track.mp3`

- [ ] **Step 1: Copy the 15 hero shots** (PowerShell)

```powershell
$dst = "marketing/public/shots"; New-Item -ItemType Directory -Force $dst | Out-Null
$shots = @(
 "final-cbp-darkOS.png","reflection-debrief-desktop-light.png","reflection-debrief-desktop-dark.png",
 "final-arc-darkOS.png","f4-practice-arc.png","hub-reveal-final.png","hub-r2-darkOS.png",
 "f5-tutor-open.png","f5-tutor-reply.png","f4-boss-arena.png","f6-builder-editor.png",
 "f3-flashcards-done.png","living-backdrop-2-flashcards-gold.png","arc-ttt-question.png","integrity-3-nudge.png"
)
foreach ($s in $shots) { Copy-Item "docs/screenshots/$s" "$dst/$s" -ErrorAction SilentlyContinue }
Get-ChildItem $dst | Select-Object Name
```

Expected: the listed files appear in `marketing/public/shots/`. (Some f0-/f-prefixed names may differ — if a copy is missing, pick the nearest hero from the inventory in the spec and adjust the scene's `src`.)

- [ ] **Step 2: Source a CC0 music bed**

Fetch one CC0 modern-tech track (~75s) from Pixabay Music / Mixkit / Chosic (CC0) and save as `marketing/public/audio/track.mp3`. If a clean licensed download isn't obtainable programmatically, create a silent placeholder so render works and flag it:

```powershell
# fallback only if no track sourced:
# (leave public/audio empty and set HAS_MUSIC=false in Marketing.tsx)
```

- [ ] **Step 3: Verify** — list both dirs; confirm shots present.

- [ ] **Step 4: Commit**

```bash
git add marketing/public/shots marketing/public/audio
git commit -m "assets(marketing): hero screenshots + music bed"
```

---

## Tasks 7.0–7.8: Build the 9 scenes (PARALLELIZABLE — file-disjoint)

**Shared contract for every scene** (all symbols defined in Tasks 1–5):
- Import tokens from `../theme/tokens` and copy from `../copy/uz`.
- Each scene is a self-contained `React.FC` rendering an `<AbsoluteFill>` with **transparent** background (the global Backdrop shows through) UNLESS noted (Reveal/CTA paint red, Hook/Problem darken).
- Each scene uses **local** frames (it will be wrapped in `<Sequence>` in Task 9, so frame 0 = scene start). Use `useCurrentFrame()`.
- Reveal/fade content with `interpolate(frame, [...], [...], {extrapolateLeft:'clamp', extrapolateRight:'clamp', easing: EASE_SPRING})` and `spring()`.
- Compose screenshots with `<DeviceFrame src="..." .../>`.
- Verify each: `npx remotion still ClassAMarketing out/check-<scene>.png --frame=<absoluteFrame>` (absolute frame from the SCENES table) after Task 9 wires it; during solo build, temporarily mount the scene in Marketing stub to grab a still.

### Task 7.0: Scene0Hook.tsx (frames 0–150) — REFERENCE IMPLEMENTATION

**Files:** Create `marketing/src/scenes/Scene0Hook.tsx`

- [ ] **Step 1: Implement**

```tsx
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {KineticText} from '../components/KineticText';
import {UZ} from '../copy/uz';
import {BRAND_RED, FONT, INK} from '../theme/tokens';

export const Scene0Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const darken = interpolate(frame, [0, 20], [1, 0.82], {extrapolateRight: 'clamp'});
  // a faint red spark pulse bottom
  const spark = interpolate(frame, [60, 110], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <AbsoluteFill style={{background: INK, opacity: darken}} />
      <div style={{display: 'flex', flexDirection: 'column', gap: 24, zIndex: 1}}>
        <KineticText text={UZ.hook[0]} delay={6} fontSize={72} />
        <KineticText text={UZ.hook[1]} delay={26} fontSize={72} outAt={130} />
      </div>
      <div style={{position: 'absolute', bottom: 120, width: 220, height: 6, borderRadius: 3,
        background: BRAND_RED, opacity: spark, filter: 'blur(2px)', boxShadow: `0 0 40px ${BRAND_RED}`}} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Verify** — mount in stub, `npx remotion still ClassAMarketing out/check-hook.png --frame=40` → both lines visible, dark bg. `npm run typecheck` PASS.
- [ ] **Step 3: Commit** `git add marketing/src/scenes/Scene0Hook.tsx && git commit -m "feat(marketing): Scene 0 hook"`

### Task 7.1: Scene1Problem.tsx (frames 150–510)
**Build spec:** three problem lines `UZ.problem[0..2]` revealing in sequence (KineticText delays ~6/40/74), each in a desaturated/muted color (`#9aa3ad`), over a dark tint. Add 2–3 faint document-rectangle shapes (gray, low opacity) drifting slowly + a slow-ticking clock arc (an SVG circle with a rotating hand via `interpolate(frame,[0,360],[0,360])`). At ~frame 300 (local), fade the lines out and bring `UZ.problemTurn` ("Yaxshiroq yo'l bor.") center in white, scaling up — sets up the smash to Reveal. Background stays dark (transparent over Backdrop which is still INK here). End-state: only the turn line. **Verify** still at absolute 480 → shows the turn line.
**Commit:** `feat(marketing): Scene 1 problem`

### Task 7.2: Scene2Reveal.tsx (frames 510–870)
**Build spec:** Backdrop is already morphing to red here. Paint an `<AbsoluteFill background={BRAND_RED}>` that fades IN over frames 0–18 (so the smash-cut from dark→red lands hard). Center the `<Wordmark progress={p} twinkle={tw} color={WHITE} logoSize={180} fontSize={72}/>` where `p = spring({frame, fps:30, config: springBouncy})` (logo A draws, sparkle twinkles ~frame 25+). Hold wordmark to ~frame 150. Then bring `UZ.revealLine` below it (KineticText, white, fontSize 40, delay 150). From ~frame 250, transition: shrink/raise the wordmark to a small top-left lockup AND slide up a `<DeviceFrame src="hub-r2-darkOS.png" kind="browser" width={1100}/>` from the bottom (translateY interpolate 400→120) — this is the red→product handoff. **Verify** stills at absolute 560 (logo assembling) and 820 (hub rising). **Commit:** `feat(marketing): Scene 2 brand reveal`

### Task 7.3: Scene3Teacher.tsx (frames 870–1200)
**Build spec:** Light section. Left: `<DeviceFrame src="f6-builder-editor.png" kind="laptop" width={1000}/>` sliding in from left (translateX -80→0, opacity, spring). Right column: `UZ.teacher[0..2]` as three stacked KineticText lines (INK color, FONT.body, left-aligned, fontSize 40, delays 10/40/70). At ~frame 150 animate a "link pill" — a rounded pill showing `/h/a1b2c3` that scales in, then a small "✓ nusxa olindi" (copied) tag, then two small phone `<DeviceFrame kind="phone">` (use `hub-reveal-final.png`) fly in from the pill toward bottom-right (translate + fade). Bottom: `UZ.teacherTag` ("Avtomatik baholanadi.") in PRODUCT_BLUE, bold, appears ~frame 220. **Verify** still at absolute 1050. **Commit:** `feat(marketing): Scene 3 teacher build+share`

### Task 7.4: Scene4Student.tsx (frames 1200–1590) — the wow beat
**Build spec:** Title `UZ.studentTitle` top-center (KineticText, INK, fontSize 48, delay 6, outAt 320). Center: a compact recreation of the **hub unlock choreography** using the real beat timings scaled to this window:
 - 0–40: three "trial dots" pop in (scale 0→1.18→1, stagger 8f, `springBouncy`).
 - 40–70: a node card (rounded 26px, gray `#e5e5e5`) binds in, grayscale.
 - 70–95: node shakes (translateX ±4px sine).
 - 95–130: "chain snap" — two short bars recoil/rotate away + a radial `burst` circle scales 0.2→1.3 fading, 4 spark dots fan out (use `--angle` via `Math.cos/sin(i/4*2π)`), node transitions grayscale→full color (PRODUCT_BLUE pebble with `#0058b8` bottom lip).
 - 130–170: a glow ring expands (scale 0.5→2.2, fading) — celebrate.
Then (frame ~180–360) a **beat-synced game montage**: 4 cards pop in sequence (stagger ~30f), each a `<DeviceFrame>` of a game shot with a category-gradient top bar: `f4-practice-arc.png` (game/purple), `final-arc-darkOS.png` (interaction/blue), `arc-ttt-question.png` (game/purple), `living-backdrop-2-flashcards-gold.png` (content/gold). Tag `UZ.studentTag` bottom (~frame 300). Background (via Backdrop) is light here; optionally tint section blobs. **Verify** stills at absolute 1320 (snap) and 1500 (montage). **Commit:** `feat(marketing): Scene 4 student hub + game montage`

### Task 7.5: Scene5Tutor.tsx (frames 1590–1800)
**Build spec:** Right: `<DeviceFrame src="f5-tutor-open.png" kind="browser" width={820}/>` settling in (spring). Over/beside it, a chat bubble that "types" — reveal `UZ.tutorLine` character-by-character via `interpolate(frame,[20,120],[0, text.length])` then `text.slice(0, n)`. Left/below: three `<ModeChip>` for `UZ.tutorModes` with tints GRAD.interaction[0], GRAD.game[0], GRAD.boss[0], delays 60/72/84. **Verify** still at absolute 1700. **Commit:** `feat(marketing): Scene 5 AI tutor`

### Task 7.6: Scene6Outcomes.tsx (frames 1800–2010)
**Build spec:** Three quick sub-beats sharing the window (~70f each), each = one `<DeviceFrame>` + one `UZ.outcomes[i]` caption, crossfading:
 - 0–80: `f4-boss-arena.png` + `UZ.outcomes[0]` ("AI-bossni yenging.")
 - 70–150: `reflection-debrief-desktop-light.png` + `UZ.outcomes[1]`
 - 140–210: `integrity-3-nudge.png` + `UZ.outcomes[2]`
Use opacity interpolation per sub-beat (in/out) so they hand off cleanly. Captions INK, fontSize 40. **Verify** stills at 1840 / 1910 / 1980. **Commit:** `feat(marketing): Scene 6 outcomes + integrity`

### Task 7.7: Scene7Proof.tsx (frames 2010–2160)
**Build spec:** Soft brand-tinted section. Row of four `<ProofCard>` from `UZ.proof` (color INK), staggered delays 6/20/34/48; the `value:0` install card should display the label only (or "0→1" link glyph) — render `value` count-up as usual but for the install card show the label emphasised. Small eyebrow above: "Maktablar uchun" (For schools). **Verify** still at absolute 2120. **Commit:** `feat(marketing): Scene 7 proof points`

### Task 7.8: Scene8CTA.tsx (frames 2160–2250)
**Build spec:** `<AbsoluteFill background={BRAND_RED}>` (fades in 0–12). Center `<Wordmark color={WHITE} layout="col" logoSize={160} fontSize={64}/>` (sparkle does a final twinkle). Below: `UZ.ctaTitle` (white, fontSize 44, delay 18), then `UZ.ctaSub` + `UZ.ctaUrl` in a white pill (delay 40). Gentle scale-settle on the whole group; hold to end; last 12f fade to slightly darker red. **Verify** still at absolute 2210. **Commit:** `feat(marketing): Scene 8 CTA`

---

## Task 8: Music wiring

**Files:** Modify `marketing/src/Marketing.tsx` (done in Task 9), uses `public/audio/track.mp3`

- [ ] **Step 1:** In Marketing (Task 9) add `<Audio src={staticFile('audio/track.mp3')} />` if the file exists; gate behind a `HAS_MUSIC` const. Optionally `volume` fade-in first 15f and fade-out last 30f via a function `(f) => interpolate(f, [0,15, 2220,2250], [0,1,1,0])`.
- [ ] **Step 2: Verify** — render still doesn't error on audio; a 2s test render plays music.

---

## Task 9: Stitch Marketing.tsx + full render

**Files:** Modify `marketing/src/Marketing.tsx`

- [ ] **Step 1: Implement the master composition**

```tsx
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import './theme/fonts';
import {SCENES} from './theme/tokens';
import {Backdrop} from './components/Backdrop';
import {Scene0Hook} from './scenes/Scene0Hook';
import {Scene1Problem} from './scenes/Scene1Problem';
import {Scene2Reveal} from './scenes/Scene2Reveal';
import {Scene3Teacher} from './scenes/Scene3Teacher';
import {Scene4Student} from './scenes/Scene4Student';
import {Scene5Tutor} from './scenes/Scene5Tutor';
import {Scene6Outcomes} from './scenes/Scene6Outcomes';
import {Scene7Proof} from './scenes/Scene7Proof';
import {Scene8CTA} from './scenes/Scene8CTA';

const HAS_MUSIC = true; // set false if no track sourced

export const Marketing: React.FC<{lang: 'uz'}> = () => {
  const S = SCENES;
  return (
    <AbsoluteFill>
      <Backdrop />
      <Sequence from={S.hook.from} durationInFrames={S.hook.duration}><Scene0Hook /></Sequence>
      <Sequence from={S.problem.from} durationInFrames={S.problem.duration}><Scene1Problem /></Sequence>
      <Sequence from={S.reveal.from} durationInFrames={S.reveal.duration}><Scene2Reveal /></Sequence>
      <Sequence from={S.teacher.from} durationInFrames={S.teacher.duration}><Scene3Teacher /></Sequence>
      <Sequence from={S.student.from} durationInFrames={S.student.duration}><Scene4Student /></Sequence>
      <Sequence from={S.tutor.from} durationInFrames={S.tutor.duration}><Scene5Tutor /></Sequence>
      <Sequence from={S.outcomes.from} durationInFrames={S.outcomes.duration}><Scene6Outcomes /></Sequence>
      <Sequence from={S.proof.from} durationInFrames={S.proof.duration}><Scene7Proof /></Sequence>
      <Sequence from={S.cta.from} durationInFrames={S.cta.duration}><Scene8CTA /></Sequence>
      {HAS_MUSIC && <Audio src={staticFile('audio/track.mp3')} />}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Typecheck** — `npm run typecheck` → PASS.

- [ ] **Step 3: Grab a still per scene** to verify each beat reads:

```bash
npx remotion still ClassAMarketing out/s0.png --frame=40
npx remotion still ClassAMarketing out/s1.png --frame=480
npx remotion still ClassAMarketing out/s2.png --frame=820
npx remotion still ClassAMarketing out/s3.png --frame=1050
npx remotion still ClassAMarketing out/s4.png --frame=1500
npx remotion still ClassAMarketing out/s5.png --frame=1700
npx remotion still ClassAMarketing out/s6.png --frame=1910
npx remotion still ClassAMarketing out/s7.png --frame=2120
npx remotion still ClassAMarketing out/s8.png --frame=2210
```

Eyeball each against the storyboard. Fix timing/layout issues in the offending scene.

- [ ] **Step 4: Full render**

Run: `npm run render`
Expected: `out/classa-marketing-75s.mp4` produced (1920×1080, H.264, ~75s). If frames flicker, set `Config.setConcurrency(1)` in `remotion.config.ts` and re-render.

- [ ] **Step 5: Report** duration, file size, resolution; surface the MP4 path. Flag the Uzbek-copy proofread + exact-red/URL confirmations.

- [ ] **Step 6: Commit**

```bash
git add marketing/src/Marketing.tsx
git commit -m "feat(marketing): stitch all scenes + audio into master composition"
```

---

## Self-review notes (planner)

- **Spec coverage:** every storyboard beat (§5) → a Scene task (7.0–7.8); brand (§4.1) → Tasks 3/7.2/7.8; product tokens (§4.2) → Task 1; architecture (§6) → Tasks 0,4,9; build plan (§7) → Tasks 0–9; music (§8) → Tasks 6,8; risks (§9) surfaced in Task 9 Step 5.
- **No undefined refs:** all components (KineticText, ClassALogo, Wordmark, Backdrop, DeviceFrame, ProofCard, ModeChip) and constants (tokens, UZ) are defined in Tasks 1–5 before scenes consume them.
- **Parallelization:** Tasks 7.0–7.8 touch disjoint files (`scenes/SceneN*.tsx`) and only READ the contract → safe to dispatch as parallel sub-agents. Task 9 (integration) is orchestrator-only and runs after the swarm.
- **Known hand-tuning (not placeholders):** logo path fidelity (Task 3 Step 3), exact brand red/URL, screenshot filename drift (Task 6 Step 1), Uzbek proofread.
