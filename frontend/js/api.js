// frontend/js/api.js
// NETS Builder frontend API bridge.
// Keeps all route paths and request handling in one place so dashboard.js and builder.js stay clean.

(function () {
  "use strict";

  const API_BASE = (window.NETS_API_BASE || "").replace(/\/$/, "");

  function buildUrl(path) {
    return `${API_BASE}${path}`;
  }

  function encodeId(id) {
    return encodeURIComponent(String(id || ""));
  }

  async function parseResponse(response) {
    const contentType = response.headers.get("content-type") || "";

    if (response.status === 204) {
      return null;
    }

    if (contentType.includes("application/json")) {
      return response.json();
    }

    return response.text();
  }

  async function request(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const hasBody = Object.prototype.hasOwnProperty.call(options, "body");

    if (hasBody && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(buildUrl(path), {
      ...options,
      headers,
      body:
        hasBody && !(options.body instanceof FormData) && typeof options.body !== "string"
          ? JSON.stringify(options.body)
          : options.body,
    });

    const payload = await parseResponse(response);

    if (!response.ok) {
      const message =
        payload && typeof payload === "object" && payload.error
          ? payload.error
          : `Request failed with ${response.status}`;

      const error = new Error(message);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  function toSsePayload(raw) {
    if (!raw) return null;

    try {
      return JSON.parse(raw);
    } catch (_) {
      return raw;
    }
  }

  function dispatchSseEvent(eventName, data, handlers) {
    const name = eventName || "message";
    const payload = toSsePayload(data);

    if (typeof handlers[name] === "function") {
      handlers[name](payload);
    }

    if (typeof handlers.event === "function") {
      handlers.event({ event: name, data: payload });
    }
  }

  async function readSseStream(response, handlers = {}) {
    if (!response.body) {
      throw new Error("Streaming is not supported by this browser.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

      let boundary = buffer.indexOf("\n\n");

      while (boundary !== -1) {
        const chunk = buffer.slice(0, boundary).trim();
        buffer = buffer.slice(boundary + 2);

        if (chunk) {
          let eventName = "message";
          const dataLines = [];

          for (const line of chunk.split("\n")) {
            const clean = line.trimEnd();

            if (clean.startsWith("event:")) {
              eventName = clean.slice(6).trim();
            } else if (clean.startsWith("data:")) {
              dataLines.push(clean.slice(5).trimStart());
            }
          }

          dispatchSseEvent(eventName, dataLines.join("\n"), handlers);
        }

        boundary = buffer.indexOf("\n\n");
      }

      if (done) break;
    }

    const tail = buffer.trim();
    if (tail) {
      let eventName = "message";
      const dataLines = [];

      for (const line of tail.split("\n")) {
        const clean = line.trimEnd();

        if (clean.startsWith("event:")) {
          eventName = clean.slice(6).trim();
        } else if (clean.startsWith("data:")) {
          dataLines.push(clean.slice(5).trimStart());
        }
      }

      dispatchSseEvent(eventName, dataLines.join("\n"), handlers);
    }
  }

  async function generateHomework(id, body, handlers = {}) {
    const controller = new AbortController();
    const path = `/api/homeworks/${encodeId(id)}/generate`;

    const promise = fetch(buildUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body || {}),
      signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) {
        const payload = await parseResponse(response);
        const message =
          payload && typeof payload === "object" && payload.error
            ? payload.error
            : `AI generation failed with ${response.status}`;

        const error = new Error(message);
        error.status = response.status;
        error.payload = payload;
        throw error;
      }

      await readSseStream(response, handlers);
    });

    return {
      abort: () => controller.abort(),
      done: promise,
    };
  }

  async function listFixtures() {
    const response = await fetch(buildUrl("/api/fixtures"), { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Failed to list fixtures");
    return response.json();
  }

  async function getFixture(name) {
    const response = await fetch(buildUrl(`/api/fixtures/${encodeURIComponent(name)}`), {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`Could not load fixture: ${name}`);
    return response.json();
  }

  window.API = {
    request,

    getSubjects() {
      return request("/api/subjects");
    },

    listFixtures,
    getFixture,

    getHealth() {
      return request("/api/health");
    },

    /**
     * Paginated + filtered homework list.
     * @param {Object} params
     * @param {string} [params.q]       - Free-text search (title/subject/family LIKE)
     * @param {string} [params.subject] - Exact subject filter
     * @param {number} [params.grade]   - Exact grade filter
     * @param {string} [params.mode]    - Exact mode filter (easy|hard)
     * @param {number} [params.limit]   - Page size (default 50, max 200)
     * @param {number} [params.offset]  - Pagination offset (default 0)
     * @returns {Promise<{items: Array, total: number, limit: number, offset: number}>}
     */
    getHomeworks(params = {}) {
      const qs = new URLSearchParams();
      if (params.q)       qs.set("q", params.q);
      if (params.subject) qs.set("subject", params.subject);
      if (params.grade != null) qs.set("grade", String(params.grade));
      if (params.mode)    qs.set("mode", params.mode);
      if (params.limit != null)  qs.set("limit", String(params.limit));
      if (params.offset != null) qs.set("offset", String(params.offset));
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      return request(`/api/homeworks${suffix}`);
    },

    /**
     * Legacy shim — returns bare array for backward-compat callers.
     * @returns {Promise<Array>}
     */
    listHomeworks() {
      return this.getHomeworks().then((r) => r.items);
    },

    createHomework({ title, subject, grade, mode }) {
      return request("/api/homeworks", {
        method: "POST",
        body: { title, subject, grade: Number(grade), mode },
      });
    },

    getHomework(id) {
      return request(`/api/homeworks/${encodeId(id)}`);
    },

    updateHomework(id, payload) {
      return request(`/api/homeworks/${encodeId(id)}`, {
        method: "PUT",
        body: payload,
      });
    },

    // URL builder used by beforeunload / visibilitychange flush path.
    // Returns an absolute URL so fetch(..., {keepalive:true}) and navigator.sendBeacon
    // both work from any document context.
    getHomeworkUrl(id) {
      return buildUrl(`/api/homeworks/${encodeId(id)}`);
    },

    // Fire-and-forget PUT that survives tab close.
    // Prefers fetch+keepalive (carries JSON Content-Type, full PUT semantics).
    // Falls back to sendBeacon (POST-only, sent as application/json Blob) if
    // keepalive fetch throws synchronously.
    // Returns true if a request was queued, false otherwise.
    flushHomework(id, payload) {
      if (!id) return false;

      const url = buildUrl(`/api/homeworks/${encodeId(id)}`);
      const body = typeof payload === "string" ? payload : JSON.stringify(payload || {});

      // Primary: fetch with keepalive (all modern browsers honor this on unload).
      try {
        fetch(url, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body,
          keepalive: true,
        }).catch(() => {
          /* best effort — no retry possible post-unload */
        });
        return true;
      } catch (_err) {
        // keepalive payload too large, or fetch unavailable — fall through.
      }

      // Fallback: sendBeacon. Note this will hit the endpoint as POST, not PUT;
      // backend may ignore it, but the network record is still useful as a signal.
      if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
        try {
          const blob = new Blob([body], { type: "application/json" });
          return navigator.sendBeacon(url, blob);
        } catch (_err) {
          return false;
        }
      }

      return false;
    },

    deleteHomework(id) {
      return request(`/api/homeworks/${encodeId(id)}`, {
        method: "DELETE",
      });
    },

    duplicateHomework(id) {
      return request(`/api/homeworks/${encodeId(id)}/duplicate`, {
        method: "POST",
      });
    },

    restoreHomework(id) {
      return request(`/api/homeworks/${encodeId(id)}/restore`, {
        method: "POST",
      });
    },

    hardDeleteHomework(id) {
      return request(`/api/homeworks/${encodeId(id)}/permanent`, {
        method: "DELETE",
      });
    },

    listTrash() {
      return request("/api/trash");
    },

    listVersions(id) {
      return request(`/api/homeworks/${encodeId(id)}/versions`);
    },

    restoreVersion(id, versionId) {
      return request(`/api/homeworks/${encodeId(id)}/versions/${encodeURIComponent(versionId)}/restore`, {
        method: "POST",
      });
    },

    generateHomework,

    getPreviewUrl(id) {
      return buildUrl(`/api/homeworks/${encodeId(id)}/preview`);
    },

    createSession({ homework_id, student_name }) {
      return request("/api/sessions", {
        method: "POST",
        body: { homework_id, student_name },
      });
    },

    submitSessionResponse(id, body) {
      return request(`/api/sessions/${encodeId(id)}/response`, {
        method: "POST",
        body,
      });
    },

    getSession(id) {
      return request(`/api/sessions/${encodeId(id)}`);
    },
  };
})();
