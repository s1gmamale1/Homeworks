import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useRuntimeStore } from "./store";
import { Eyebrow, Title, Lead, Button } from "../shared/ui/primitives";
import type { Flashcard, MemoryCheckItem } from "../shared/types";
import s from "./Flashcards.module.css";

function cardRef(card: Flashcard | undefined, index: number): string {
  const authored = card?.id?.trim();
  if (authored) return authored;
  return `fc_${index + 1}`;
}

// Tile B, study half: a flippable deck (front ↔ back) with "Bildim/Bilmadim"
// recall buttons. The student must view every card ≥1× before "Start Memory
// Check" enables — "viewed" = the card index lands in fc.viewedCards (recorded
// on first flip OR after a 600ms dwell, whichever comes first). Mirrors the
// CaseBasedPreview sub-machine style.
export function Flashcards() {
  const payload = useRuntimeStore((st) => st.payload);
  const cardIndex = useRuntimeStore((st) => st.fc.cardIndex);
  const viewedCards = useRuntimeStore((st) => st.fc.viewedCards);
  const weakItems = useRuntimeStore((st) => st.fc.weakItems);
  const setCardIndex = useRuntimeStore((st) => st.setCardIndex);
  const markViewed = useRuntimeStore((st) => st.markViewed);
  const startMemoryCheck = useRuntimeStore((st) => st.startMemoryCheck);
  const goto = useRuntimeStore((st) => st.goto);

  const cards = (payload?.content_json.flashcards ?? []) as Flashcard[];
  const memoryItems = (payload?.content_json.memory_check?.items ?? []) as MemoryCheckItem[];
  const total = cards.length;
  const card = cards[cardIndex] as Flashcard | undefined;

  const [flipped, setFlipped] = useState(false);

  // Reset the flip when we move to a different card.
  useEffect(() => setFlipped(false), [cardIndex]);

  // A card counts as "viewed" after a brief dwell even without a flip, so a
  // student who reads the front and moves on isn't blocked. Flipping marks it
  // immediately (handled in onFlip).
  useEffect(() => {
    if (total === 0) return;
    const t = setTimeout(() => markViewed(cardIndex), 600);
    return () => clearTimeout(t);
  }, [cardIndex, total, markViewed]);

  if (total === 0) {
    return (
      <Shell testid="fc-flashcards">
        <BackToHub onClick={() => goto("hub")} />
        <Eyebrow>Flashcards</Eyebrow>
        <Title size="hero">No cards in this deck.</Title>
        <Lead className={s.empty}>
          This homework didn’t ship a flashcard deck. You can still take the
          Memory Check.
        </Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={startMemoryCheck} data-testid="fc-start-mc">
            Start Memory Check →
          </Button>
        </div>
      </Shell>
    );
  }

  const allViewed = viewedCards.length >= total;
  const isRetry = weakItems.length > 0;
  const weakCardRefs = new Set(
    weakItems
      .map((i) => memoryItems[i]?.flashcard_ref)
      .filter((ref): ref is string => !!ref)
  );
  const weakCardIndices = new Set(
    weakItems
      .map((i) => {
        const ref = memoryItems[i]?.flashcard_ref;
        if (ref) {
          const match = cards.findIndex((c, idx) => cardRef(c, idx) === ref);
          if (match >= 0) return match;
        }
        return i < total ? i : -1;
      })
      .filter((i) => i >= 0)
  );
  const currentWeak =
    weakCardIndices.has(cardIndex) || weakCardRefs.has(cardRef(card, cardIndex));

  const onFlip = () => {
    setFlipped((f) => !f);
    markViewed(cardIndex);
  };

  const go = (delta: number) => {
    const next = cardIndex + delta;
    if (next >= 0 && next < total) setCardIndex(next);
  };

  return (
    <Shell testid="fc-flashcards">
      <BackToHub onClick={() => goto("hub")} />

      {isRetry && (
        <div className={s.weakBanner} role="status">
          <span aria-hidden="true">↺</span>
          Review the deck, then re-take the {weakItems.length} item
          {weakItems.length === 1 ? "" : "s"} you missed.
        </div>
      )}

      <div className={s.head}>
        <Eyebrow>{isRetry ? "Review deck" : "Flashcards"}</Eyebrow>
        <span className={s.counter}>
          {cardIndex + 1} / {total} · {viewedCards.length} viewed
        </span>
      </div>

      <Progress
        current={cardIndex}
        viewed={viewedCards}
        weak={weakCardIndices}
        total={total}
      />

      <div className={s.cardScene}>
        <button
          type="button"
          className={`${s.card} ${flipped ? s.cardFlipped : ""} ${
            currentWeak ? s.cardWeak : ""
          }`}
          onClick={onFlip}
          aria-label={flipped ? "Show front of card" : "Show back of card"}
          aria-pressed={flipped}
          data-testid="fc-card"
        >
          <span className={`${s.face} ${s.faceFront}`} aria-hidden={flipped}>
            <span className={s.faceLabel}>Front</span>
            {currentWeak && <span className={s.weakChip}>Weak — review</span>}
            <p className={s.faceText}>{card?.front ?? card?.term}</p>
            {card?.hint && <span className={s.faceHint}>Hint: {card.hint}</span>}
            <span className={s.flipHint}>Tap to flip →</span>
          </span>
          <span className={`${s.face} ${s.faceBack}`} aria-hidden={!flipped}>
            <span className={s.faceLabel}>Back</span>
            <p className={s.faceText}>{card?.back ?? card?.def ?? card?.definition}</p>
            {card?.example && <p className={s.faceDetail}>{card.example}</p>}
            <span className={s.flipHint}>Tap to flip back</span>
          </span>
        </button>
      </div>

      {/* Bildim / Bilmadim — self-assessment, advances to the next card. */}
      <div className={s.recall}>
        <button
          type="button"
          className={`${s.recallBtn} ${s.recallKnew}`}
          onClick={() => {
            markViewed(cardIndex);
            go(1);
          }}
          disabled={cardIndex + 1 >= total}
          data-testid="fc-knew"
        >
          ✓ Bildim
        </button>
        <button
          type="button"
          className={`${s.recallBtn} ${s.recallDidnt}`}
          onClick={() => {
            markViewed(cardIndex);
            setFlipped(true);
          }}
          data-testid="fc-didnt"
        >
          ↺ Bilmadim
        </button>
      </div>

      <div className={s.nav}>
        <button
          type="button"
          className={s.navBtn}
          onClick={() => go(-1)}
          disabled={cardIndex === 0}
        >
          ← Prev
        </button>
        <button
          type="button"
          className={s.navBtn}
          onClick={() => go(1)}
          disabled={cardIndex + 1 >= total}
        >
          Next →
        </button>
      </div>

      <div className={s.actions}>
        <Button
          variant="blue"
          onClick={startMemoryCheck}
          disabled={!allViewed}
          aria-disabled={!allViewed}
          data-testid="fc-start-mc"
        >
          Start Memory Check →
        </Button>
      </div>
      {!allViewed && (
        <p className={s.viewHint}>
          View all {total} cards to unlock the Memory Check ({total - viewedCards.length} to go).
        </p>
      )}
    </Shell>
  );
}

function Shell({ children, testid }: { children: ReactNode; testid: string }) {
  return (
    <main className="v2-shell" data-testid={testid}>
      <div className={s.stage} key={testid}>
        {children}
      </div>
    </main>
  );
}

function BackToHub({ onClick }: { onClick: () => void }) {
  return (
    <button className={s.back} onClick={onClick} type="button">
      ← Back to Hub
    </button>
  );
}

function Progress({
  current,
  viewed,
  weak,
  total,
}: {
  current: number;
  viewed: number[];
  weak?: Set<number>;
  total: number;
}) {
  return (
    <div className={s.progress} aria-label={`Card ${current + 1} of ${total}`}>
      {Array.from({ length: total }).map((_, i) => {
        const cls =
          i === current
            ? s.dotActive
            : weak?.has(i)
            ? s.dotWeak
            : viewed.includes(i)
            ? s.dotDone
            : "";
        return <span key={i} className={`${s.dot} ${cls}`} aria-hidden="true" />;
      })}
    </div>
  );
}
