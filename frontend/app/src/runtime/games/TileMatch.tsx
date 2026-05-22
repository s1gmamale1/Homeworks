import { useEffect, useState } from "react";
import { useRuntimeStore } from "../store";
import { submitTileMatch } from "../../shared/api";
import type { GameProps } from "../GameHost";
import type { TileMatchPayload } from "../../shared/types";
import { Eyebrow, Title, Lead, Pill, Button } from "../../shared/ui/primitives";
import { play } from "../sfx";
import s from "./TileMatch.module.css";

// ---------------------------------------------------------------------------
// Tile Match — the F4 reference game (proves the GameHost registry).
//
// `gb_tile_match` now arrives as TWO independently-shuffled token columns:
// `{ lefts: [{lid, text}], rights: [{rid, text}] }`. The `lid`/`rid` are opaque
// per-side HMAC tokens — there is NO shared id, so the DOM can't reveal which
// left matches which right (the old `[{id,left,right}]` shape leaked exactly
// that). The student taps a left tile, then a right tile; we submit the two
// tokens to the server, which inverts them to pair indices and grades by
// `left_index === right_index`. Correctness is ALWAYS the server's call; the
// client never compares strings. Complete when the server reports all pairs
// matched. On a wrong match the server returns a `hint` (the left text of the
// picked right tile's TRUE partner — already on screen, so not a new leak).
//
// Both columns are already shuffled server-side (stable per hw_id), so the
// client renders them in delivery order — no client-side reshuffle needed.
// ---------------------------------------------------------------------------

const EMPTY_PAYLOAD: TileMatchPayload = { lefts: [], rights: [] };

