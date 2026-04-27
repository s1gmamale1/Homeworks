# Auth Model Decision — 2026-04-27

## Status
Proposal — pending approval.

## Three options

### A. Public-by-default (status quo)
- **What it means:** All homeworks are accessible to anyone with the permanent URL `/h/{id}`. No authentication layer.
- **Pros:** Zero friction for students; no sign-up, password resets, or session management. Perfect for quick one-off shareable links.
- **Cons:** No privacy; homeworks leak to search engines; impossible to enforce per-student scoping (e.g., "this homework only for 8th grade"); answers and feedback visible to anyone; no audit trail.
- **Who breaks:** Multi-school deployments, schools with privacy requirements, teachers who want per-class rosters, any rollout with >100 homeworks.

### B. Token-in-URL (capability links)
- **What it means:** Each homework gets a long random slug (`/h/<128-char-slug>`). Possessing the URL grants access; sharing the URL shares access. No login needed.
- **Pros:** Simple to implement (~2 hours); unguessable links prevent accidental enumeration; shareable with a click; privacy-friendly (no identity tracked); defers multi-user complexity. Works for 99% of small-school use cases.
- **Cons:** No built-in roster/audit; if a URL leaks, everyone on the internet has access; can't revoke access per-student without regenerating the link; doesn't scale to "homework inbox for student X".

### C. Full multi-user (Google OAuth / email magic link)
- **What it means:** Students log in via OAuth (Google, Microsoft) or email magic link. Teachers get a dashboard with class rosters, assignment grading, and per-student link generation. Per-school scoping.
- **Pros:** Enterprise-ready; fine-grained access control; audit trail; roster management; per-student progress tracking; scales to multi-school deployments.
- **Cons:** Significant engineering (6–10 days); persistent sessions, user management, group scoping, audit. Requires external identity provider or email backend. Overkill for a single-school MVP.

---

## Recommendation
**Option B (Token-in-URL)** for the next 3–6 months. It unblocks production deployments with minimal complexity, gives teachers shareable-but-private links, and buys time to validate demand before committing to the full multi-user stack. If a school outgrows this model (needs roster management or per-student revocation), option C becomes the next wave.

---

## Open questions for the team
- How many schools do we target by June 2026? (Affects break-even point for option C.)
- Do we need per-student progress tracking in v1.0, or is shareable homework enough?
- Should we reserve namespace for option C now (e.g., `/api/v2/users/*`) to avoid a v2 migration later?

---

## Implementation tasks (file as separate issues once decided)

For **Option B**:
1. Update `POST /api/homeworks` to generate a 128-character random slug on creation.
2. Change route from `/h/{id}` to `/h/{slug}`.
3. Add `slug` column to homework schema; migrate existing homeworks.
4. Update frontend static links (dashboard, preview button) to use slug.
5. Update export to use slug in the standalone HTML title/path.
6. Security: rate-limit `/h/{slug}` to prevent brute-force enumeration.
7. Docs: add "how to share a homework" guide.

For **Option C** (deferred):
1. Add user + group + role tables.
2. Integrate identity provider (Google OAuth or email magic link).
3. Build teacher dashboard and roster UI.
4. Fine-grained access control: user → groups → homeworks.
5. Audit logging: who accessed what, when.
