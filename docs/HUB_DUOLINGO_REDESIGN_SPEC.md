# Hub Redesign Spec — Duolingo-Flavored Learning Path

> **Scope:** Visual + interaction redesign of the runtime **Learning Hub**
> (`frontend/app/src/runtime/LearningHub.tsx` + `LearningHub.module.css`).
> Replaces the current "plain white cards" (owner: *"very AI-generative, lacks
> style"*) with a stylish, full-screen, mobile-first, Duolingo-flavored set of
> interactive path **nodes** — NOT a grid of boxes.
>
> **This is a build spec. It does not change the data contract, the store, the
> screen routing, or any `data-testid`.** All gate logic stays
> server-authoritative (`gateState.{cbp,mc,practice_arc_unlocked}`). The hub
> still only *renders* state; it never decides unlock.
>
> Status: SPEC ONLY — no app code touched.

---

## 0. What we keep wired (hard constraints — do not break)

These come from `LearningHub.tsx` + `store.ts` and MUST survive the redesign.
Renaming/removing any of these breaks tests or the contract.

| Concern | Current binding | Redesign rule |
|---|---|---|
| Store reads | `useRuntimeStore` → `payload`, `gateState`, `startCbp`, `enterFlashcards`, `enterUnlockGate` | Unchanged. Same selectors. |
| Gate shape | `gateState.cbp` (`CbpGate`), `gateState.mc` (`McGate`), `gateState.practice_arc_unlocked` (`shared/types.ts:140–159`) | Read-only, unchanged. |
| Unlock truth | `gate.practice_arc_unlocked` (boolean, server-set) | The ONLY trigger for the unlock choreography. Client never sets it. |
| MC threshold | `gate.mc.threshold_pct ?? 60` | The "≥60%" copy is data-driven — keep `mcThreshold` variable, never hardcode `60`. |
| **testids** | `screen-hub`, `hub-start-cbp`, `hub-start-fc`, `hub-division-3`, `hub-unlock-gate`, `hub-enter-gate` | **All six preserved** on the same logical elements (see §5 mapping). |
| CBP/MC status | `cbpStatus()` / `mcStatus()` → `notStarted | inProgress | passed` | Reuse as-is to drive node state (locked/active/done). |

> ⚠ **Naming note.** The owner's three divisions are **Case-Study**, **Flash
> cards**, **Homework Practices** (exact names). The current file labels
> Division 1 as *"Real-Life Challenge"* and Division 2 as *"Flashcards + Memory
> Check"*. This spec uses the owner's names — **node titles change to
> "Case-Study" and "Flash cards"** while the underlying actions
> (`startCbp` / `enterFlashcards`) stay identical.

---

## 1. Chosen palette (from `ui-ux-pro-max`)

Source: `ui-ux-pro-max --design-system "gamified education kids learning
playful vibrant"` → style **Claymorphism (Mobile)**, plus the
`--domain color "education playful vibrant"` → **Educational App** palette
(playful indigo + energetic orange, WCAG-adjusted). We fuse that palette with
Duolingo's signature **Owl Green / Feather Blue / Cardinal Red** action colors
so the path reads as a *game*, and keep the repo's `_tokens.css` as the neutral
substrate (Onest, surfaces, spring curve).

### Hub token block (add to top of `LearningHub.module.css` `.shell`)

```css
.shell {
  /* ---- Duolingo-flavored play palette (scoped to the hub only) ---- */
  /* Action / brand greens (Duolingo "Owl Green") */
  --hub-green:        #58CC02;   /* primary node + primary CTA face   */
  --hub-green-edge:   #3CA303;   /* darker bottom-edge (3D shadow)    */
  --hub-green-ring:   #4AAE01;
  /* Feather blue (secondary action / "in progress") */
  --hub-blue:         #1CB0F6;
  --hub-blue-edge:    #1487C4;
  /* Energetic orange (Case-Study accent — from ui-ux-pro-max EA580C) */
  --hub-orange:       #FF9600;
  --hub-orange-edge:  #E08200;
  /* Cardinal red (Boss / danger) */
  --hub-red:          #FF4B4B;
  --hub-red-edge:     #D33A3A;
  /* Legendary / unlock burst (playful indigo→violet, ui-ux-pro-max) */
  --hub-violet:       #7C3AED;
  --hub-violet-soft:  #A78BFA;
  --hub-gold:         #FFC800;   /* completed crown / star            */

  /* Locked (grayed) chain node */
  --hub-locked-face:  #E5E5E5;
  --hub-locked-edge:  #BDBDBD;
  --hub-locked-ink:   #AFAFAF;

  /* Surfaces / ink — keep the contrast contract from the old file */
  --hub-ink:          #1d1d1f;   /* hard ink, never theme-flips       */
  --hub-secondary:    #4B4B4B;   /* Duolingo body gray (darker than 86) */
  --hub-subtle:       #777777;
  --hub-page-top:     #FFFFFF;
  --hub-page-bot:     #F0F4F8;   /* very light cool wash, not pure gray */

  /* Pin the theme-flipping tokens to LIGHT (the prior rejection fix) */
  --v2-text: #1d1d1f; --v2-text-muted: #4B4B4B; --v2-text-subtle: #777777;
}
```

**Contrast check (WCAG AA):** node titles are `--hub-ink` (#1d1d1f) on white →
17:1. White CTA label on `--hub-green` (#58CC02) is large/bold ≥18px 700 → 3:1
class passes for large text; for small labels use `--hub-ink` on green. Locked
ink `#AFAFAF` on `#E5E5E5` is intentionally low-contrast (disabled semantic),
so it carries a **lock icon + text** (`color-not-only`), never color alone.

**Why this palette:** the owner's complaint is "AI-generative, lacks style."
Default-AI hubs read as flat gray cards. Duolingo's energy comes from
**saturated, candy-bright fills used as the node body itself** (not as a 4px top
bar), high-contrast hard ink, and the green = "go" semantic. The ui-ux-pro-max
clay style supplies the *tactile* layer (deep colored bottom-edges + spring
squish) that makes a button feel pressable.

---

## 2. Chosen font

Source: `ui-ux-pro-max --domain typography "playful friendly rounded chunky
bold"` → **"Playful Creative" = Fredoka (display) + Nunito (body)**, with
**Baloo 2** as the kid/education alternate.

**Decision:** **Fredoka** for node titles, big numbers, and the page title;
**Nunito** for body/lead copy and meta. Both are rounded-terminal Google Fonts —
the visual cousins of Duolingo's `din-round` / Feather. The repo's **Onest**
stays as the ultimate fallback so nothing breaks if the web font fails.

```css
/* add near the font import layer (or inline in LearningHub.module.css head) */
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@600;700;800&display=swap');

.shell {
  --font-hub-display: 'Fredoka', var(--font-onest), system-ui, sans-serif;
  --font-hub-body:    'Nunito',  var(--font-onest), system-ui, sans-serif;
}
.pageTitle, .nodeTitle, .nodeNum, .ctaLabel { font-family: var(--font-hub-display); }
.pageSub, .nodeLead, .meta, .lockReq        { font-family: var(--font-hub-body); }
```

**Type scale (Fredoka headings / Nunito body):** Page title `clamp(30px, 7vw,
44px)/700` · Node title `22px/700` · Big node number `clamp(30px,9vw,40px)/700`
· Lead `15px/600 lh1.45` · CTA label `17px/700` · Meta `13px/700`. Body min
16px equivalent honored (lead 15px is supporting copy, not body paragraph). Use
`font-display: swap` (already in import) to avoid FOIT.

---

## 3. Full-screen, mobile-first layout

### 3.1 Mental model (Duolingo "path", not a card grid)

Duolingo's 2022+ home is a **single winding column of pebble-shaped nodes that
snake down the screen** — "pebble-shaped circles in a swirling path moving down
the screen" ([Duolingo blog](https://blog.duolingo.com/new-duolingo-home-screen-design/)).
We adapt that to our 3-step flow: instead of 200 micro-lessons we have **3 big
station nodes** connected by a thick dashed path, top to bottom, gently
left/right offset so the eye travels (not a rigid centered stack).

```
PHONE (mobile-first, ≤ 679px) — vertical winding path, full-bleed
┌──────────────────────────────────┐  ← min-height: 100dvh; safe-area insets
│  ◜ HOMEWORK TITLE (subject pill)  │  sticky-ish header, hero glow behind
│        Topic · Section            │
│   ◆ progress ring  2 / 3 cleared  │  small overall progress chip
│                                    │
│        ╭───────────╮               │
│        │   01      │  ← Case-Study node (orange clay button)
│        │ CASE-STUDY│     offset LEFT, big 3D press button
│        ╰───────────╯               │
│             ┊ (dashed path)        │
│                 ╭───────────╮      │
│                 │   02      │ ← Flash cards node (blue clay)
│                 │FLASH CARDS│    offset RIGHT
│                 ╰───────────╯      │
│             ┊┊ (CHAINED path)      │  ← chain-link motif while locked
│        ╭━━━━━━━━━━━╮               │
│        │ 🔒  03    │  ← Homework Practices — GRAYED, CHAINED node
│        │ HOMEWORK  │     centered, wrapped in chain-links
│        │ PRACTICES │
│        ╰━━━━━━━━━━━╯               │
└──────────────────────────────────┘
  (scrolls within 100dvh; no horizontal scroll)
```

```
TABLET / DESKTOP (≥ 680px) — same path, wider gutters, path amplitude grows
┌────────────────────────────────────────────────────┐
│                 HOMEWORK TITLE · Topic                │  max-width 560px center
│                  ◆ 2 / 3 cleared                      │
│      ╭──────────╮                                     │
│      │ 01 CASE  │  ·····\                             │
│      ╰──────────╯        \····· ╭──────────╮          │
│                                  │ 02 FLASH │          │
│                          /······ ╰──────────╯          │
│            ╭━━━━━━━━━━━━━╮ /                            │
│            │ 🔒 03 PRACTICES │  (chained, centered)    │
│            ╰━━━━━━━━━━━━━╯                              │
└────────────────────────────────────────────────────┘
   max-width 600px column, centered; path stays a single winding column
   (we do NOT switch to a 2-up grid — that would re-introduce "card grid" feel)
```

### 3.2 Structural rules

- **Full-bleed shell:** `min-height: 100dvh` (not `100vh` — `viewport-units`
  rule), `padding-top: max(24px, env(safe-area-inset-top))`,
  `padding-bottom: max(32px, env(safe-area-inset-bottom))`. Background is the
  light cool wash gradient `linear-gradient(180deg, var(--hub-page-top),
  var(--hub-page-bot))`, keeping the existing soft `heroGlow`.
- **Single winding column.** Container `max-width: 600px; margin-inline: auto`.
  Nodes are laid out in a vertical flex column with `gap: clamp(40px, 9vw,
  72px)`. Horizontal offset per node via `align-self` + a small translateX so
  the path *winds*: node 1 left, node 2 right, node 3 center (terminal).
- **The path connector** is the SVG layer (reuse current `FlowConnectors`
  pattern, `viewBox 0 0 1000 1000`, `preserveAspectRatio="none"`), but restyled:
  a **thick (10–12px) dashed/dotted rounded path** in `--hub-locked-edge` for
  locked segments, recoloring to `--hub-green` once a segment's upstream node is
  `passed`. The segment feeding node 3 renders as **chain links** while locked
  (see §4.3).
- **Touch targets:** every node button ≥ 64px tall (well over the 44px min);
  8px+ spacing inherent in the 40px+ path gaps.

---

## 4. Node / button visual design (Duolingo 3D-press)

### 4.1 The signature 3D "press" button

Duolingo's button "uses box-shadow to make the button look slightly raised, and
when you press it, the shadow disappears which makes it feel like the button is
actually being pushed down" — the **box-shadow method** (not border-bottom,
which causes layout shift) is the recommended technique
([Replicating Duolingo's Button in Pure CSS](https://medium.com/@lilskyjuicebytes/clone-the-ui-1-replicating-duolingos-button-in-pure-css-bd37a97edb7e),
[Josh W. Comeau — Magical 3D Button](https://www.joshwcomeau.com/animation/3d-button/)).

The whole **station node IS the big button** (not a card with a small CTA
inside). Each node = a chunky rounded rectangle with a solid candy fill and a
**colored bottom-edge "lip"** rendered as a hard `box-shadow: 0 Npx 0 <edge>`.
On press the node translates down by the lip thickness and the lip collapses —
it depresses like a physical key.

```css
/* Base station node = the pressable 3D button */
.node {
  position: relative;
  display: flex; flex-direction: column;
  width: min(340px, 86vw);
  min-height: 132px;
  padding: 20px 22px;
  border: none;
  border-radius: 26px;                    /* clay: 20–26px */
  color: #ffffff;
  text-align: left;
  cursor: pointer;
  touch-action: manipulation;             /* kills 300ms tap delay */
  /* the 3D lip: 6px solid colored bottom-edge */
  box-shadow: 0 6px 0 var(--node-edge), 0 12px 22px rgba(0,0,0,0.12);
  transition:
    transform 90ms var(--landing-spring),
    box-shadow 90ms var(--landing-spring),
    filter 160ms var(--landing-spring);
  will-change: transform;
}
.node:hover    { filter: brightness(1.04); }
.node:active   {                            /* the depress */
  transform: translateY(6px);
  box-shadow: 0 0 0 var(--node-edge), 0 4px 10px rgba(0,0,0,0.10);
}
.node:focus-visible { outline: 3px solid var(--hub-ink); outline-offset: 4px; }

/* per-node fill + edge (drives the 3D lip color) */
.nodeCase  { background: var(--hub-orange); --node-edge: var(--hub-orange-edge); }
.nodeFlash { background: var(--hub-blue);   --node-edge: var(--hub-blue-edge);  }
.nodeDone  { background: var(--hub-green);  --node-edge: var(--hub-green-edge); } /* passed */
```

> **Important:** because the WHOLE node depresses, `startCbp`/`enterFlashcards`
> move to the node's own `onClick` and the node element becomes a semantic
> `<button>` (or `role="button"` on the `<article>`). Keep the inner `<Button
> data-testid="hub-start-cbp">` as a visually-nested "Start →" affordance OR
> migrate the testid onto the node button itself (see §5). Either way the testid
> stays attached to the element that fires `startCbp`.

### 4.2 Node anatomy & state

Each learning node shows: a **big number badge** (01 / 02) in a frosted circle,
the **title** (Fredoka 700, white), a one-line **lead**, and a **status glyph**
(progress ring / check). State maps off the existing `cbpStatus`/`mcStatus`:

| State | Source | Visual |
|---|---|---|
| `notStarted` | `cbp/mc === "notStarted"` | full-saturation fill, "Start →" affordance, idle **bob** animation to invite the tap |
| `inProgress` | `=== "inProgress"` | same fill + a **progress ring** (conic-gradient) around the number badge showing `score_pct` / checkpoint fraction; label "Continue →" |
| `passed` | `=== "passed"` | recolor to `--hub-green` (`.nodeDone`), a **gold crown/check** stamps in with a small pop; label "Review →" |

**Idle bob** (Duolingo's nodes gently bob to draw the eye to the next action):

```css
@keyframes hubBob {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-5px); }
}
.node.isNext { animation: hubBob 2.4s ease-in-out infinite; }
.node.isNext:active { animation: none; }  /* press wins over bob */
```

Only the **single next actionable node** gets `.isNext` (max 1–2 animated
elements per view — `excessive-motion` rule).

**Progress ring** around the number badge (no layout cost, transform/opacity
only):

```css
.numRing {
  background: conic-gradient(var(--hub-gold) calc(var(--pct) * 1%), rgba(255,255,255,0.25) 0);
  /* --pct set inline from gate.mc.score_pct or checkpoint fraction */
}
```

### 4.3 The locked, CHAINED Homework Practices node

Division 3 is a **single node** rendered as a **grayed-out, chained** 3D button
while `practice_arc_unlocked === false`. It looks heavy and inert — the chains
visually shackle it to the path.

```css
.nodePractices {
  background: var(--hub-locked-face);
  --node-edge: var(--hub-locked-edge);
  color: var(--hub-locked-ink);
  cursor: not-allowed;
  box-shadow: 0 6px 0 var(--hub-locked-edge), 0 8px 16px rgba(0,0,0,0.08);
  filter: grayscale(0.35);
}
.nodePractices:active { transform: none; box-shadow: 0 6px 0 var(--hub-locked-edge); } /* dead press */

/* Chain-link overlay — two diagonal link-chains crossing the node corners.
   Reuse the chain-link visual vocabulary already proven in UnlockGate.module.css
   (the .linkHalf 9px-border rounded squares). */
.chains { position: absolute; inset: -10px; pointer-events: none; z-index: 3; }
.chainLink {
  position: absolute; width: 30px; height: 30px;
  border: 7px solid var(--hub-subtle); border-radius: 12px;
  filter: drop-shadow(0 2px 2px rgba(0,0,0,0.25));
}
/* lay ~4 links across a diagonal padlock band; a central padlock badge sits on top */
.padlock { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); z-index: 4; }
```

The locked node carries:
- A **padlock badge** (existing `LockGlyph`, enlarged) centered on the chain band.
- The three sub-items (Gamified / Interactive / Boss) shown **dimmed** inside
  (preserved from current markup — keeps the "what's behind the lock" preview).
- An inline lock requirement line: `Clear Case-Study & Flash cards (≥{mcThreshold}%) to unlock.`
- A "nudge" shake on click (the locked button never navigates — reuse the
  existing `handleLockedClick` + `hubShake`).

When `practice_arc_unlocked` flips true (and after the choreography in §5
plays), the node swaps to an **unlocked** look: violet→green clay fill
(`--hub-violet` → `--hub-green` gradient), chains gone, padlock replaced by an
open state, and the live `<Button data-testid="hub-enter-gate">Enter Practice
Arc →</Button>` becomes the pressable CTA (calls `enterUnlockGate`).

---

## 5. Unlock choreography (gray-out → shake → chain-break → reveal)

### 5.1 Trigger & play-once state flag

**Trigger condition (read-only, server truth):** the choreography plays exactly
once, the first time the hub mounts/sees `gateState.practice_arc_unlocked ===
true` **AND** it has not played before on this device.

The owner's wording is "after BOTH learning divisions are ≥60% complete." That
threshold is already enforced server-side — when both clear, the server sets
`practice_arc_unlocked = true`. The hub does **not** re-derive 60%; it watches
the boolean. (If a belt-and-suspenders client check is wanted, gate on
`cbpStatus === "passed" && mcStatus === "passed"`, but the boolean is the
contract.)

**Play-once flag** — persist per homework+session in `localStorage` so a refresh
or re-entry doesn't replay the celebration:

```ts
// inside LearningHub.tsx
const unlocked = gate?.practice_arc_unlocked ?? false;
const seenKey = `hub:unlockSeen:${hwId}`;                // hwId from store
const [playUnlock, setPlayUnlock] = useState(false);

useEffect(() => {
  if (!unlocked) return;
  if (localStorage.getItem(seenKey) === "1") return;     // already celebrated
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    localStorage.setItem(seenKey, "1");                  // skip anim, show final
    return;
  }
  setPlayUnlock(true);                                    // arm the sequence
  const done = setTimeout(() => {
    setPlayUnlock(false);
    localStorage.setItem(seenKey, "1");                   // mark seen at sequence end
  }, 3200);                                               // total sequence ms (see §5.2)
  return () => clearTimeout(done);
}, [unlocked, seenKey]);
```

The root `.shell` gets `data-unlock={playUnlock ? "playing" : unlocked ? "open"
: "locked"}` so all keyframes are driven by one attribute (no per-element JS).

### 5.2 The sequence (single timeline, one attribute drives it)

Total ≈ **3.2s**, four beats. All transforms/opacity only (no layout
animation). Each beat is a keyframe scoped under
`.shell[data-unlock="playing"]`.

| Beat | Time | What happens | Mechanism |
|---|---|---|---|
| **1 · Dim** | 0–600ms | Whole hub dims/grays; a scrim fades in; learning nodes desaturate so attention funnels to node 3 | scrim `::after` opacity 0→0.55; `filter: grayscale` ramp on `.entries` |
| **2 · Shake** | 600–1150ms | The locked node 3 **shakes** to signal something's about to happen | `hubUnlockShake` (stronger than the nudge shake) |
| **3 · Chain-break** | 1150–2000ms | Chains **snap apart** — link halves fling outward + rotate, a glow burst + sparks fire at the break point | reuse `snapLeft`/`snapRight`/`burst`/`spark*` from `UnlockGate.module.css` |
| **4 · Reveal** | 2000–3200ms | Scrim lifts, node 3 **un-grays** and pops to its violet→green unlocked fill, gold sparkle, the path segment recolors green, "Enter Practice Arc →" CTA scales in | scrim opacity→0; `hubUnlockReveal` (grayscale→0, scale pop); CTA `hubCtaIn` |

```css
/* ---- scrim that dims the whole hub during the sequence ---- */
.shell::after {
  content: ""; position: fixed; inset: 0; z-index: 50;
  background: rgba(20,24,28,0.0); pointer-events: none;
  transition: background 1s var(--landing-spring);
}
.shell[data-unlock="playing"]::after { animation: hubScrim 3.2s var(--landing-spring) both; }
.shell[data-unlock="playing"] .entries { animation: hubDesat 3.2s var(--landing-spring) both; }

@keyframes hubScrim {
  0%   { background: rgba(20,24,28,0.0); }
  18%  { background: rgba(20,24,28,0.55); }   /* fully dimmed by ~600ms */
  62%  { background: rgba(20,24,28,0.55); }   /* held through the break */
  100% { background: rgba(20,24,28,0.0); }    /* lifts on reveal */
}
@keyframes hubDesat {
  0% { filter: grayscale(0); }
  18%,62% { filter: grayscale(0.85) brightness(0.85); }
  100% { filter: grayscale(0); }
}

/* ---- Beat 2: the shake (delayed to 600ms) ---- */
@keyframes hubUnlockShake {
  0%,100% { transform: translateX(0) translateY(0); }
  10% { transform: translateX(-8px) rotate(-1.5deg); }
  20% { transform: translateX(7px)  rotate(1.2deg); }
  30% { transform: translateX(-6px) rotate(-1deg); }
  40% { transform: translateX(5px)  rotate(0.8deg); }
  50% { transform: translateX(-3px); }
  60% { transform: translateX(2px); }
}
.shell[data-unlock="playing"] .nodePractices {
  animation: hubUnlockShake 0.55s var(--landing-spring) 0.6s 1 both;
}

/* ---- Beat 3: chains snap apart (delay 1.15s) ----
   Reuse the proven snap geometry from UnlockGate.module.css verbatim,
   just retimed. Link halves + burst + sparks live inside .chains. */
.shell[data-unlock="playing"] .chainLinkLeft  { animation: snapLeft  720ms var(--landing-spring) 1.15s both; }
.shell[data-unlock="playing"] .chainLinkRight { animation: snapRight 720ms var(--landing-spring) 1.15s both; }
.shell[data-unlock="playing"] .chainBurst     { animation: burst    1100ms var(--landing-spring) 1.3s both; }
.shell[data-unlock="playing"] .chainSpark1    { animation: spark1    900ms var(--landing-spring) 1.35s both; }
.shell[data-unlock="playing"] .chainSpark2    { animation: spark2    900ms var(--landing-spring) 1.39s both; }
.shell[data-unlock="playing"] .chainSpark3    { animation: spark3    900ms var(--landing-spring) 1.37s both; }
/* snapLeft / snapRight / burst / spark1-3 keyframes: copy from
   UnlockGate.module.css lines 76–182 (already battle-tested + reduced-motion-safe). */

/* ---- Beat 4: node 3 un-grays + pops to unlocked, CTA enters (delay 2.0s) ---- */
@keyframes hubUnlockReveal {
  0%   { filter: grayscale(0.35); transform: scale(1); }
  40%  { filter: grayscale(0);    transform: scale(1.06); }
  70%  { transform: scale(0.985); }
  100% { filter: grayscale(0);    transform: scale(1); }
}
.shell[data-unlock="playing"] .nodePractices {
  /* shake first (above), then reveal — chained via two animations */
  animation:
    hubUnlockShake 0.55s var(--landing-spring) 0.6s 1 both,
    hubUnlockReveal 1.2s var(--landing-spring) 2.0s 1 both;
}
@keyframes hubCtaIn {
  from { opacity: 0; transform: translateY(10px) scale(0.9); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
.shell[data-unlock="playing"] .enterCta { animation: hubCtaIn 0.5s var(--landing-spring) 2.4s both; }
```

After the sequence, `data-unlock` becomes `"open"` (flag persisted) and node 3
renders in its static unlocked style with the live `hub-enter-gate` CTA — no
animation on subsequent visits.

> **Relationship to the existing `UnlockGate` screen.** There is already a
> separate full-screen `UnlockGate.tsx` "moment" reached via `enterUnlockGate`
> (`screen: "gate"`). This spec's choreography is the **in-hub** version the
> owner asked for — it plays on the hub itself. Keep `enterUnlockGate` →
> `UnlockGate` as the *destination* after the student taps "Enter Practice Arc
> →". The two are complementary: hub celebrates the unlock in place; the gate
> screen is the threshold into the arc. **Reuse `UnlockGate.module.css`'s chain
> keyframes** rather than reinventing them.

### 5.3 prefers-reduced-motion fallback

Per the `reduced-motion` rule and the existing `_tokens.css` global reducer
(which already forces `animation-duration: 0.01ms`), add an explicit hub block
so the **final state shows instantly with no shake/snap/scrim**:

```css
@media (prefers-reduced-motion: reduce) {
  .shell[data-unlock="playing"]::after,
  .shell[data-unlock="playing"] .entries,
  .shell[data-unlock="playing"] .nodePractices,
  .shell[data-unlock="playing"] .chainLinkLeft,
  .shell[data-unlock="playing"] .chainLinkRight,
  .shell[data-unlock="playing"] .chainBurst,
  .shell[data-unlock="playing"] .chainSpark1,
  .shell[data-unlock="playing"] .chainSpark2,
  .shell[data-unlock="playing"] .chainSpark3,
  .shell[data-unlock="playing"] .enterCta { animation: none; }
  .node.isNext { animation: none; }                 /* no bob */
  .nodePractices .chains { display: none; }          /* show unlocked state directly */
}
```

The JS in §5.1 also short-circuits (`localStorage` set, `setPlayUnlock`
skipped) when reduced-motion is on, so the unlocked node simply appears.

---

## 6. testid → element mapping (so tests stay green)

| testid | Old element | New element |
|---|---|---|
| `screen-hub` | `<main>` | `<main>` (the `.shell`) — unchanged |
| `hub-start-cbp` | inner `<Button>` in card 1 | the Case-Study node button's primary action (node `onClick={startCbp}`; testid on the pressable element) |
| `hub-start-fc` | inner `<Button>` in card 2 | the Flash cards node button's primary action (`onClick={enterFlashcards}`) |
| `hub-division-3` | `<article>` Practices | the Homework Practices node `<article>` — unchanged |
| `hub-unlock-gate` | `.gateScope` div | the gate-scope wrapper inside node 3 — unchanged, keep `aria-live="polite"` |
| `hub-enter-gate` | unlocked `<Button>` | the unlocked "Enter Practice Arc →" CTA (`onClick={enterUnlockGate}`) — unchanged |

If the node becomes a single `<button>`, attach `hub-start-cbp`/`hub-start-fc`
to that node `<button>` directly (it's the element that fires the action — what
the Playwright tests click). Verify against `tests/` Playwright specs before
finalizing.

---

## 7. Responsive breakpoints

Systematic breakpoints per the `breakpoint-consistency` rule (375 / 768 / 1024 /
1440). Mobile-first base, scale up:

| Width | Behavior |
|---|---|
| **base (≤ 375px)** | Single winding column, node width `min(340px, 86vw)`, path gap `40px`, node offset translateX `±10px`. Hero title `clamp(30px,7vw,44px)`. |
| **≥ 480px** | Node width up to 360px, path amplitude (offset) grows to `±28px` so the winding reads more. |
| **≥ 680px** | Column `max-width: 600px` centered; gaps `clamp(56px,8vw,72px)`; offsets `±48px`; path SVG curve amplitude increases. **Stay a single column — do NOT split into 2-up** (would re-create the rejected card-grid feel). |
| **≥ 1024px** | Same column, larger hero glow, more vertical breathing; node hover `brightness(1.04)` only (no scale that competes with the press). |
| **landscape phone** | `min-height` relaxes; allow the column to scroll; keep the floating "back to current" affordance optional. |

No horizontal scroll at any width (`horizontal-scroll` rule). `touch-action:
manipulation` on all nodes. Safe-area insets on the shell (notch / home
indicator).

---

## 8. Build checklist

**Setup**
- [ ] Worktree off `origin/server`; uvicorn on a free port (8765 / next free).
- [ ] Read the Playwright hub specs in `tests/` to confirm exact testid usage
      before moving any testid onto a new element.

**Tokens & type**
- [ ] Add the `--hub-*` play palette + Fredoka/Nunito import to `.shell` in
      `LearningHub.module.css` (scoped — do not touch global `_tokens.css`).
- [ ] Keep the `--v2-text*` pin-to-light contrast fix.

**Layout**
- [ ] Convert `.entries` 2-up grid → single winding flex column with per-node
      `align-self` + translateX offsets.
- [ ] Restyle `FlowConnectors` SVG: thick dashed path; recolor segments green
      on upstream `passed`; chain-link motif on the locked node-3 segment.
- [ ] `min-height: 100dvh` + safe-area insets on `.shell`.

**Nodes (3D press)**
- [ ] Make each learning node the pressable 3D button (box-shadow lip +
      `:active` depress + `:focus-visible` ring); per-node fill/edge classes.
- [ ] Rename titles to **Case-Study** and **Flash cards**; keep
      `startCbp`/`enterFlashcards` wiring + testids.
- [ ] State styles: notStarted (bob on the single next node), inProgress
      (conic progress ring), passed (green + gold check pop).
- [ ] Locked Practices node: gray clay + chain overlay + padlock + dimmed
      sub-items + nudge-shake on click (no nav).

**Unlock choreography**
- [ ] Add `data-unlock` attribute on `.shell` driven by the §5.1 effect +
      `localStorage` play-once flag (`hub:unlockSeen:{hwId}`).
- [ ] Copy `snapLeft/snapRight/burst/spark1-3` keyframes from
      `UnlockGate.module.css`; add `hubScrim/hubDesat/hubUnlockShake/
      hubUnlockReveal/hubCtaIn`.
- [ ] Wire the 4-beat timeline (dim → shake → chain-break → reveal, ≈3.2s).
- [ ] Unlocked node renders violet→green fill + live `hub-enter-gate` CTA.

**Accessibility & QA**
- [ ] `prefers-reduced-motion`: final state instantly, no shake/snap/scrim/bob
      (§5.3) + JS short-circuit.
- [ ] Locked state uses lock icon + text, not color alone.
- [ ] Touch targets ≥ 44px (nodes are ≥ 64px); `aria-disabled` on locked CTA.
- [ ] WCAG AA contrast on titles/labels (white on green only for large/bold).
- [ ] `python -m pytest tests/ -q` green; Playwright hub specs green.
- [ ] **Launch locally + smoke in a real browser at 375px and ≥768px**, walk
      the unlock: clear both → return to hub → confirm the one-time
      dim→shake→chain-break→reveal plays, then does NOT replay on refresh.
- [ ] Every fix ships a regression test (repo rule) — e.g. assert the play-once
      flag prevents replay, and that all six testids resolve.

---

## 9. Sources

**ui-ux-pro-max skill (local):**
- `~/.claude/skills/ui-ux-pro-max/SKILL.md` — workflow + rule categories
- `--design-system "gamified education kids learning playful vibrant"` →
  Claymorphism (Mobile); palette Educational App / clay
- `--domain color "education playful vibrant"` → playful indigo + energetic
  orange (WCAG-adjusted); `--domain typography "playful friendly rounded chunky
  bold"` → Fredoka + Nunito / Baloo 2
- Data: `data/colors.csv`, `data/typography.csv`, `data/styles.csv`,
  `data/ux-guidelines.csv`

**Duolingo UI/UX:**
- [Introducing the new Duolingo learning path](https://blog.duolingo.com/new-duolingo-home-screen-design/) — winding path of pebble nodes, descriptive unit headers, character/personality, "back to current" floating arrow
- [Replicating Duolingo's Button in Pure CSS (Medium)](https://medium.com/@lilskyjuicebytes/clone-the-ui-1-replicating-duolingos-button-in-pure-css-bd37a97edb7e) — box-shadow 3D-press technique
- [Josh W. Comeau — Building a Magical 3D Button](https://www.joshwcomeau.com/animation/3d-button/) — translateY-on-active depress
- [Making a 3D Button with Haptic Effect like Duolingo (DEV)](https://dev.to/yossabourne/making-3d-button-with-haptic-effect-like-duolingo-in-swiftui-2mj9) — press + haptic feel
- [Duolingo onboarding & UX breakdown (UserGuiding)](https://userguiding.com/blog/duolingo-onboarding-ux) — gamification psychology

**Repo references:**
- `frontend/css/_tokens.css` — Onest, Apple palette, `--grad-*`, spring curve,
  global reduced-motion reducer
- `frontend/app/src/runtime/LearningHub.tsx` + `.module.css` — current hub
- `frontend/app/src/runtime/UnlockGate.module.css` — proven chain-break keyframes
- `frontend/app/src/runtime/store.ts`, `frontend/app/src/shared/types.ts` —
  gate state contract
