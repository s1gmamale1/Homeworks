import { useCallback, useState } from "react";
import type { ListeningEditorProps, DraftListeningCheckpoint } from "./types";
import { EditorCard, Field, TextInput, TextArea, Select, SmallButton } from "./fields";
import { uploadFile } from "./builderApi";

type AudioSource = "url" | "file";

const AUDIO_SOURCE_OPTIONS: { value: AudioSource; label: string }[] = [
  { value: "url", label: "URL" },
  { value: "file", label: "Upload file (.mp3)" },
];

// ---------------------------------------------------------------------------
// Listening editor (GRADED) — owns content_json.listening (DraftListening).
//
// Two cards:
//   1. Audio & transcript — the audio URL (URL only; upload deferred) plus the
//      transcript. The runtime keeps the transcript hidden until the student
//      has played the audio (the "one rule").
//   2. Checkpoints — reading-style comprehension questions ({prompt, ans, fb}),
//      graded locally and counted toward the AMR score.
//
// server/schemas/content.py ListeningPhase: title, audio_url, transcript,
//   checkpoints[] (ReadingCheckpoint shape: q/prompt, ans, fb).
// ---------------------------------------------------------------------------

const wrap: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 16,
};

function emptyCheckpoint(): DraftListeningCheckpoint {
  return { prompt: "", ans: "", fb: "" };
}