export default function TileMatch({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const tm = (payload?.content_json.gb_tile_match ?? EMPTY_PAYLOAD) as TileMatchPayload;
  const lefts = tm.lefts ?? [];
  const rights = tm.rights ?? [];
  const totalPairs = lefts.length;

  // Selection + match state keyed by the OPAQUE per-side tokens. `matchedLeft`
  // / `matchedRight` track which tokens are locked so both columns gray out the
  // resolved tiles (we don't know the pairing client-side, so they're tracked
  // independently — a correct submit locks the picked lid + rid together).
  const [selectedLid, setSelectedLid] = useState<string | null>(null);
  const [matchedLefts, setMatchedLefts] = useState<Set<string>>(new Set());
  const [matchedRights, setMatchedRights] = useState<Set<string>>(new Set());
  const [wrongFlash, setWrongFlash] = useState<string | null>(null); // rid
  const [hint, setHint] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [complete, setComplete] = useState(false);

  // Clear the wrong-flash highlight after a beat.
  useEffect(() => {
    if (!wrongFlash) return;
    const t = setTimeout(() => setWrongFlash(null), 520);
    return () => clearTimeout(t);
  }, [wrongFlash]);

  if (totalPairs === 0) {
    return (
      <div className={s.wrap} data-testid="tile-match-empty">
        <Lead>No tile-match pairs on this homework.</Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete}>
            Skip →
          </Button>
        </div>
      </div>
    );
  }

  const onPickLeft = (lid: string) => {
    if (submitting || complete || matchedLefts.has(lid)) return;
    setHint(null);
    setSelectedLid((cur) => (cur === lid ? null : lid));
  };

  const onPickRight = async (rid: string) => {
    if (submitting || complete || selectedLid === null) return;
    if (matchedRights.has(rid)) return;

    setSubmitting(true);
    setError(null);
    try {
      // The server inverts the opaque tokens to pair indices and grades by
      // index equality. We send the two tapped tokens; the verdict comes back.
      const res = await submitTileMatch(hwId, sessionId, selectedLid, rid);

      // Sync the local matched-set from the server's authoritative
      // `matched_tokens` on EVERY response (correct / wrong / already-matched
      // replay). The server's _TM_ATTEMPTS dict survives across navigation
      // while the React component remounts with empty matched-set —
      // without this sync, a returning student sees "0/N matched" and every
      // click on a previously-matched pair flashes wrong with no recovery.
      // Echoing the full token set on every response re-bases the UI to
      // ground truth in one round-trip.
      if (Array.isArray(res.matched_tokens)) {
        setMatchedLefts(new Set(res.matched_tokens.map((t) => t.lid)));
        setMatchedRights(new Set(res.matched_tokens.map((t) => t.rid)));
      }

      if (res.correct) {
        play("correct");
        setSelectedLid(null);
        setHint(null);
        // Server is authoritative on completion (matched_count vs total_pairs).
        // The matched_tokens sync above (lines 98-101) already re-based the
        // local matched-set from `res.matched_tokens`, so no manual add needed.
        if (res.complete) {
          play("complete");
          setComplete(true);
        }
      } else if (res.already_matched || res.complete) {
        // Replay against a pair the server already considers matched (typical
        // after navigating away from a completed Tile Match and coming back).
        // Treat as no-op — the matched_tokens sync above already re-based the
        // UI to ground truth. Don't flash wrong, don't show a misleading hint.
        setSelectedLid(null);
        setHint(null);
        if (res.complete) {
          setComplete(true);
        }
      } else {
        play("wrong");
        setWrongFlash(rid);
        setHint(res.hint ?? null);
        setSelectedLid(null);
      }
    } catch (err) {
      setError((err as Error).message || "Couldn’t check that match.");
    } finally {
      setSubmitting(false);
    }
  };

  const matchedCount = matchedLefts.size;

  return (
    <div className={s.wrap} data-testid="tile-match">
      <div className={s.ambient} aria-hidden="true" />
      <div className={s.head}>
        <Eyebrow>Tile Match</Eyebrow>
        <span className={s.counter} data-testid="tile-match-progress">
          {matchedCount}/{totalPairs} matched
        </span>
      </div>

      {!complete ? (
        <>
          <Title size="section">Match each concept to its meaning.</Title>
          <Lead className={s.sub}>Tap a card on the left, then its match on the right.</Lead>

          <div className={s.board}>
            <div className={s.column} role="group" aria-label="Concepts">
              {lefts.map((t) => {
                const isMatched = matchedLefts.has(t.lid);
                const isSel = selectedLid === t.lid;
                return (
                  <button
                    key={`l-${t.lid}`}
                    type="button"
                    className={[
                      s.tile,
                      s.tileLeft,
                      isMatched && s.tileMatched,
                      isSel && s.tileSelected,
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    disabled={isMatched || submitting || complete}
                    onClick={() => { play("tick"); onPickLeft(t.lid); }}
                    aria-pressed={isSel}
                    data-testid={`tm-left-${t.lid}`}
                  >
                    {t.text}
                  </button>
                );
              })}
            </div>

            <div className={s.column} role="group" aria-label="Meanings">
              {rights.map((t) => {
                const isMatched = matchedRights.has(t.rid);
                const isWrong = wrongFlash === t.rid;
                return (
                  <button
                    key={`r-${t.rid}`}
                    type="button"
                    className={[
                      s.tile,
                      s.tileRight,
                      isMatched && s.tileMatched,
                      isWrong && s.tileWrong,
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    disabled={isMatched || submitting || complete || selectedLid === null}
                    onClick={() => { play("tick"); onPickRight(t.rid); }}
                    data-testid={`tm-right-${t.rid}`}
                  >
                    {t.text}
                  </button>
                );
              })}
            </div>
          </div>

          {hint && (
            <div className={s.hint} role="status">
              <Pill tone="warn">Not a match</Pill>
              <span className={s.hintText}>That one pairs with “{hint}”. Try again.</span>
            </div>
          )}
          {error && (
            <p className={s.error} role="alert">
              {error}
            </p>
          )}
        </>
      ) : (
        <div className={s.done} data-testid="tile-match-complete">
          <Pill tone="good">✓ All matched</Pill>
          <Title size="section">Every pair locked in.</Title>
          <Lead>You matched all {totalPairs} pairs. On to the next.</Lead>
          <div className={s.actions}>
            <Button variant="blue" onClick={onComplete} data-testid="tm-continue">
              Continue →
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
