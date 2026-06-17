// Builder authoring API. Reuses the existing homework CRUD endpoints UNCHANGED:
//   - POST  /api/homeworks               create ({title, subject, grade, mode})
//   - GET   /api/homeworks               list (content_json stripped)
//   - GET   /api/homeworks/{id}          UNREDACTED full row (authoring read)
//   - PUT   /api/homeworks/{id}          full content_json overwrite
//   - PATCH /api/homeworks/{id}/content  partial content_json merge
//
// Authoring reads the UNREDACTED GET on purpose — the builder needs the answers
// (the runtime redactor strips them only on the student delivery path).

import type { HomeworkRow } from "./types";

const BASE = "";

export class BuilderApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "BuilderApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch (networkErr) {
    throw new BuilderApiError(
      `Network error reaching ${path}: ${(networkErr as Error).message}`,
      0
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body?.detail === "string") detail = body.detail;
      else if (body?.detail && typeof body.detail === "object")
        detail = JSON.stringify(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new BuilderApiError(`${res.status} ${detail}`, res.status);
  }
  // 204 / empty body tolerance.
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

export interface CreateHomeworkInput {
  title: string;
  subject: string;
  grade: number;
  mode: "easy" | "hard";
  // Optional caller-supplied content_json; merged with the v2 tag below.
  content_json?: Record<string, unknown>;
}

/**
 * Create a fresh homework row. Returns the persisted row (incl. `id`). We tag
 * the new row v2 by seeding `content_json: { flow_version: "v2" }` (merged with
 * any caller-supplied content_json) so every builder-created homework is a v2
 * row from creation — the runtime + builder both branch on flow_version.
 */
export function createHomework(input: CreateHomeworkInput): Promise<HomeworkRow> {
  const { content_json, ...rest } = input;
  return request<HomeworkRow>("/api/homeworks", {
    method: "POST",
    body: JSON.stringify({
      ...rest,
      content_json: { flow_version: "v2", ...(content_json ?? {}) },
    }),
  });
}

/** Delete a homework row. Resolves on 200/204. */
export function deleteHomework(id: string): Promise<void> {
  return request<void>(`/api/homeworks/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

/**
 * Duplicate a homework row server-side. Returns the persisted copy (new `id`).
 */
export function duplicateHomework(id: string): Promise<HomeworkRow> {
  return request<HomeworkRow>(
    `/api/homeworks/${encodeURIComponent(id)}/duplicate`,
    { method: "POST" }
  );
}

/** List homeworks (content_json is stripped server-side for the list view).
 * The endpoint returns `{ items: [...] }` — unwrap it (defensively tolerate a
 * bare array too) so callers get a real HomeworkRow[]. */
export async function listHomeworks(): Promise<HomeworkRow[]> {
  const res = await request<HomeworkRow[] | { items?: HomeworkRow[] }>(
    "/api/homeworks"
  );
  if (Array.isArray(res)) return res;
  return res?.items ?? [];
}

/** GET the UNREDACTED full row for authoring (answers included). */
export function getHomework(id: string): Promise<HomeworkRow> {
  return request<HomeworkRow>(`/api/homeworks/${encodeURIComponent(id)}`);
}

/** Full content_json overwrite (also lets us patch the title). */
export function putHomework(
  id: string,
  body: { title?: string; content_json?: Record<string, unknown> }
): Promise<HomeworkRow> {
  return request<HomeworkRow>(`/api/homeworks/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

/** One unmet delivery-grade rule on the stored content_json. */
export interface ReadinessIssue {
  path: string;
  msg: string;
}
/** Strict (delivery-grade) readiness of a homework — whether it's complete
 * enough to share. The builder autosaves leniently; this is the share gate. */
export interface Readiness {
  ready: boolean;
  issues: ReadinessIssue[];
}

/** GET strict readiness — used to surface "fix N issues before sharing".
 * Mirrors GET /api/homeworks/{id}/readiness. */
export function getReadiness(id: string): Promise<Readiness> {
  return request<Readiness>(
    `/api/homeworks/${encodeURIComponent(id)}/readiness`
  );
}

/** Partial content_json merge (server deep-merges the keys you send). */
export function patchHomeworkContent(
  id: string,
  content_json: Record<string, unknown>
): Promise<HomeworkRow> {
  return request<HomeworkRow>(
    `/api/homeworks/${encodeURIComponent(id)}/content`,
    { method: "PATCH", body: JSON.stringify({ content_json }) }
  );
}

// Subjects + their valid grades, mirrored from server/services/routing.py so the
// create form can't POST an invalid (subject, grade) pair.
export const SUBJECT_GRADES: Record<string, number[]> = {
  "math-algebra": [5, 6, 7, 8, 9, 10, 11],
  "geometriya-g7-11": [7, 8, 9, 10, 11],
  physics: [6, 7, 8, 9, 10, 11],
  biology: [5, 6, 7, 8, 9, 10, 11],
  "kimyo-g7-11": [7, 8, 9, 10, 11],
  english: [5, 6, 7, 8, 9, 10, 11],
  history: [5, 6, 7, 8, 9, 10, 11],
};

export const SUBJECT_LABELS: Record<string, string> = {
  "math-algebra": "Algebra",
  "geometriya-g7-11": "Geometry",
  physics: "Physics",
  biology: "Biology",
  "kimyo-g7-11": "Chemistry",
  english: "English",
  history: "History",
};

// english + history are always-hard server-side; the form still sends a mode
// but the server normalizes it.
export const ALWAYS_HARD = new Set(["english", "history"]);

// Multipart file upload for Extra Materials (type=file). Uses a bare fetch — the
// `request` helper forces a JSON Content-Type, but multipart needs the browser
// to set its own boundary header. Returns the stored URL the item points at.
export interface UploadResult {
  url: string;
  name: string;
  type: string;
}

export async function uploadFile(file: File, hwId: string): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  let res: Response;
  try {
    res = await fetch(`${BASE}/api/uploads?hw_id=${encodeURIComponent(hwId)}`, { method: "POST", body: form });
  } catch (networkErr) {
    throw new BuilderApiError(
      `Network error during upload: ${(networkErr as Error).message}`,
      0
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: { message?: string } | string };
      if (typeof body?.detail === "string") detail = body.detail;
      else if (body?.detail?.message) detail = body.detail.message;
    } catch {
      /* keep statusText */
    }
    throw new BuilderApiError(detail, res.status);
  }
  return (await res.json()) as UploadResult;
}
