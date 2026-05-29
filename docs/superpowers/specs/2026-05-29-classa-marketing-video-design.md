# Class A Education — Marketing Video (Remotion) — Design Spec

**Date:** 2026-05-29
**Status:** Approved (brainstorming gate passed)
**Owner:** product owner (s1gmamale1)
**Deliverable:** A polished ~72s 16:9 marketing video (rendered `.mp4`) + a reusable Remotion project.

---

## 1. Overview & goal

A flagship product marketing video for **Class A Education** — the company behind **NETS Homeworks**, an AI-powered, gamified homework platform (teachers build interactive lessons → share a link → students play a Duolingo-style learning hub of mini-games with a live AI tutor, hybrid grading, anti-cheat, and a reflection debrief).

The video is built in **Remotion** (code-as-video, React) so it stays editable, deterministic, and re-renderable, and so we can derive other aspect ratios (9:16, 1:1) cheaply later from the same composition.

## 2. Audience & positioning

- **Primary audience:** schools & private schools (institutional decision-makers).
- **Conversion drivers (research-backed for EdTech):** teacher *time saved* → student *engagement* → *outcomes + academic integrity*.
- **Core promise (one line):** *Turn any lesson into a game students want to finish — built, graded, and tutored by AI.*
- **Supporting benefits:** instant authoring + instant grading (teacher time back); intrinsic motivation via gamified unlock progression (student engagement); process-supervision integrity + per-student mastery readouts (institutional trust/outcomes).

## 3. Format, length, audio

- **Flagship:** 1920×1080 (16:9), 30 fps, **~72s** (2160 frames).
- **Audio:** royalty-free (CC0) music bed + **on-screen kinetic captions** (muted-first; 85% of social video is watched muted). **No voiceover/TTS.**
- **Captions language:** **Uzbek** (formal *Siz* register). In-product UI shown in screenshots is already Uzbek, reinforcing localization.
- **Parameterization:** the `<Composition>` takes `width`/`height`/`fps`/`lang` as props so a vertical 9:16 cut and/or an English caption track are near-free follow-ups.

## 4. Brand & art direction

Two-color story that bookends the cool product UI with the bold company brand.

