import { useEffect, useRef, useState } from "react";
import { useRuntimeStore } from "./store";
import { play } from "./sfx";
import s from "./TutorWidget.module.css";

// ---------------------------------------------------------------------------
// TutorWidget — the F5 docked, collapsible help channel. Mounted once at the
// V2FlowController level so it PERSISTS across every screen (Hub → CBP →
// Flashcards/Memory → Gate → Practice Arc → Boss → Reflection).
//
// Closed = a floating button bottom-right. Open = a chat panel styled like the
// landing tutor-card-dark aesthetic (student/tutor bubbles, typing indicator).
//
// LEAK SAFETY (architecture §C.5): the widget NEVER displays or requests answer
// content. It only forwards the student's message + a screen-derived `phase`
// (the store maps screen → "preview" | "practice" | "boss"); the server rebuilds
// question context and redacts answers server-side. There is no answer field in
// the widget's state, request, or render.
// ---------------------------------------------------------------------------
export function TutorWidget() {
  const open = useRuntimeStore((st) => st.tutor.open);
  const turns = useRuntimeStore((st) => st.tutor.turns);
  const sending = useRuntimeStore((st) => st.tutor.sending);
  const sendError = useRuntimeStore((st) => st.tutor.sendError);
  const toggle = useRuntimeStore((st) => st.toggleTutor);
  const send = useRuntimeStore((st) => st.sendTutorMessage);

  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  // Guard: skip the very first mount so open=false on load never fires a cue.
  const mountedRef = useRef(false);
  // Guard: track the turn count we last fired "reply landed" for.
  const lastReplyCountRef = useRef(0);

  // Auto-scroll to the newest turn / the typing indicator.
  useEffect(() => {
    if (!open) return;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [open, turns.length, sending]);

  // Fire popup-open / popup-close when the panel toggles. Skip the initial render.
  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      return;
    }
    if (open) {
      play("popup-open");
    } else {
      play("popup-close");
    }
  }, [open]);

  // Focus the composer when the panel opens.
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  // "Reply landed" cue: fires once per tutor turn, when sending flips true→false
  // and the last turn is from the tutor. Fires even when the panel is minimized.
  useEffect(() => {
    if (sending) return;
    const lastTurn = turns[turns.length - 1];
    if (!lastTurn || lastTurn.role !== "tutor") return;
    if (turns.length <= lastReplyCountRef.current) return;
    lastReplyCountRef.current = turns.length;
    play("popup-open");
  }, [sending, turns]);

  const onSend = () => {
    const text = draft.trim();
    if (!text || sending) return;
    setDraft("");
    void send(text, {});
  };

  return (
    <div className={s.root} data-testid="tutor-widget">
      {/* Chat panel — mounted only when open so closed = pure floating button. */}
      {open && (
        <section
          className={s.panel}
          role="dialog"
          aria-label="Tutor chat"
          data-testid="tutor-panel"
        >
          <header className={s.head}>
            <div className={s.headTitle}>
              <span className={s.headDot} aria-hidden="true" />
              <span className={s.headLabel}>
                <span className={s.headName}>Tutor</span>
                <span className={s.headStatus}>Always here to nudge</span>
              </span>
            </div>
            <button
              type="button"
              className={s.headClose}
              onClick={() => { play("tick"); toggle(false); }}
              aria-label="Close tutor"
              data-testid="tutor-close"
            >
              <CloseGlyph />
            </button>
          </header>

          <div className={s.thread} ref={scrollRef} data-testid="tutor-thread">
            {turns.length === 0 && (
              <div className={s.empty}>
                <p className={s.emptyTitle}>Stuck? Ask away.</p>
                <p className={s.emptyBody}>
                  I'll nudge your thinking — I won't hand you the answer.
                </p>
              </div>
            )}
            {turns.map((t) => (
              <div
                key={t.id}
                className={`${s.bubbleRow} ${t.role === "student" ? s.rowStudent : s.rowTutor}`}
              >
                <div
                  className={`${s.bubble} ${t.role === "student" ? s.bubbleStudent : s.bubbleTutor}`}
                >
                  {t.text}
                </div>
              </div>
            ))}
            {sending && (
              <div className={`${s.bubbleRow} ${s.rowTutor}`} data-testid="tutor-typing">
                <div className={`${s.bubble} ${s.bubbleTutor} ${s.typing}`} aria-label="Tutor is typing">
                  <span className={s.typeDot} />
                  <span className={s.typeDot} />
                  <span className={s.typeDot} />
                </div>
              </div>
            )}
          </div>

          {sendError && (
            <p className={s.error} role="alert">
              {sendError}
            </p>
          )}

          <div className={s.composer}>
            <textarea
              ref={inputRef}
              className={s.input}
              value={draft}
              placeholder="Ask the tutor…"
              rows={1}
              disabled={sending}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSend();
                }
              }}
              data-testid="tutor-input"
            />
            <button
              type="button"
              className={s.sendBtn}
              onClick={() => { play("tick"); onSend(); }}
              disabled={sending || draft.trim() === ""}
              aria-label="Send message"
              data-testid="tutor-send"
            >
              <SendGlyph />
            </button>
          </div>
        </section>
      )}

      {/* Floating launcher — always present; toggles the panel. */}
      <button
        type="button"
        className={`${s.launcher} ${open ? s.launcherOpen : ""}`}
        onClick={() => { play("tick"); toggle(); }}
        aria-label={open ? "Minimize tutor" : "Open tutor"}
        aria-expanded={open}
        data-testid="tutor-launcher"
      >
        {open ? <ChevronDownGlyph /> : <ChatGlyph />}
      </button>
    </div>
  );
}

const ChatGlyph = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const ChevronDownGlyph = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="m6 9 6 6 6-6" />
  </svg>
);

const CloseGlyph = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
);

const SendGlyph = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="m22 2-7 20-4-9-9-4Z" />
    <path d="M22 2 11 13" />
  </svg>
);
