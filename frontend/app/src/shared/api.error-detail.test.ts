// Regression: ApiError.message must NEVER render as "[object Object]" when
// the server returns FastAPI's object-shaped HTTPException.detail.
//
// The legacy api.ts cast `body.detail` to `string` and assigned it directly
// into a string variable; newer routes (reflection, runtime gate, integrity)
// raise HTTPException(detail={"error": "...", "code": "..."}). Naive template
// interpolation of that object yielded "404 [object Object]" in the UI —
// see the screenshot in PR description. The fix extracts .error / .message /
// .code (in that order), falling back to JSON.stringify only as last resort.
//
// We test through `getReflection`, which uses the same shared `request()`
// helper as everything else, so any caller that gets a 4xx with object detail
// is implicitly covered.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiError, getReflection } from "./api";

function jsonResponse(body: unknown, status: number, statusText = "ERR"): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: async () => body,
  } as Response;
}

beforeEach(() => {
  globalThis.fetch = vi.fn() as unknown as typeof fetch;
});

describe("ApiError message rendering — object-shaped HTTPException.detail", () => {
  it("does NOT contain '[object Object]' when detail is an object", async () => {
    // Exact response shape FastAPI emits for reflection_engine SESSION_NOT_FOUND.
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse(
        { detail: { error: "Session not found", code: "SESSION_NOT_FOUND" } },
        404,
        "Not Found"
      )
    );

    let caught: unknown = null;
    try {
      await getReflection("HW-1", "s1");
    } catch (e) {
      caught = e;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.status).toBe(404);
    // The regression: pre-fix code rendered "[object Object]" because the
    // object detail was coerced via template-string interpolation.
    expect(err.message).not.toContain("[object Object]");
    // The good behavior: the user-facing string is the .error field verbatim.
    expect(err.message).toContain("Session not found");
  });

  it("prefers .error, then .message, then .code from object detail", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({ detail: { code: "ONLY_CODE_PRESENT" } }, 409)
    );
    let caught: unknown = null;
    try {
      await getReflection("HW-2", "s2");
    } catch (e) {
      caught = e;
    }
    expect((caught as ApiError).message).toContain("ONLY_CODE_PRESENT");
    expect((caught as ApiError).message).not.toContain("[object Object]");
  });

  it("still handles string-shaped detail (legacy routes) correctly", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      jsonResponse({ detail: "Plain string error from a legacy route" }, 422)
    );
    let caught: unknown = null;
    try {
      await getReflection("HW-3", "s3");
    } catch (e) {
      caught = e;
    }
    expect((caught as ApiError).message).toContain(
      "Plain string error from a legacy route"
    );
  });

  it("falls back to statusText when body is non-JSON", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => {
        throw new Error("not json");
      },
    } as unknown as Response);
    let caught: unknown = null;
    try {
      await getReflection("HW-4", "s4");
    } catch (e) {
      caught = e;
    }
    expect((caught as ApiError).message).toContain("Internal Server Error");
  });
});
