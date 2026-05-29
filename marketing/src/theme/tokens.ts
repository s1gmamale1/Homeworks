import {Easing} from 'remotion';

// ---- Canvas ----
export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const DURATION_IN_FRAMES = 2250; // 75s

// ---- Class A brand (bookends) ----
export const BRAND_RED = '#F40B16'; // single source of truth — tune to exact hex
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
  hook: {from: 0, duration: 150},
  problem: {from: 150, duration: 360},
  reveal: {from: 510, duration: 360},
  teacher: {from: 870, duration: 330},
  student: {from: 1200, duration: 390},
  tutor: {from: 1590, duration: 210},
  outcomes: {from: 1800, duration: 210},
  proof: {from: 2010, duration: 150},
  cta: {from: 2160, duration: 90},
} as const;
