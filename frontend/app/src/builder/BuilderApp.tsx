import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { CbpEditor } from "./CbpEditor";
import { MemoryCheckEditor } from "./MemoryCheckEditor";
import { BossEditor } from "./BossEditor";
import { MetadataEditor } from "./MetadataEditor";
import { ReflectionEditor } from "./ReflectionEditor";
import { ExtraMaterialsEditor } from "./ExtraMaterialsEditor";
import { PracticeArcSection } from "./PracticeArcSection";
import { BuilderPreview } from "./BuilderPreview";
import type { PreviewSurface } from "./BuilderPreview";
import { emptyDraft, fromContentJson, toContentJson } from "./draft";
import { getHomework, putHomework, getReadiness } from "./builderApi";
import type { Readiness } from "./builderApi";
import type { BuilderDraft } from "./types";
import s from "./BuilderApp.module.css";

type Section =
  | "meta"
  | "cbp"
  | "memory"
  | "practice"
  | "boss"
  | "extra_materials"
  | "reflection";
type SaveStatus = "idle" | "saving" | "saved" | "error";

// Each editor section maps to the preview surface it opens on. Practice opens
// on Tile Match (the canonical first arc game); the author flips the preview
// surface freely via the preview tabs.
const SECTION_TO_SURFACE: Record<Section, PreviewSurface> = {
  meta: "cbp",
  cbp: "cbp",
  memory: "memory",
  practice: "tile_match",
  boss: "boss",
  extra_materials: "extra_materials",
  reflection: "reflection",
};

// 24x24 line icons (strokeWidth 1.8, currentColor) — the no-emoji equivalent of
// the legacy builder's phase glyphs. Each echoes the old phase-icon vibe:
// clipboard (preview), brain (memory), gamepad (practice arc), shield (boss),
// speech bubble (reflection), sliders (metadata).
function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      className={s.navIcon}
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

const SECTION_ICONS: Record<Section, ReactNode> = {
  // Sliders — settings/metadata
  meta: (
    <Icon>
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="18" x2="20" y2="18" />
      <circle cx="9" cy="6" r="2" />
      <circle cx="15" cy="12" r="2" />
      <circle cx="8" cy="18" r="2" />
    </Icon>
  ),
  // Clipboard — case preview
  cbp: (
    <Icon>
      <rect x="6" y="4" width="12" height="17" rx="2" />
      <path d="M9 4h6v3H9z" />
      <line x1="9" y1="11" x2="15" y2="11" />
      <line x1="9" y1="15" x2="13" y2="15" />
    </Icon>
  ),
  // Brain — memory check
  memory: (
    <Icon>
      <path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 3 3V4z" />
      <path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-3 3V4z" />
    </Icon>
  ),
  // Gamepad — practice arc
  practice: (
    <Icon>
      <rect x="3" y="8" width="18" height="9" rx="4" />
      <line x1="7.5" y1="11" x2="7.5" y2="14" />
      <line x1="6" y1="12.5" x2="9" y2="12.5" />
      <circle cx="16" cy="12" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="18" cy="14" r="0.9" fill="currentColor" stroke="none" />
    </Icon>
  ),
  // Shield — boss
  boss: (
    <Icon>
      <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" />
      <path d="M9.5 12l1.8 1.8L15 10" />
    </Icon>
  ),
  // Speech bubble — reflection
  reflection: (
    <Icon>
      <path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-4 3v-3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z" />
      <line x1="8" y1="10" x2="16" y2="10" />
      <line x1="8" y1="13" x2="13" y2="13" />
    </Icon>
  ),
  // External link — extra materials
  extra_materials: (
    <Icon>
      <path d="M14 4h6v6" />
      <path d="M20 4l-8.5 8.5" />
      <path d="M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6" />
    </Icon>
  ),
};

const SECTIONS: { id: Section; label: string }[] = [
  { id: "meta", label: "Metadata" },
  { id: "cbp", label: "Case Preview" },
  { id: "memory", label: "Memory Check" },
  { id: "practice", label: "Practice Arc" },
  { id: "boss", label: "Boss" },
  { id: "extra_materials", label: "Extra Materials" },
  { id: "reflection", label: "Reflection" },
];

