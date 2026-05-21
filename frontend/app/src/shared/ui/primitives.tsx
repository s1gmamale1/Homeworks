import type { HTMLAttributes, ReactNode, ButtonHTMLAttributes } from "react";
import s from "./primitives.module.css";

type Div = { children?: ReactNode; className?: string };

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

export function Pill({
  children,
  tone = "default",
  className,
}: Div & { tone?: "default" | "dark" | "accent" | "good" | "warn" }) {
  const toneClass = {
    default: "",
    dark: s.pillDark,
    accent: s.pillAccent,
    good: s.pillGood,
    warn: s.pillWarn,
  }[tone];
  return <span className={cx(s.pill, toneClass, className)}>{children}</span>;
}

export function Eyebrow({ children, cyan, className }: Div & { cyan?: boolean }) {
  return <p className={cx(s.eyebrow, cyan && s.eyebrowCyan, className)}>{children}</p>;
}

export function FeatureCard({ children, hover, className }: Div & { hover?: boolean }) {
  return <div className={cx(s.featureCard, hover && s.featureCardHover, className)}>{children}</div>;
}

export function DarkSection({
  children,
  glow = true,
  className,
  ...rest
}: Div & { glow?: boolean } & HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cx(s.darkSection, className)} {...rest}>
      {glow && <div className={s.darkGlow} aria-hidden="true" />}
      {children}
    </div>
  );
}

export function LaunchShell({ children, className }: Div) {
  return (
    <div className={cx(s.launchShell, className)}>
      <div className={s.launchGlow} aria-hidden="true" />
      {children}
    </div>
  );
}

const Chevron = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="m9 18 6-6-6-6" />
  </svg>
);

export function LessonPanel({
  eyebrow,
  title,
  state = "idle",
  onClick,
  disabled,
}: {
  eyebrow?: string;
  title: string;
  state?: "idle" | "active" | "correct" | "wrong";
  onClick?: () => void;
  disabled?: boolean;
}) {
  const stateClass = {
    idle: "",
    active: s.lessonPanelActive,
    correct: s.lessonPanelCorrect,
    wrong: s.lessonPanelWrong,
  }[state];
  return (
    <button
      type="button"
      className={cx(s.lessonPanel, stateClass)}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={state === "active"}
    >
      <span>
        {eyebrow && <span className={s.lessonPanelEyebrow}>{eyebrow}</span>}
        <span className={s.lessonPanelTitle}>{title}</span>
      </span>
      <span className={s.lessonPanelChev}>
        <Chevron />
      </span>
    </button>
  );
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "blue" | "outline" | "white";
};
export function Button({ variant = "blue", className, children, ...rest }: BtnProps) {
  const v = { blue: s.btnBlue, outline: s.btnOutline, white: s.btnWhite }[variant];
  return (
    <button className={cx(s.btn, v, className)} {...rest}>
      {children}
    </button>
  );
}

export function Title({
  children,
  size = "section",
  inverse,
  className,
}: Div & { size?: "hero" | "section"; inverse?: boolean }) {
  return (
    <h1
      className={cx(s.title, size === "hero" ? s.titleHero : s.titleSection, inverse && s.titleInverse, className)}
    >
      {children}
    </h1>
  );
}

export function Lead({ children, inverse, className }: Div & { inverse?: boolean }) {
  return <p className={cx(s.lead, inverse && s.leadInverse, className)}>{children}</p>;
}
