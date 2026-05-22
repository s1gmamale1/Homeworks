import { useState, useCallback, useRef } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import { Eyebrow, Title, Lead, Pill, Button, FeatureCard } from "../../shared/ui/primitives";
import { useAnswerTelemetry } from "../hooks/useAnswerTelemetry";
import { play } from "../sfx";
import s from "./MemoryPalace.module.css";

// ---------------------------------------------------------------------------
// Memory Palace — method-of-loci game-break (Practice Arc, F4).
//
// Client-shape comes from __GB_MEMORY_PALACE__ (injector._serialize_memory_palace):
//   { palaces: Palace[], concepts: Concept[], config: Config }
//
// The "answer" is the STUDENT'S OWN placement map, not an author key.
// All three lists (placements + recall_results) ride in ONE stateless POST.
// Server recomputes is_correct from placements → the client never self-grades.
//
// UX arc (4 phases rendered from local `phase` state):
//   "study"   → "place"  → "recall"  → "result"
//   (read)      (encode)   (test)       (outcome card)
//
// Types are defined inline per spec (do NOT edit shared/types.ts).
// ---------------------------------------------------------------------------

// ---- Inline types (do not leak to shared/types.ts) ----

interface MPLocation {
  name: string;
  sensory_cue?: string | null;
  icon?: string | null;
}

interface MPConcept {
  id: string;
  term: string;
  description?: string | null;
  image_cue?: string | null;
}

interface MPPalace {
  key: string;
  name: string;
  icon?: string | null;
  description?: string | null;
  locations: MPLocation[];
}

interface MPConfig {
  concept_count: number;
  min_palace_options: number;
  enable_reverse_recall: boolean;
}

interface MPGameData {
  palaces: MPPalace[];
  concepts: MPConcept[];
  config: MPConfig;
}

// Posted to the server.
interface Placement {
  location_idx: number;
  concept_id: string;
}

// Server response from phase=memory-palace.
interface MPResult {
  outcome: string;           // "perfect" | "yaxshi" | "hali_emas_partial" | "hali_emas_fail"
  outcome_title: string;
  outcome_text: string;
  accuracy_pct: number;
  correct_count: number;
  total_count: number;
  recall_speed_avg_s: number;
  level_label: string;
  session_xp_display: number;
  retry_offered: boolean;
  missed_location_indices: number[];
}

// ---- Game phases ----
type Phase = "study" | "place" | "recall" | "result";

