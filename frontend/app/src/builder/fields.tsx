import type { ReactNode, ChangeEvent } from "react";
import s from "./fields.module.css";

// Small set of controlled form primitives shared by every editor. Keeps the
// editors declarative and the styling consistent with the v2 design tokens.

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className={s.field}>
      <span className={s.label}>
        {label}
        {hint && <span className={s.hint}>{hint}</span>}
      </span>
      {children}
    </label>
  );
}

export function TextInput({
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      className={s.input}
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
    />
  );
}

export function NumberInput({
  value,
  onChange,
  min,
  max,
  step,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <input
      className={s.input}
      type="number"
      value={Number.isFinite(value) ? value : ""}
      min={min}
      max={max}
      step={step}
      onChange={(e: ChangeEvent<HTMLInputElement>) => {
        const n = Number(e.target.value);
        onChange(Number.isFinite(n) ? n : 0);
      }}
    />
  );
}

export function TextArea({
  value,
  onChange,
  placeholder,
  rows = 3,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <textarea
      className={s.textarea}
      value={value}
      rows={rows}
      placeholder={placeholder}
      onChange={(e: ChangeEvent<HTMLTextAreaElement>) => onChange(e.target.value)}
    />
  );
}

export function Select<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <select
      className={s.select}
      value={value}
      onChange={(e: ChangeEvent<HTMLSelectElement>) => onChange(e.target.value as T)}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function EditorCard({
  title,
  children,
  actions,
}: {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className={s.card}>
      <header className={s.cardHead}>
        <h3 className={s.cardTitle}>{title}</h3>
        {actions && <div className={s.cardActions}>{actions}</div>}
      </header>
      <div className={s.cardBody}>{children}</div>
    </section>
  );
}

export function SmallButton({
  children,
  onClick,
  tone = "default",
  disabled,
}: {
  children: ReactNode;
  onClick: () => void;
  tone?: "default" | "danger" | "primary";
  disabled?: boolean;
}) {
  const toneClass =
    tone === "danger" ? s.btnDanger : tone === "primary" ? s.btnPrimary : "";
  return (
    <button
      type="button"
      className={`${s.smallBtn} ${toneClass}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

// An option-row group with a "correct" radio. The whole answer_spec contract:
// tapping the radio sets the correct option index. The caller maps that index
// into {type:"option_index", expected:<idx>, option_count:<n>}.
export function OptionEditor({
  options,
  correctIndex,
  onOptionChange,
  onCorrectChange,
  onAddOption,
  onRemoveOption,
  fixedOptions,
}: {
  options: string[];
  correctIndex: number;
  onOptionChange: (i: number, v: string) => void;
  onCorrectChange: (i: number) => void;
  onAddOption?: () => void;
  onRemoveOption?: (i: number) => void;
  fixedOptions?: boolean;
}) {
  return (
    <div className={s.optionGroup}>
      <span className={s.label}>
        Options
        <span className={s.hint}>Tap the circle to mark the correct answer</span>
      </span>
      {options.map((opt, i) => (
        <div key={i} className={s.optionRow}>
          <button
            type="button"
            className={`${s.correctRadio} ${i === correctIndex ? s.correctRadioOn : ""}`}
            aria-label={`Mark option ${i + 1} correct`}
            aria-pressed={i === correctIndex}
            onClick={() => onCorrectChange(i)}
          >
            {i === correctIndex ? "✓" : ""}
          </button>
          <input
            className={s.input}
            value={opt}
            placeholder={`Option ${String.fromCharCode(65 + i)}`}
            disabled={fixedOptions}
            onChange={(e) => onOptionChange(i, e.target.value)}
          />
          {!fixedOptions && onRemoveOption && options.length > 2 && (
            <SmallButton tone="danger" onClick={() => onRemoveOption(i)}>
              ✕
            </SmallButton>
          )}
        </div>
      ))}
      {!fixedOptions && onAddOption && (
        <SmallButton onClick={onAddOption}>+ Add option</SmallButton>
      )}
    </div>
  );
}