### 4.1 Class A Education brand (bookends: hook accent, wordmark reveal, proof framing, CTA)
- **Brand red:** `#F40B16` (vivid red sampled from logo; **single token `BRAND_RED`, one-line tunable** — exact hex/PNG can be dropped in `marketing/public/brand/` for a pixel-perfect swap).
- **White** `#FFFFFF` on red; near-black `#0B0B0D` for dark canvases.
- **Logo:** recreated as vector `<ClassALogo>` — red rounded square + bold white **"A"** (flat-top apex, triangular counter, open bottom notch) + a white **4-point concave sparkle** upper-right. The A and sparkle animate independently (sparkle twinkle = signature motif, echoes the product's own sparkle glyph).
- **Wordmark:** icon + "Class A Education" set in Onest/Fredoka bold.

### 4.2 NETS Homeworks product UI (demo beats — keep as-is, it IS the product)
Tokens pulled verbatim from the codebase (`frontend/app/src/runtime/*`, `server/template/perfect_homework.html`):
- **Product blue:** `#0a72e0` / accent `#0066CC`; category-gradient top-bars — game `linear-gradient(135deg,#b388eb,#8a5fc8)`, content `#ffd166→#f4a261`, language `#74aa9c→#4a8576`, boss `#e26d6d→#c93a3a`, interaction `#5e9ed6→#4677b8`.
- **Type:** Onest (system), Fredoka (hub display), Nunito (hub body).
- **Glass cards:** 20px radius, shadow `0 4px 24px rgba(0,0,0,.04)`; 3D "pebble" buttons with bottom-edge lip; hover scale 1.02.
- **Signature spring easing:** `cubic-bezier(0.16, 1, 0.3, 1)` — used for ALL reveals to match product feel.
- **Living backdrop:** breathing aurora mesh + floating blobs (recreated in Remotion using the real gradient stops), variant color per category (blue/purple/gold/teal).

### 4.3 Pacing (Apple-influenced)
- **Slow, confident spring reveals** for the solution/hero beats (let the hero shot breathe).
- **Faster, beat-synced cuts** for the problem-agitation and game montage.
- **Dark-first** open (dark shots photograph best; red pops on near-black), warming into light for game/reflection beats, back to red for the CTA.

## 5. Storyboard — ~72s @ 30fps

Built on the proven 6-beat conversion arc (Hook → Problem → Solution → Demo → Proof → one CTA). Uzbek captions are **drafts pending native proofread** (see Risks).

| # | Time | Frames | Beat | Uzbek caption (draft) | English gloss | Visual / shots |
|---|------|--------|------|------------------------|---------------|----------------|
| 0 | 0:00–0:05 | 0–150 | **Hook** | "Uy vazifasidan o'quvchilar bezgan. Tekshiruvdan o'qituvchilar charchagan." | Students are tired of homework. Teachers are exhausted by grading. | Dark canvas, living-aurora breathing; words punch in on the beat; a faint red spark |
| 1 | 0:05–0:17 | 150–510 | **Problem** | "Jonsiz varaqalar. Ko'chirilgan javoblar. Juda kech keladigan izoh." → "Yaxshiroq yo'l bor." | Lifeless worksheets. Copied answers. Feedback that comes too late. → There's a better way. | Desaturated doc shapes + slow clock; type-driven; ends on a smash-cut |
| 2 | 0:17–0:29 | 510–870 | **Solution reveal** | "Class A Education bilan tanishing." / "Har bir dars — qiziqarli o'yinga aylanadi." | Meet Class A Education. / Every lesson becomes an engaging game. | RED brand wash; `<ClassALogo>` assembles (A draws, sparkle twinkles); wordmark; then Hub hero (`hub-r2-darkOS`) rises in a browser frame as red→blue transition |
| 3 | 0:29–0:40 | 870–1200 | **Demo · Teacher** | "Daqiqalar ichida tayyorlang. Kod kerak emas." / "Bitta havola orqali ulashing." / "Avtomatik baholanadi." | Build in minutes. No code. / Share with one link. / Auto-graded. | `f6-builder-editor` in a laptop frame; `/h/{id}` link pill copies → flies to phone devices |
| 4 | 0:40–0:53 | 1200–1590 | **Demo · Student (core)** | "O'quvchilar bajarishni istaydigan 8 xil o'yin." / "Har bir javob — shu zahoti baholanadi." | 8 game arcs students want to finish. / Every answer graded instantly. | Native hub **unlock choreography** (gray→shake→chain-snap→glow burst, real 3700ms timings) → beat-synced montage: Tile Match (`f4-practice-arc`), 6-game pipeline (`final-arc-darkOS`), TTT, Mystery Box; backdrop shifts purple/gold/teal |
| 5 | 0:53–1:00 | 1590–1800 | **Demo · AI tutor** | "Jonli AI-repetitor: yo'l ko'rsatadi, javobni aytmaydi." / chips: "Tanishuv · Mashq · Boss" | Live AI tutor: guides, never gives the answer. / Preview · Practice · Boss | `f5-tutor-open`/`f5-tutor-reply`; a reply types in; 3 mode chips |
| 6 | 1:00–1:07 | 1800–2010 | **Outcomes + integrity** | "AI-bossni yenging." / "Nimani o'zlashtirganini aniq ko'ring." / "Halol mehnat — beozor nazorat." | Beat the AI boss. / See exactly what they mastered. / Honest work, gently enforced. | Triad: `f4-boss-arena` → `reflection-debrief` (88%) → integrity nudge |
| 7 | 1:07–1:13 | 2010–2100 (approx) | **Proof** | "3 til · 8 o'yin turi · O'rnatish shart emas · 2 soniyada AI baholash" | 3 languages · 8 game types · No install · <2s AI grading | Count-ups on token cards over brand gradient |
| 8 | 1:13–1:18 | 2100–2160 | **One CTA** | "Class A Education'ni maktabingizga olib keling." / "Demo uchun bog'laning" + URL | Bring Class A Education to your school. / Book a demo. | RED canvas; wordmark center; sparkle settles; music resolves; fade |

(Exact per-scene frame boundaries are finalized in the implementation plan; total tuned to ~2160f.)

## 6. Technical architecture

New project at **`marketing/`** (isolated from `frontend/app` — does not touch the frozen `content_json` schema, runtime template, or its deps).

```
marketing/
  package.json            # remotion, @remotion/cli, @remotion/renderer, react, react-dom, typescript
  remotion.config.ts
  tsconfig.json
  public/
    shots/                # selected screenshots copied from docs/screenshots/
    brand/                # (optional) exact logo PNG drop-in
    audio/                # CC0 music bed
    fonts/                # Onest / Fredoka / Nunito (woff2) if not via @remotion/google-fonts
  src/
    index.ts              # registerRoot
    Root.tsx              # <Composition id="ClassAMarketing" ...> parameterized (w/h/fps/lang)
    theme/tokens.ts       # BRAND_RED, product blue, gradients, SPRING easing, type, durations  <-- SHARED CONTRACT
    copy/uz.ts            # all Uzbek caption strings (one place to proofread/swap)
    components/
      ClassALogo.tsx      # animatable vector logo (A + sparkle)
      Wordmark.tsx
      KineticText.tsx     # word-by-word spring caption primitive
      DeviceFrame.tsx     # browser/laptop/phone frames for screenshots (<Img staticFile>)
      LivingBackdrop.tsx  # aurora + blobs, variant color prop
      ProofCard.tsx, ModeChip.tsx, etc.
    scenes/
      Scene0Hook.tsx ... Scene8CTA.tsx   # FILE-DISJOINT -> parallel build
    Marketing.tsx         # the master sequence: stitches scenes via <Sequence from/durationInFrames>
    music.ts              # beat-map / cut points
```

### Key Remotion rules (from docs)
- All motion driven by `useCurrentFrame()` (deterministic export; never `Date.now`/`setTimeout`).
- `spring()` → `interpolate(..., {extrapolateLeft:'clamp', extrapolateRight:'clamp'})` for reveals.
- Per-beat timing via `<Sequence from durationInFrames>` (shifts child frame to 0).
- Screenshots via `<Img src={staticFile(...)}>` (waits for load → **no flicker**; never CSS `background-image` for content).
- Audio via `<Audio src={staticFile(...)}>`; cuts aligned to the track's beat hits.

## 7. Build plan (foundation → fan-out → integrate)

1. **Foundation (orchestrator, critical path):** scaffold project, `npm install`, write `theme/tokens.ts` + `copy/uz.ts` + shared components (`ClassALogo`, `KineticText`, `DeviceFrame`, `LivingBackdrop`, `Wordmark`), register `<Composition>`, copy the ~15 hero screenshots into `public/shots/`, wire fonts, source + place music. This is the **frozen contract** the swarm builds against.
2. **Fan-out (parallel sub-agents, file-disjoint):** ~4 agents, each owning a cluster of `src/scenes/SceneN*.tsx`, building strictly against the token/component contract (fps, dims, easing, caption source). Batched 3–5 at a time per the swarm playbook.
3. **Integrate + verify (orchestrator):** stitch scenes into `Marketing.tsx`, tune frame boundaries & beat-sync, run `remotion studio` headless frame-grabs (screenshot key frames per beat) to verify look against the design, fix.
4. **Render:** `npx remotion render ClassAMarketing out/classa-marketing-72s.mp4` (H.264; auto-downloads headless Chromium; a few minutes). Report duration/size/any warnings.

## 8. Music sourcing
- Source one CC0/royalty-free modern-tech track from Pixabay Music / Mixkit / Chosic (CC0 filter) / YouTube Audio Library.
- Trim to ~72s, place in `public/audio/`, beat-map the cut points.
- **Risk/fallback:** if the file can't be fetched with a clean license programmatically, the MP4 ships silent with a documented one-line swap path — we will **not** ship an unlicensed track.

## 9. Risks & flags
- **Uzbek copy quality (HIGH-VALUE):** marketing tone in Uzbek is high-stakes for a school pitch. Captions in §5 are solid drafts but should be **proofread by a native speaker** (the owner) before final render. All strings live in `src/copy/uz.ts` for a fast pass.
- **Exact brand red / logo fidelity:** vector recreation matched by eye; owner can drop exact hex or the PNG for pixel-perfect.
- **Render toolchain:** Remotion render needs headless Chromium (auto-download) + several minutes on Windows; flicker mitigations (`<Img>`, `--concurrency=1` if needed) applied.
- **Screenshot resolution:** some hero shots are mobile-framed; we composite in device frames so native res reads as intentional, not stretched.

## 10. Acceptance criteria
- [ ] `marketing/` project builds and `remotion studio` opens with no console errors.
- [ ] All 9 scenes render; total ≈72s; captions Uzbek; brand = Class A red + A✦ mark.
- [ ] Real product screenshots composited cleanly (no flicker, no stretch).
- [ ] Music bed present (or documented-silent fallback) with cuts roughly beat-aligned.
- [ ] `out/classa-marketing-72s.mp4` produced (1920×1080, H.264) and spot-checked frame-by-frame against the storyboard.
- [ ] Uzbek copy flagged to owner for proofread before "final" sign-off.

## 11. Out of scope (this pass)
- 9:16 / 1:1 derivative cuts (composition is parameterized to make these cheap follow-ups).
- Voiceover/TTS narration.
- Embedding into the product site / any deploy.
- Changes to product code, schema, or the runtime template.