// ---------------------------------------------------------------------------
// Entry guard: validate game data and return the first valid palace.
// ---------------------------------------------------------------------------
function pickPalace(data: MPGameData | null): MPPalace | null {
  if (!data?.palaces?.length) return null;
  return data.palaces[0];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function MemoryPalace({ onComplete }: GameProps) {
  const hwId      = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload   = useRuntimeStore((st) => st.payload);

  // The injector ships `gb_memory_palace` (already redacted).
  const raw = (payload?.content_json as Record<string, unknown> | undefined)
    ?.gb_memory_palace as MPGameData | null | undefined;

  const data    = raw ?? null;
  const palace  = pickPalace(data);
  const concepts = data?.concepts ?? [];

  // Empty guard — graceful skip card.
  if (!palace || concepts.length === 0) {
    return (
      <div className={s.wrap} data-testid="memory-palace-empty">
        <FeatureCard>
          <Eyebrow>Memory Palace</Eyebrow>
          <Title size="section">Nothing to memorize yet.</Title>
          <Lead>This homework doesn't have a Memory Palace exercise. Keep going!</Lead>
          <div className={s.actions}>
            <Button variant="blue" onClick={onComplete} data-testid="mp-skip">
              Continue →
            </Button>
          </div>
        </FeatureCard>
      </div>
    );
  }

  return (
    <PalaceGame
      hwId={hwId}
      sessionId={sessionId}
      palace={palace}
      concepts={concepts}
      onComplete={onComplete}
    />
  );
}

// ---------------------------------------------------------------------------
// PalaceGame — rendered once data is confirmed present.
// ---------------------------------------------------------------------------
function PalaceGame({
  hwId,
  sessionId,
  palace,
  concepts,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  palace: MPPalace;
  concepts: MPConcept[];
  onComplete: () => void;
}) {
  const locations = palace.locations;
  const totalStations = Math.min(locations.length, concepts.length);

  // Slice to the smaller of locations/concepts so every station has a concept.
  const activeLocations = locations.slice(0, totalStations);
  const activeConcepts  = concepts.slice(0, totalStations);

  // ---- Phase state ----
  const [phase, setPhase]                   = useState<Phase>("study");
  const [studyIdx, setStudyIdx]             = useState(0);

  // Phase 2: placement map — locationIdx → conceptId.
  const [placements, setPlacements]         = useState<Placement[]>([]);
  const [placeIdx, setPlaceIdx]             = useState(0);
  const [placePickedConcept, setPickedCon]  = useState<string | null>(null);

  // Shuffled concept list for placement picking — stable for this mount.
  const [shuffledConcepts]                  = useState<MPConcept[]>(() => shuffle(activeConcepts));

  // Phase 3: recall map — locationIdx → pickedConceptId (ordered by location).
  const [recallPicks, setRecallPicks]       = useState<Record<number, string>>({});
  const [recallIdx, setRecallIdx]           = useState(0);
  const [recallPickedConcept, setRecallPick]= useState<string | null>(null);

  // Advisory anti-cheat (tap-only → timing only, no paste). Re-baselines each
  // recall station so per-station elapsed_ms reflects real recall latency, and
  // captures it into a ref-map at each confirm.
  const tele = useAnswerTelemetry(recallIdx);
  const recallElapsedRef = useRef<Record<number, number>>({});

  // Submission state.
  const [submitting, setSubmitting]         = useState(false);
  const [error, setError]                   = useState<string | null>(null);
  const [result, setResult]                 = useState<MPResult | null>(null);

  // ---- Study phase handlers ----
  const onStudyNext = useCallback(() => {
    if (studyIdx + 1 < totalStations) {
      setStudyIdx(studyIdx + 1);
    } else {
      // Enter placement phase.
      setPhase("place");
      setPlaceIdx(0);
      setPickedCon(null);
    }
  }, [studyIdx, totalStations]);

  // ---- Placement phase handlers ----
  const onPlaceConfirm = useCallback(() => {
    if (!placePickedConcept) return;
    const next: Placement[] = [...placements, { location_idx: placeIdx, concept_id: placePickedConcept }];
    setPlacements(next);
    if (placeIdx + 1 < totalStations) {
      setPlaceIdx(placeIdx + 1);
      setPickedCon(null);
    } else {
      // Enter recall phase.
      setPhase("recall");
      setRecallIdx(0);
      setRecallPick(null);
    }
  }, [placePickedConcept, placements, placeIdx, totalStations]);

  // ---- Recall phase handlers ----
  const onRecallConfirm = useCallback(async () => {
    if (!recallPickedConcept) return;
    // Capture this station's recall latency (advisory; tap-only timing).
    recallElapsedRef.current[recallIdx] = tele.read().client_time_ms;
    const updatedPicks = { ...recallPicks, [recallIdx]: recallPickedConcept };
    setRecallPicks(updatedPicks);

    const isLast = recallIdx + 1 >= totalStations;
    if (!isLast) {
      setRecallIdx(recallIdx + 1);
      setRecallPick(null);
      return;
    }

    // All picks collected — build recall_results and POST. elapsed_ms now
    // carries the real per-station recall latency (advisory; was hardcoded 0).
    const recallResults = Array.from({ length: totalStations }, (_, i) => ({
      location_idx: i,
      picked_concept_id: updatedPicks[i] ?? null,
      elapsed_ms: recallElapsedRef.current[i] ?? 0,
    }));

    setSubmitting(true);
    setError(null);
    try {
      const res = await submitGameAnswer<MPResult>(hwId, sessionId, "memory-palace", {
        palace_key: "",  // palace.key may be empty (schema default ""); server uses placements
        placements,
        recall_results: recallResults,
      });
      setResult(res);
      if (res.outcome === "perfect" || res.outcome === "yaxshi") {
        play("complete");
      } else {
        play("wrong");
      }
      setPhase("result");
    } catch (err) {
      setError((err as Error).message || "Couldn't submit your palace. Try again.");
    } finally {
      setSubmitting(false);
    }
  }, [recallPickedConcept, recallPicks, recallIdx, totalStations, hwId, sessionId, placements, tele]);

  // ---- Render by phase ----
  return (
    <div className={s.wrap} data-testid="memory-palace">
      <div className={s.head}>
        <Eyebrow>Memory Palace</Eyebrow>
        <span className={s.badge} data-testid="mp-palace-name">
          {palace.icon ? `${palace.icon} ` : ""}{palace.name}
        </span>
      </div>

      {phase === "study" && (
        <StudyPhase
          location={activeLocations[studyIdx]}
          concept={activeConcepts[studyIdx]}
          stationIdx={studyIdx}
          total={totalStations}
          onNext={onStudyNext}
        />
      )}

      {phase === "place" && (
        <PlacePhase
          location={activeLocations[placeIdx]}
          stationIdx={placeIdx}
          total={totalStations}
          concepts={shuffledConcepts}
          picked={placePickedConcept}
          onPick={setPickedCon}
          onConfirm={onPlaceConfirm}
          placedIds={placements.map((p) => p.concept_id)}
        />
      )}

      {phase === "recall" && (
        <RecallPhase
          location={activeLocations[recallIdx]}
          stationIdx={recallIdx}
          total={totalStations}
          concepts={shuffledConcepts}
          picked={recallPickedConcept}
          onPick={setRecallPick}
          onConfirm={onRecallConfirm}
          submitting={submitting && recallIdx + 1 >= totalStations}
          error={error}
        />
      )}

      {phase === "result" && result && (
        <ResultPhase
          result={result}
          locations={activeLocations}
          concepts={activeConcepts}
          onComplete={onComplete}
          onRetry={() => {
            // Reset to placement phase; study was already done.
            setPlacements([]);
            setPlaceIdx(0);
            setPickedCon(null);
            setRecallPicks({});
            setRecallIdx(0);
            setRecallPick(null);
            setResult(null);
            setError(null);
            setPhase("place");
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase: Study — read each station + its concept in sequence.
// ---------------------------------------------------------------------------
function StudyPhase({
  location,
  concept,
  stationIdx,
  total,
  onNext,
}: {
  location: MPLocation;
  concept: MPConcept;
  stationIdx: number;
  total: number;
  onNext: () => void;
}) {
  const isLast = stationIdx + 1 >= total;
  return (
    <div className={s.phase} data-testid={`mp-study-${stationIdx}`}>
      <div className={s.phaseHeader}>
        <Title size="section">Walk the palace.</Title>
        <Lead className={s.sub}>
          Memorize what's at each station. Picture it vividly.
        </Lead>
      </div>

      <div className={s.progressRow}>
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            className={[s.dot, i < stationIdx && s.dotDone, i === stationIdx && s.dotActive]
              .filter(Boolean)
              .join(" ")}
            aria-hidden="true"
          />
        ))}
        <span className={s.progressLabel}>{stationIdx + 1} / {total}</span>
      </div>

      <div className={s.stationCard} data-testid="mp-station-card">
        <div className={s.locationRow}>
          {location.icon && <span className={s.locationIcon} aria-hidden="true">{location.icon}</span>}
          <div>
            <span className={s.locationLabel}>Station {stationIdx + 1}</span>
            <span className={s.locationName}>{location.name}</span>
          </div>
        </div>
        {location.sensory_cue && (
          <p className={s.sensoryCue} data-testid="mp-sensory-cue">
            {location.sensory_cue}
          </p>
        )}
      </div>

      <div className={s.conceptCard} data-testid="mp-concept-card">
        <span className={s.conceptLabel}>Place here</span>
        <span className={s.conceptTerm}>{concept.term}</span>
        {concept.description && (
          <p className={s.conceptDesc}>{concept.description}</p>
        )}
        {concept.image_cue && (
          <p className={s.imageCue} data-testid="mp-image-cue">
            Imagine: {concept.image_cue}
          </p>
        )}
      </div>

      <div className={s.actions}>
        <Button
          variant="blue"
          onClick={onNext}
          data-testid="mp-study-next"
        >
          {isLast ? "Start placing →" : "Next station →"}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase: Place — the student selects which concept goes at each location.
// ---------------------------------------------------------------------------
function PlacePhase({
  location,
  stationIdx,
  total,
  concepts,
  picked,
  onPick,
  onConfirm,
  placedIds,
}: {
  location: MPLocation;
  stationIdx: number;
  total: number;
  concepts: MPConcept[];
  picked: string | null;
  onPick: (id: string) => void;
  onConfirm: () => void;
  placedIds: string[];  // already placed concept ids (greyed out)
}) {
  return (
    <div className={s.phase} data-testid={`mp-place-${stationIdx}`}>
      <div className={s.phaseHeader}>
        <Title size="section">Build your journey.</Title>
        <Lead className={s.sub}>
          Assign a concept to each station — you chose where it lives.
        </Lead>
      </div>

      <div className={s.progressRow}>
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            className={[s.dot, i < stationIdx && s.dotDone, i === stationIdx && s.dotActive]
              .filter(Boolean)
              .join(" ")}
            aria-hidden="true"
          />
        ))}
        <span className={s.progressLabel}>{stationIdx + 1} / {total}</span>
      </div>

      <div className={s.stationCard}>
        <div className={s.locationRow}>
          {location.icon && <span className={s.locationIcon} aria-hidden="true">{location.icon}</span>}
          <div>
            <span className={s.locationLabel}>Station {stationIdx + 1}</span>
            <span className={s.locationName}>{location.name}</span>
          </div>
        </div>
      </div>

      <p className={s.instruction}>Pick a concept to place here:</p>

      <div className={s.optionGrid} role="group" aria-label="Concepts to place">
        {concepts.map((c) => {
          const isPlaced   = placedIds.includes(c.id) && c.id !== picked;
          const isSelected = picked === c.id;
          return (
            <button
              key={c.id}
              type="button"
              className={[
                s.optionBtn,
                isSelected && s.optionSelected,
                isPlaced   && s.optionUsed,
              ].filter(Boolean).join(" ")}
              disabled={isPlaced}
              onClick={() => { play("tick"); onPick(c.id); }}
              aria-pressed={isSelected}
              data-testid={`mp-place-option-${c.id}`}
            >
              {c.term}
            </button>
          );
        })}
      </div>

      <div className={s.actions}>
        <Button
          variant="blue"
          onClick={onConfirm}
          disabled={!picked}
          data-testid="mp-place-confirm"
        >
          {stationIdx + 1 >= total ? "Start recall test →" : "Place here →"}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase: Recall — for each location, the student picks which concept was there.
// ---------------------------------------------------------------------------
function RecallPhase({
  location,
  stationIdx,
  total,
  concepts,
  picked,
  onPick,
  onConfirm,
  submitting,
  error,
}: {
  location: MPLocation;
  stationIdx: number;
  total: number;
  concepts: MPConcept[];
  picked: string | null;
  onPick: (id: string) => void;
  onConfirm: () => void;
  submitting: boolean;
  error: string | null;
}) {
  const isLast = stationIdx + 1 >= total;
  return (
    <div className={s.phase} data-testid={`mp-recall-${stationIdx}`}>
      <div className={s.phaseHeader}>
        <Title size="section">Test your palace.</Title>
        <Lead className={s.sub}>
          What did you place at this station? Pick from the list.
        </Lead>
      </div>

      <div className={s.progressRow}>
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            className={[s.dot, i < stationIdx && s.dotDone, i === stationIdx && s.dotActive]
              .filter(Boolean)
              .join(" ")}
            aria-hidden="true"
          />
        ))}
        <span className={s.progressLabel}>{stationIdx + 1} / {total}</span>
      </div>

      <div className={s.stationCard}>
        <div className={s.locationRow}>
          {location.icon && <span className={s.locationIcon} aria-hidden="true">{location.icon}</span>}
          <div>
            <span className={s.locationLabel}>Station {stationIdx + 1}</span>
            <span className={s.locationName}>{location.name}</span>
          </div>
        </div>
        {location.sensory_cue && (
          <p className={s.sensoryCue}>{location.sensory_cue}</p>
        )}
      </div>

      <p className={s.instruction}>What did you place here?</p>

      <div className={s.optionGrid} role="group" aria-label="Recall options">
        {concepts.map((c) => {
          const isSelected = picked === c.id;
          return (
            <button
              key={c.id}
              type="button"
              className={[s.optionBtn, isSelected && s.optionSelected]
                .filter(Boolean).join(" ")}
              disabled={submitting}
              onClick={() => { play("tick"); onPick(c.id); }}
              aria-pressed={isSelected}
              data-testid={`mp-recall-option-${c.id}`}
            >
              {c.term}
            </button>
          );
        })}
      </div>

      {error && (
        <p className={s.error} role="alert">{error}</p>
      )}

      <div className={s.actions}>
        <Button
          variant="blue"
          onClick={onConfirm}
          disabled={!picked || submitting}
          data-testid="mp-recall-confirm"
        >
          {submitting ? "Grading…" : isLast ? "Submit recall →" : "Next station →"}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase: Result — the server's outcome card.
// ---------------------------------------------------------------------------
const OUTCOME_TONE: Record<string, "good" | "warn" | "accent" | "default"> = {
  perfect: "good",
  yaxshi: "accent",
  hali_emas_partial: "warn",
  hali_emas_fail: "default",
};

function ResultPhase({
  result,
  locations,
  concepts,
  onComplete,
  onRetry,
}: {
  result: MPResult;
  locations: MPLocation[];
  concepts: MPConcept[];
  onComplete: () => void;
  onRetry: () => void;
}) {
  const tone = OUTCOME_TONE[result.outcome] ?? "default";
  const missedLocations = result.missed_location_indices
    .map((i) => locations[i])
    .filter(Boolean);

  return (
    <div className={s.result} data-testid="mp-result">
      <Pill tone={tone}>{result.level_label}</Pill>
      <Title size="section">{result.outcome_title}</Title>
      <Lead>{result.outcome_text}</Lead>

      <div className={s.statsRow} data-testid="mp-stats">
        <div className={s.stat}>
          <span className={s.statValue} data-testid="mp-accuracy">{result.accuracy_pct}%</span>
          <span className={s.statLabel}>Accuracy</span>
        </div>
        <div className={s.stat}>
          <span className={s.statValue} data-testid="mp-correct">
            {result.correct_count}/{result.total_count}
          </span>
          <span className={s.statLabel}>Recalled</span>
        </div>
        <div className={s.stat}>
          <span className={s.statValue} data-testid="mp-speed">{result.recall_speed_avg_s}s</span>
          <span className={s.statLabel}>Avg. time</span>
        </div>
        <div className={s.stat}>
          <span className={s.statValue} data-testid="mp-xp">+{result.session_xp_display}</span>
          <span className={s.statLabel}>XP</span>
        </div>
      </div>

      {missedLocations.length > 0 && (
        <div className={s.missedBlock} data-testid="mp-missed">
          <p className={s.missedLabel}>Stations to revisit:</p>
          <ul className={s.missedList}>
            {result.missed_location_indices.map((locIdx) => {
              const loc = locations[locIdx];
              const concept = concepts[locIdx];
              return (
                <li key={locIdx} className={s.missedItem}>
                  <span className={s.missedStation}>
                    {loc?.icon ? `${loc.icon} ` : ""}{loc?.name ?? `Station ${locIdx + 1}`}
                  </span>
                  {concept && (
                    <span className={s.missedConcept}>→ {concept.term}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className={s.actions}>
        {result.retry_offered && (
          <Button
            variant="outline"
            onClick={onRetry}
            data-testid="mp-retry"
          >
            Retry palace
          </Button>
        )}
        <Button
          variant="blue"
          onClick={onComplete}
          data-testid="mp-continue"
        >
          Continue →
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Utility: Fisher-Yates shuffle (stable per mount — called in useState init).
// ---------------------------------------------------------------------------
function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