export function ListeningEditor({ value, onChange }: ListeningEditorProps) {
  const patch = useCallback(
    (partial: Partial<typeof value>) => onChange({ ...value, ...partial }),
    [value, onChange]
  );

  const checkpoints = value.checkpoints ?? [];

  // Live audio preview — play a real http(s) URL OR an uploaded /media file.
  const audioPreview = (value.audio_url ?? "").trim();
  const isPlayableAudio = /^https?:\/\//i.test(audioPreview) || audioPreview.startsWith("/media/");

  // Audio source toggle. Default to "file" when the current URL is an upload.
  const [audioSource, setAudioSource] = useState<AudioSource>(
    audioPreview.startsWith("/media/") ? "file" : "url"
  );
  const [uploading, setUploading] = useState(false);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const [audioLoadErr, setAudioLoadErr] = useState(false);

  const handleAudioFile = async (file: File | null) => {
    if (!file) return;
    // Listening audio is .mp3 only.
    if (!/\.mp3$/i.test(file.name)) {
      setUploadErr("Only .mp3 files are allowed.");
      return;
    }
    setUploading(true);
    setUploadErr(null);
    try {
      const res = await uploadFile(file);
      patch({ audio_url: res.url });
    } catch (e) {
      setUploadErr((e as Error).message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const addCheckpoint = useCallback(() => {
    patch({ checkpoints: [...checkpoints, emptyCheckpoint()] });
  }, [patch, checkpoints]);

  const removeCheckpoint = useCallback(
    (idx: number) => {
      patch({ checkpoints: checkpoints.filter((_, i) => i !== idx) });
    },
    [patch, checkpoints]
  );

  const updateCheckpoint = useCallback(
    (idx: number, partial: Partial<DraftListeningCheckpoint>) => {
      patch({
        checkpoints: checkpoints.map((cp, i) =>
          i === idx ? { ...cp, ...partial } : cp
        ),
      });
    },
    [patch, checkpoints]
  );

  return (
    <div style={wrap}>
      {/* ---- Card 1: Audio & transcript ---- */}
      <EditorCard title="Audio & transcript">
        <p style={{ color: "var(--muted, #888)", fontSize: 13, margin: "0 0 8px" }}>
          Graded listening. Paste an audio URL or upload an .mp3. The transcript
          stays hidden until the student plays the audio.
        </p>

        <Field label="Title" hint="Shown as the phase heading (optional)">
          <TextInput
            value={value.title ?? ""}
            onChange={(v) => patch({ title: v || undefined })}
            placeholder="e.g. Weather forecast"
          />
        </Field>

        <Field label="Audio source">
          <Select<AudioSource>
            value={audioSource}
            onChange={(v) => setAudioSource(v)}
            options={AUDIO_SOURCE_OPTIONS}
          />
        </Field>

        {audioSource === "url" ? (
          <Field label="Audio URL" hint="Direct link to an mp3/stream">
            <TextInput
              type="url"
              value={value.audio_url ?? ""}
              onChange={(v) => patch({ audio_url: v || undefined })}
              placeholder="https://…/audio.mp3"
            />
          </Field>
        ) : (
          <Field label="Audio file" hint="Only .mp3 is allowed (max 25 MB)">
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <input
                type="file"
                accept=".mp3,audio/mpeg"
                disabled={uploading}
                onChange={(e) => handleAudioFile(e.target.files?.[0] ?? null)}
              />
              {uploading && <span style={{ fontSize: 13 }}>Uploading…</span>}
              {uploadErr && <span style={{ fontSize: 13, color: "#c0392b" }}>{uploadErr}</span>}
              {audioPreview.startsWith("/media/") && !uploading && (
                <span style={{ fontSize: 12, color: "var(--muted, #888)" }}>
                  Uploaded → {audioPreview}
                </span>
              )}
            </div>
          </Field>
        )}

        {/* Live player so the author can hear exactly what they're attaching
            before saving. Only render for a real http(s) URL. */}
        {audioPreview &&
          (isPlayableAudio ? (
            <>
              <audio
                key={audioPreview}
                controls
                preload="metadata"
                src={audioPreview}
                style={{ width: "100%", margin: "4px 0 4px" }}
                data-testid="listening-editor-audio"
                onError={() => setAudioLoadErr(true)}
                onLoadedMetadata={() => setAudioLoadErr(false)}
              />
              {audioLoadErr && (
                <p style={{ color: "#c0392b", fontSize: 13, margin: "0 0 12px" }}>
                  Couldn't load this audio. Check the URL is a direct, public
                  audio file (a hard refresh may be needed after recent changes).
                </p>
              )}
            </>
          ) : (
            <p style={{ color: "var(--muted, #c0392b)", fontSize: 13, margin: "4px 0 12px" }}>
              Enter a full http(s):// URL to preview the audio.
            </p>
          ))}

        <Field
          label="Transcript"
          hint="Revealed to the student only after the audio plays"
        >
          <TextArea
            value={value.transcript ?? ""}
            rows={5}
            onChange={(v) => patch({ transcript: v || undefined })}
            placeholder="Paste or write the transcript of the audio…"
          />
        </Field>
      </EditorCard>

      {/* ---- Card 2: Checkpoints ---- */}
      <EditorCard
        title="Comprehension checkpoints"
        actions={
          <SmallButton tone="primary" onClick={addCheckpoint}>
            + Add checkpoint
          </SmallButton>
        }
      >
        <p style={{ color: "var(--muted, #888)", fontSize: 13, margin: "0 0 8px" }}>
          Questions about the audio. Each must be answered correctly before the
          student continues.
        </p>

        {checkpoints.length === 0 ? (
          <p style={{ color: "var(--muted, #888)", fontSize: 13 }}>
            No checkpoints yet — add one to grade comprehension.
          </p>
        ) : (
          checkpoints.map((cp, idx) => (
            <div
              key={idx}
              style={{
                borderTop: idx === 0 ? "none" : "1px solid var(--border, #2a2a2a)",
                paddingTop: idx === 0 ? 0 : 14,
                marginTop: idx === 0 ? 0 : 14,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 6,
                }}
              >
                <strong style={{ fontSize: 13 }}>Checkpoint {idx + 1}</strong>
                <SmallButton tone="danger" onClick={() => removeCheckpoint(idx)}>
                  Remove
                </SmallButton>
              </div>

              <Field label="Question">
                <TextArea
                  value={cp.prompt ?? ""}
                  rows={2}
                  onChange={(v) => updateCheckpoint(idx, { prompt: v })}
                  placeholder="e.g. What will the weather be tomorrow?"
                />
              </Field>

              <Field label="Accepted answer" hint="Case/spacing-insensitive match">
                <TextInput
                  value={cp.ans ?? ""}
                  onChange={(v) => updateCheckpoint(idx, { ans: v })}
                  placeholder="e.g. sunny"
                />
              </Field>

              <Field label="Feedback" hint="Shown after a correct answer (optional)">
                <TextInput
                  value={cp.fb ?? ""}
                  onChange={(v) => updateCheckpoint(idx, { fb: v })}
                  placeholder="e.g. Correct — clear skies ahead."
                />
              </Field>
            </div>
          ))
        )}
      </EditorCard>
    </div>
  );
}
