import { useState } from "react";
import { youtubeId, youtubeEmbedSrc, youtubeWatchUrl, isImageUrl } from "./embed";
import s from "./ExtraMaterialsView.module.css";

// Click-to-play YouTube facade. The thumbnail is a plain <img> (not blocked by
// tracking prevention / ad blockers, unlike the iframe), and the iframe is
// mounted only on a user click — which usually bypasses the block. The "Open on
// YouTube" link below is the always-works fallback.
function YouTubeEmbed({
  embed,
  watch,
  thumb,
  label,
}: {
  embed: string;
  watch: string;
  thumb: string | null;
  label: string;
}) {
  const [playing, setPlaying] = useState(false);
  return (
    <div className={s.item}>
      <div className={s.itemLabel}>{label}</div>
      <div className={s.embed}>
        {playing ? (
          <iframe
            src={`${embed}?autoplay=1&rel=0`}
            title={label}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <button
            type="button"
            className={s.facade}
            onClick={() => setPlaying(true)}
            style={thumb ? { backgroundImage: `url(${thumb})` } : undefined}
            aria-label={`Play ${label}`}
          >
            <span className={s.playBtn} aria-hidden="true">
              ▶
            </span>
          </button>
        )}
      </div>
      <a className={s.fallbackLink} href={watch} target="_blank" rel="noopener noreferrer">
        Open on YouTube ↗
      </a>
    </div>
  );
}

// Structural props so this renders identically from the builder (DraftExtra…)
// and the runtime (raw content_json.extra_materials). `type` is "link" |
// "video" | "file" (string-typed here to accept both call sites).
export interface ExtraMaterialViewItem {
  label?: string;
  url?: string;
  type?: string;
}

export interface ExtraMaterialsViewData {
  title?: string;
  intro?: string;
  items?: ExtraMaterialViewItem[];
}

// Render one item. YouTube URLs (type video or link) embed as a privacy-mode
// iframe with an "Open on YouTube" fallback; image files render inline; anything
// else is a click-through link. Shared by the editor preview, the builder
// preview surface, and the student runtime so all three match.
export function ExtraMaterialItemView({ item }: { item: ExtraMaterialViewItem }) {
  const url = (item.url ?? "").trim();
  if (!url) return null;
  const label = (item.label ?? "").trim() || url;
  const type = item.type ?? "link";

  const embed = type === "video" || type === "link" ? youtubeEmbedSrc(url) : null;
  if (embed) {
    const id = youtubeId(url);
    return (
      <YouTubeEmbed
        embed={embed}
        watch={youtubeWatchUrl(url) ?? url}
        thumb={id ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : null}
        label={label}
      />
    );
  }

  if (type === "file" && isImageUrl(url)) {
    return (
      <div className={s.item}>
        <div className={s.itemLabel}>{label}</div>
        <img className={s.image} src={url} alt={label} loading="lazy" />
      </div>
    );
  }

  const icon = type === "video" ? "🎬" : type === "file" ? "📎" : "🔗";
  return (
    <a className={s.link} href={url} target="_blank" rel="noopener noreferrer">
      <span className={s.linkIcon} aria-hidden="true">
        {icon}
      </span>
      <span>{label}</span>
    </a>
  );
}

export function ExtraMaterialsView({ value }: { value: ExtraMaterialsViewData }) {
  const items = (value.items ?? []).filter((it) => (it.url ?? "").trim() !== "");
  return (
    <div className={s.wrap}>
      {value.title && <h3 className={s.title}>{value.title}</h3>}
      {value.intro && <p className={s.intro}>{value.intro}</p>}
      {items.length === 0 ? (
        <p className={s.empty}>No materials added yet.</p>
      ) : (
        <div className={s.list}>
          {items.map((it, i) => (
            <ExtraMaterialItemView key={i} item={it} />
          ))}
        </div>
      )}
    </div>
  );
}