const PREVIEW_TABS: { id: PreviewSurface; label: string }[] = [
  { id: "cbp", label: "Case" },
  { id: "flashcards", label: "Flashcards" },
  { id: "memory", label: "Memory Check" },
  { id: "tile_match", label: "Tile Match" },
  { id: "sentence_fill", label: "Sentence Fill" },
  { id: "mystery_box", label: "Mystery Box" },
  { id: "puzzle_lock", label: "Puzzle Lock" },
  { id: "adaptive_quiz", label: "Adaptive Quiz" },
  { id: "memory_palace", label: "Memory Palace" },
  { id: "ttt", label: "Tic-Tac-Toe" },
  { id: "real_life_challenge", label: "Real-Life" },
  { id: "listening", label: "Listening" },
  { id: "extra_materials", label: "Extra Materials" },
  { id: "boss", label: "Boss" },
  { id: "reflection", label: "Reflection" },
];

const SAVE_DEBOUNCE_MS = 1200;

// F6 Builder shell. The legacy dashboard navigates here via /app/builder?id=<hwId>,
// so the builder ALWAYS edits exactly one homework: it reads `id` from the URL on
// mount, loads it, and (with no `id`) bounces back to the legacy dashboard at "/".
// There is no in-app React dashboard anymore. Layout echoes the legacy builder.html:
// a left glass sidebar listing the phases vertically (icon + label, active row), a
// slim top bar, and the editor + LIVE preview to the right.
export function BuilderApp() {
  const [hwId, setHwId] = useState<string | null>(null);
  const [draft, setDraft] = useState<BuilderDraft | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [section, setSection] = useState<Section>("cbp");
  const [surface, setSurface] = useState<PreviewSurface>("cbp");
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dirtyRef = useRef(false);

  // Strict (delivery-grade) readiness — the autosave is lenient so authors can
  // save half-finished questions, but a homework still must be COMPLETE before
  // it's worth sharing. Refresh after load + every successful save; never throws.
  const refreshReadiness = useCallback((id: string) => {
    getReadiness(id)
      .then(setReadiness)
      .catch(() => setReadiness(null));
  }, []);

  // Load the unredacted authoring blob when a homework is opened.
  const openHomework = useCallback(async (id: string, seed?: BuilderDraft) => {
    setHwId(id);
    setLoadError(null);
    if (seed) {
      setDraft(seed);
      return;
    }
    try {
      const row = await getHomework(id);
      setDraft(fromContentJson(row.content_json ?? {}));
      refreshReadiness(id);
    } catch (err) {
      setLoadError((err as Error).message || "Couldn't load this homework.");
      setDraft(emptyDraft());
    }
  }, [refreshReadiness]);

  // Entry: the legacy dashboard sends us /app/builder?id=<hwId>. Read it once on
  // mount → load that homework. No `id` means the builder was reached without a
  // target, so return to the legacy dashboard rather than render an empty shell.
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    if (id) {
      void openHomework(id);
    } else {
      window.location.href = "/index.html";
    }
  }, [openHomework]);

  // Debounced autosave. Each draft change schedules a single PUT.
  const scheduleSave = useCallback(
    (id: string, next: BuilderDraft) => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      dirtyRef.current = true;
      setSaveStatus("saving");
      saveTimer.current = setTimeout(async () => {
        try {
          await putHomework(id, { content_json: toContentJson(next) });
          dirtyRef.current = false;
          setSaveStatus("saved");
          setSaveError(null);
          refreshReadiness(id);
        } catch (err) {
          setSaveStatus("error");
          setSaveError((err as Error).message || "Save failed.");
        }
      }, SAVE_DEBOUNCE_MS);
    },
    [refreshReadiness]
  );

  useEffect(() => {
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
  }, []);

  const updateDraft = useCallback(
    (next: BuilderDraft) => {
      setDraft(next);
      if (hwId) scheduleSave(hwId, next);
    },
    [hwId, scheduleSave]
  );

  // Keep the preview surface in sync when the editor section changes.
  const selectSection = (next: Section) => {
    setSection(next);
    setSurface(SECTION_TO_SURFACE[next]);
  };

  // Minimal loading frame while the homework hydrates (or while the no-id
  // redirect to "/" is in flight). The redirect is fire-and-forget, so this is
  // the only thing we render until the draft lands.
  if (!hwId || !draft) {
    return (
      <div className={s.loading} data-testid="builder-loading" role="status">
        <span className={s.spinner} aria-hidden="true" />
        <p className={s.loadingText}>Loading homework…</p>
      </div>
    );
  }

  return (
    <div className={s.builder} data-testid="builder-app">
      <aside className={s.sidebar} aria-label="Homework phases">
        <div className={s.sidebarHeader}>
          <a className={s.backLink} href="/index.html" aria-label="Back to dashboard">
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>Dashboard</span>
          </a>
          <p className={s.eyebrow}>NETS Builder · v2</p>
          <span className={s.hwId}>{hwId}</span>
        </div>

        <nav className={s.phaseList} aria-label="Editor sections">
          {SECTIONS.map((sec) => (
            <button
              key={sec.id}
              type="button"
              className={`${s.phaseItem} ${section === sec.id ? s.phaseActive : ""}`}
              aria-current={section === sec.id ? "true" : undefined}
              onClick={() => selectSection(sec.id)}
            >
              <span className={s.phaseIcon}>{SECTION_ICONS[sec.id]}</span>
              <span className={s.phaseLabel}>{sec.label}</span>
            </button>
          ))}
        </nav>

        <div className={s.sidebarFooter} data-status={saveStatus}>
          <span className={s.saveDot} aria-hidden="true" />
          <span className={s.saveText}>
            {saveStatus === "saving" && "Saving…"}
            {saveStatus === "saved" && "Saved"}
            {saveStatus === "error" && (
              <span className={s.saveErr} title={saveError ?? ""}>
                Save failed
              </span>
            )}
            {saveStatus === "idle" && "All changes saved"}
          </span>
        </div>

        {readiness && (
          <div
            className={s.readiness}
            data-ready={readiness.ready ? "true" : "false"}
            data-testid="builder-readiness"
          >
            {readiness.ready ? (
              <span className={s.readyOk}>✓ Ready to share</span>
            ) : (
              <span
                className={s.readyWarn}
                title={readiness.issues
                  .map((i) => `• ${i.msg.replace(/^Value error,\s*/, "")}`)
                  .join("\n")}
              >
                {readiness.issues.length} thing
                {readiness.issues.length === 1 ? "" : "s"} to finish before
                sharing
              </span>
            )}
          </div>
        )}
      </aside>

      <section className={s.main} aria-label="Homework builder workspace">
        {loadError && (
          <p className={s.loadErr} role="alert">
            {loadError}
          </p>
        )}

        <div className={s.panes}>
          <div className={s.editorPane}>
            {section === "meta" && (
              <MetadataEditor
                value={draft.meta}
                onChange={(meta) => updateDraft({ ...draft, meta })}
              />
            )}
            {section === "cbp" && (
              <CbpEditor
                value={draft.case_based_preview}
                onChange={(case_based_preview) =>
                  updateDraft({ ...draft, case_based_preview })
                }
              />
            )}
            {section === "memory" && (
              <MemoryCheckEditor
                flashcards={draft.flashcards}
                memoryCheck={draft.memory_check}
                onFlashcardsChange={(flashcards) =>
                  updateDraft({ ...draft, flashcards })
                }
                onMemoryCheckChange={(memory_check) =>
                  updateDraft({ ...draft, memory_check })
                }
              />
            )}
            {section === "practice" && (
              <PracticeArcSection draft={draft} updateDraft={updateDraft} />
            )}
            {section === "boss" && (
              <BossEditor
                bossMeta={draft.boss_meta}
                bossQuestions={draft.boss_questions}
                onBossMetaChange={(boss_meta) =>
                  updateDraft({ ...draft, boss_meta })
                }
                onBossQuestionsChange={(boss_questions) =>
                  updateDraft({ ...draft, boss_questions })
                }
              />
            )}
            {section === "extra_materials" && (
              <ExtraMaterialsEditor
                value={draft.extra_materials}
                hwId={hwId}
                onChange={(extra_materials) =>
                  updateDraft({ ...draft, extra_materials })
                }
              />
            )}
            {section === "reflection" && (
              <ReflectionEditor
                value={draft.reflection}
                onChange={(reflection) => updateDraft({ ...draft, reflection })}
              />
            )}
          </div>

          <div className={s.previewPane}>
            <div className={s.previewTabs} aria-label="Preview surface">
              {PREVIEW_TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`${s.previewTab} ${surface === t.id ? s.previewTabActive : ""}`}
                  onClick={() => setSurface(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <BuilderPreview draft={draft} surface={surface} />
          </div>
        </div>
      </section>
    </div>
  );
}
