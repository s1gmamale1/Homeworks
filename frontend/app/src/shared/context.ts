// Reads the runtime context the FastAPI SPA shell injects as window.NETS_CTX.
// Falls back to URL parsing for dev (Vite :5173) where there's no server shell.

export interface NetsContext {
  hwId: string | null;
  token: string | null;
  sessionId: string | null;
  flowVersion: string | null;
}

declare global {
  interface Window {
    NETS_CTX?: {
      hw_id?: string;
      token?: string;
      session_id?: string;
      flow_version?: string;
    };
  }
}

export function readContext(): NetsContext {
  const ctx = window.NETS_CTX ?? {};
  const url = new URL(window.location.href);

  // Path form: /h/{id} or /app/h/{id}
  const pathMatch = url.pathname.match(/\/h\/([^/?#]+)/);
  const hwId = ctx.hw_id ?? pathMatch?.[1] ?? url.searchParams.get("hw") ?? null;

  return {
    hwId,
    token: ctx.token ?? url.searchParams.get("token") ?? null,
    sessionId: ctx.session_id ?? url.searchParams.get("session") ?? null,
    flowVersion: ctx.flow_version ?? null,
  };
}
