import { useCallback, useState } from "react";
import type {
  ExtraMaterialsEditorProps,
  DraftExtraMaterialItem,
  ExtraMaterialType,
} from "./types";
import { EditorCard, Field, TextInput, Select, SmallButton } from "./fields";
import { ExtraMaterialItemView } from "../shared/ExtraMaterialsView";
import { uploadFile } from "./builderApi";

// ---------------------------------------------------------------------------
// Extra Materials editor (UNGRADED) — owns content_json.extra_materials.
// Each item has a `type` that drives BOTH the input and the renderer:
//   link  → URL input → click-through link
//   video → URL input → YouTube embeds as an iframe, else a link
//   file  → file upload (POST /api/uploads) → inline image or download link
// A live preview of each item renders below its fields.
// ---------------------------------------------------------------------------

const wrap: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 16,
};

const TYPE_OPTIONS: { value: ExtraMaterialType; label: string }[] = [
  { value: "link", label: "Link" },
  { value: "video", label: "Video (embed)" },
  { value: "file", label: "File upload" },
];

// Mirrors the server upload allowlist (server/routes/uploads.py).
const FILE_ACCEPT =
  ".png,.jpg,.jpeg,.gif,.webp,.svg,.mp3,.wav,.ogg,.m4a,.mp4,.webm,.mov,.pdf,.txt,.csv,.doc,.docx,.ppt,.pptx,.xls,.xlsx";

function emptyItem(): DraftExtraMaterialItem {
  return { label: "", url: "", type: "link" };
}

function ItemEditor({
  item,
  index,
  onChange,
  onRemove,
}: {
  item: DraftExtraMaterialItem;
  index: number;
  onChange: (next: DraftExtraMaterialItem) => void;
  onRemove: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const type = item.type ?? "link";

  const handleFile = async (file: File | null) => {
    if (!file) return;
    setUploading(true);
    setUploadErr(null);
    try {
      const res = await uploadFile(file);
      onChange({ ...item, url: res.url, label: item.label || res.name });
    } catch (e) {
      setUploadErr((e as Error).message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      style={{
        borderTop: index === 0 ? "none" : "1px solid var(--border, #2a2a2a)",
        paddingTop: index === 0 ? 0 : 16,
        marginTop: index === 0 ? 0 : 16,
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
        <strong style={{ fontSize: 13 }}>Item {index + 1}</strong>
        <SmallButton tone="danger" onClick={onRemove}>
          Remove
        </SmallButton>
      </div>

      <Field label="Label" hint="What the student sees">
        <TextInput
          value={item.label ?? ""}
          onChange={(v) => onChange({ ...item, label: v })}
          placeholder="e.g. Intro video"
        />
      </Field>

      <Field label="Type">
        <Select<ExtraMaterialType>
          value={type}
          onChange={(v) => onChange({ ...item, type: v })}
          options={TYPE_OPTIONS}
        />
      </Field>

      {type === "file" ? (
        <Field label="File" hint="Image, PDF, audio, video or document (max 25 MB)">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <input
              type="file"
              accept={FILE_ACCEPT}
              disabled={uploading}
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
            {uploading && <span style={{ fontSize: 13 }}>Uploading…</span>}
            {uploadErr && (
              <span style={{ fontSize: 13, color: "#c0392b" }}>{uploadErr}</span>
            )}
            {item.url && !uploading && (
              <span style={{ fontSize: 12, color: "var(--muted, #888)" }}>
                Uploaded → {item.url}
              </span>
            )}
          </div>
        </Field>
      ) : (
        <Field
          label="URL"
          hint={
            type === "video"
              ? "Paste a YouTube link — it embeds automatically"
              : "http(s) link"
          }
        >
          <TextInput
            type="url"
            value={item.url ?? ""}
            onChange={(v) => onChange({ ...item, url: v })}
            placeholder={type === "video" ? "https://youtu.be/…" : "https://…"}
          />
        </Field>
      )}

      {/* Live preview of exactly how this item will render. */}
      {(item.url ?? "").trim() !== "" && (
        <div style={{ marginTop: 10 }}>
          <ExtraMaterialItemView item={item} />
        </div>
      )}
    </div>
  );
}

export function ExtraMaterialsEditor({ value, onChange }: ExtraMaterialsEditorProps) {
  const patch = useCallback(
    (partial: Partial<typeof value>) => onChange({ ...value, ...partial }),
    [value, onChange]
  );

  const items = value.items ?? [];

  const addItem = useCallback(() => {
    patch({ items: [...items, emptyItem()] });
  }, [patch, items]);

  const updateItem = useCallback(
    (idx: number, next: DraftExtraMaterialItem) => {
      patch({ items: items.map((it, i) => (i === idx ? next : it)) });
    },
    [patch, items]
  );

  const removeItem = useCallback(
    (idx: number) => {
      patch({ items: items.filter((_, i) => i !== idx) });
    },
    [patch, items]
  );

  return (
    <div style={wrap}>
      {/* ---- Card 1: Section copy ---- */}
      <EditorCard title="Section copy">
        <p style={{ color: "var(--muted, #888)", fontSize: 13, margin: "0 0 8px" }}>
          Ungraded. Shown near the end of the homework.
        </p>

        <Field label="Section title" hint="Optional heading">
          <TextInput
            value={value.title ?? ""}
            onChange={(v) => patch({ title: v || undefined })}
            placeholder="e.g. Go further"
          />
        </Field>

        <Field label="Intro" hint="One line of context (optional)">
          <TextInput
            value={value.intro ?? ""}
            onChange={(v) => patch({ intro: v || undefined })}
            placeholder="e.g. Optional resources to explore the topic."
          />
        </Field>
      </EditorCard>

      {/* ---- Card 2: Items ---- */}
      <EditorCard
        title="Materials"
        actions={
          <SmallButton tone="primary" onClick={addItem}>
            + Add item
          </SmallButton>
        }
      >
        {items.length === 0 ? (
          <p style={{ color: "var(--muted, #888)", fontSize: 13 }}>
            No materials yet — add a link, an embeddable video, or upload a file.
          </p>
        ) : (
          items.map((it, idx) => (
            <ItemEditor
              key={idx}
              item={it}
              index={idx}
              onChange={(next) => updateItem(idx, next)}
              onRemove={() => removeItem(idx)}
            />
          ))
        )}
      </EditorCard>
    </div>
  );
}
