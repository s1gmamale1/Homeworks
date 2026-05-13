# Media Migration Root Cause Audit - 2026-05-14

## TL;DR

The media loss was not a rendering-only bug. PR #206 introduced a destructive repair rule that treated every `/generated/...` image reference in math/geometry content as stale and replaced it with generated SVG data URIs. PR #208 improved parts of the repair path and exposed manual migration controls, but the broader migration flow still allowed automatic SVG rewriting during save/migrate. This created the "new fixes disappear later" pattern.

## Timeline

| Commit / PR | Change | Media impact |
| --- | --- | --- |
| `9a9b576` / #202 | Added read-time `content_json` compatibility normalization | Additive read path; not the main image-loss cause. |
| `d21c495` / #206 | `repair_math_geometry_homeworks.py` began matching `/generated/*.png|jpg|webp|svg` as stale media | Destructive. Replaced authored/generated images with SVG data URIs. |
| `98c3c9b` / #208 | Added manual migration API/UI and revised repair behavior | Reduced some damage but kept migration/repair as a user-triggered write path. |
| `a7d13fc` / #214 | Added `content_media_migration.py` to preserve generated URLs and extract bitmap data URIs | Good direction, but still rewrote generic SVG placeholders into new context SVGs. |
| #216/#217 | Builder image remove/replace controls | Not the original loss cause; helps manual restoration once migration is safe. |

## Evidence

Mac DB backup counts:

| DB snapshot | `<img>` | `/generated/` | `data:image` | `<svg>` |
| --- | ---: | ---: | ---: | ---: |
| `nets.db.bak-20260508-021134` | 58 | 41 | 115 | 213 |
| `nets.db.bak-fix-hw008-20260508-025336` | 58 | 1 | 155 | 213 |
| Current active API rows | 0 normal generated image refs in active homework API scan | 0 | 0 | 294 SVG fragments |

The sharp drop from 41 `/generated/` refs to 1 happened between the May 8 backups, matching the #206 repair window.

## Root Cause Findings

| ID | Severity | File / function | What happened | Fix direction |
| --- | --- | --- | --- | --- |
| MEDIA-1 | Critical | `scripts/oneoff/repair_math_geometry_homeworks.py` from #206 | `_is_stale_generated_image_ref` classified valid generated images as stale and `_repair_node` replaced them with SVG data URIs. | Never convert valid `/generated/` images to SVG. Normalize absolute generated URLs to `/generated/...` only. |
| MEDIA-2 | High | `server/services/content_media_migration.py` | Generic SVGs were rewritten into context SVGs during migration. This can make saves/migrations mutate visuals unexpectedly. | Preserve existing SVG markup; flag poor artwork in QA, not in schema migration. |
| MEDIA-3 | High | `server/routes/homework.py` PUT/PATCH + migrate endpoint | Normal save paths call media migration. If migration rewrites visuals, opening builder and saving can silently change media. | Keep save-time migration strictly preservation-only. |
| MEDIA-4 | Medium | Mac deployment state | Live Mac was on `codex/builder-media-actions-always-visible-2026-05-14`, ahead/behind, with untracked DB/backups/generated files. | After current fixes merge, deploy from clean `server` and avoid long-running temporary branches on production. |

## Fix Applied In This Branch

- `content_media_migration.py` now preserves SVG data URI payloads exactly after decoding.
- It no longer rewrites generic SVG markers into new context SVGs.
- `repair_math_geometry_homeworks.py` no longer treats generic SVG placeholders as something to auto-rewrite.
- Regression tests pin that generic SVGs are preserved for manual review and are not silently replaced during migration.

## Remaining Data Restoration Work

This code fix prevents repeat damage. It does not restore already-lost real images.

For restoration, use DB backups / the worker source that still has valid images:

1. Restore only real authored images into `/generated/...`.
2. Patch only media fields, not lesson text/questions.
3. Verify builder/player/preview.
4. Run migration-status; do not run broad repair scripts.

