// URL helpers for Extra Materials rendering.

// Extract the 11-char video id from any common YouTube URL shape, else null.
export function youtubeId(url: string): string | null {
  const u = (url || "").trim();
  const patterns = [
    /youtube\.com\/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})/,
    /youtu\.be\/([A-Za-z0-9_-]{11})/,
    /youtube\.com\/embed\/([A-Za-z0-9_-]{11})/,
    /youtube(?:-nocookie)?\.com\/embed\/([A-Za-z0-9_-]{11})/,
    /youtube\.com\/shorts\/([A-Za-z0-9_-]{11})/,
  ];
  for (const re of patterns) {
    const m = u.match(re);
    if (m) return m[1];
  }
  return null;
}

// Embeddable iframe src for a YouTube URL, or null. Uses the privacy-enhanced
// youtube-nocookie domain, which browser tracking-prevention (Edge/Brave/ad
// blockers) is far less likely to block than youtube.com.
export function youtubeEmbedSrc(url: string): string | null {
  const id = youtubeId(url);
  return id ? `https://www.youtube-nocookie.com/embed/${id}` : null;
}

// Canonical watch URL for the "Open on YouTube" fallback link.
export function youtubeWatchUrl(url: string): string | null {
  const id = youtubeId(url);
  return id ? `https://www.youtube.com/watch?v=${id}` : null;
}

// True when the URL points at an image we can render inline with <img>.
export function isImageUrl(url: string): boolean {
  return /\.(png|jpe?g|gif|webp|svg)(\?|#|$)/i.test((url || "").trim());
}
