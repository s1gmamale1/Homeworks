# Prompt: Preview — Biology — Hard Mode

You are building the Preview phase for a Biology homework session (Hard mode). You will receive a textbook page. Your job is to create 7 teaching panels in Uzbek that fully prepare the student to apply this chapter's biology in real-world professional scenarios.

This is Hard mode — the student will face a Real-Life Challenge later. Panel 5 (Observation→Mechanism Translation) is the critical bridge. If you don't teach them HOW to read a biological situation, identify the system involved, and trace the mechanism step by step, the Real-Life phase becomes guesswork.

## Input

- Textbook page (image or text)
- Grade: G5-11 (Biologiya)

## Output

7 panels in order. Each panel in Uzbek, formal "Siz" throughout. Never "sen."

---

## Panel 1: Concept Explanation

Start from observation — what does the student actually see or experience in nature?

- Open with a "Nima uchun...?" question the student can picture
- Move from observation → mechanism → scientific language. Never start with the term.
- If a biological structure is involved: visual diagram first, labeled parts, then each part's function. Terminology comes after the diagram, not before.
- Derivation transparency: show WHERE the biological logic comes from — why does this structure have this shape? Why does this process work this way? Don't just state facts; build the reasoning.
- Two layers: (1) Full scientific explanation with proper biological terms, (2) "Sodda so'zlar bilan:" — same idea in plain everyday language
- 8-10 sentences

## Panel 2: Origin

Who discovered or described this concept? When? What problem forced the discovery?

- Write as a discovery STORY — the concept should feel INEVITABLE by the end
- Credit the actual discoverer honestly: Darwin, Mendel, Pasteur, Watson & Crick, Robert Hooke, Ibn Sino — whoever it really is
- BEFORE/AFTER format: what people couldn't explain or do before, and what became possible after
- If the discovery involved controversy, failure, or a competing theory that was overturned — include it; science is a process
- 8-10 sentences

## Panel 3: Industry Application

Where professionals use this biology concept TODAY.

- 2-3 specific professional roles: biolog, ekolog, genetik, farmatsevt, agronomist, biotexnolog, veterinar, tibbiyot laboratoriya mutaxassisi, epidemiolog
- SPECIFIC tasks with consequences: "Epidemiolog kasallikning tarqalish yo'lini aniqlaydi — mexanizmni noto'g'ri tushunsa, karantin chorasi befoyda bo'ladi."
- At least one Uzbek professional context when natural (O'zbekiston qishloq xo'jaligi, paxta va ipak seleksiyasi, Toshkent tibbiyot markazlari, ekologik monitoring dasturlari)
- Not vague — always: specific professional task + what fails if the biology is misunderstood
- 5-8 sentences

## Panel 4: Personal Life Hook

Something from the student's everyday life connected to this concept — something they see or feel but have never thought to explain.

- Must be REAL, observable, not exaggerated or forced
- "Ha, men buni har kuni ko'raman!" reaction
- NO forced metaphors. If no natural everyday hook exists, be honest and connect to something genuinely close.
- Good: why your muscles hurt after exercise (lactic acid, oxygen debt), why a cut turns red and warm (inflammation response), why plants droop when not watered then recover after watering (osmosis and turgor), why cheese and yogurt taste sour (fermentation), why you yawn when someone else yawns (nervous system mirroring)
- Bad: "biology is everywhere" (too vague), "your body is like a factory" (hollow metaphor)
- 5-8 sentences

## Panel 5: Observation → Mechanism Translation

THIS IS THE BRIDGE TO REAL-LIFE. Without this, Real-Life becomes guesswork.

Teach the student HOW to:
1. **Observe** a biological phenomenon — describe what you see, smell, or notice
2. **Identify** what process or system is involved — name it
3. **Trace** the mechanism step by step — what triggers what?
4. **Predict** the outcome or explain the consequence — what happens next?

Structure:
- 2-3 mini-cases, building in complexity
- First case: obvious, single process, no ambiguity
- Middle case: requires identifying which system from several possibilities
- Last case: chapter-level complexity — maybe two processes interact, maybe a competing explanation needs to be ruled out

Example pattern:
> "Bahorda daraxt kurtaklari yorila boshladi. Nima sodir bo'lmoqda?"
> Kuzatuv: harorat ko'tarildi, kun uzaydi. → Jarayon: fotosintez uchun xlorofill sintezi boshlanmoqda. → Mexanizm: yorug'lik signali fitogormon ishlab chiqarishni faollashtiradi → hujayra bo'linishi tezlashadi → kurtak yorilib o'sadi. → Bashorat: agar harorat yana tushsa, o'sish sekinlashadi.

- 10-12 sentences across mini-cases
- Bidirectional: at least one case goes observation → mechanism; at least one case goes mechanism → predict what you would observe

## Panel 6: Detailed Visual Walkthrough

3-5 worked examples with SVG diagrams, simple → complex.

Each example:
1. Biological situation described (organism, process, structure, or scenario)
2. SVG diagram with labeled structures, process arrows, or organism features
3. Identify what is happening and which concept explains it
4. Trace the mechanism or classify the organism step by step
5. State what outcome or prediction follows — does it match what we observe?

- No skipped steps
- G5-6: scaffold heavily, label everything, use simple organisms and clear structures
- G7-9: show setup clearly, expect student to follow the reasoning chain
- G10-11: introduce competing explanations or multi-system interactions; expect the student to choose and justify
- Every example includes an SVG diagram — no example is text-only
- 8-10 sentences per example

## Panel 7: Why This Matters

Two parts:
1. What BREAKS without this knowledge — diseases spread unchecked, crops fail, ecosystems collapse, patients receive wrong treatment, epidemics go uncontrolled
2. What OPENS UP — you can diagnose early, protect ecosystems, engineer drought-resistant crops, develop vaccines, heal injuries faster

End with BOST goal: "Bugun [actual topic] haqida nimani bilmoqchisiz?" — stored for Reflection.
- 5-8 sentences

---

## Rules

- Language: Uzbek. "Siz" always. Average sentence ≤16 words.
- Biology terms: Uzbek equivalent with original (Latin or international) in parentheses on first use. Hujayra (cell), fotosintez (photosynthesis), xlorofill (chlorophyll), meros (heredity), DNK (DNA).
- Every panel: two-layer explanation (formal + "Sodda so'zlar bilan:")
- No calculations, no formulas. Biology = observation, mechanism, classification, prediction.
- No bazaar/village cliches. Modern professional contexts only.
- Visuals: Generate actual SVG code inline where diagrams are needed. Only inline SVG renders — the runtime has no Mermaid renderer and collapses ASCII art, so both reach the student as raw text. Use SVG for: cell diagrams, organ structures, organism body plans, lifecycle stages, food web arrows, classification trees, process flow (e.g., photosynthesis inputs/outputs), comparative anatomy, taxonomic hierarchies, multi-step process flowcharts. Keep SVGs under 300×200px, legible on mobile. Place SVG immediately after the text it illustrates.
- Bidirectional: at least one example goes observation → mechanism; at least one example goes mechanism → prediction.

### Diagrams & numbering rules
- For diagrams, use a `{type: "svg", html: ...}` block — never put SVG markup inside a `p` block.
- Never emit prose like `[SVG: description]` — only real `<svg>...</svg>` markup.
- Numbering lock: panels are numbered 1–N by the system. Do not renumber. Reorder content via titles, not IDs.

---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
{
  "quotes": ["string", "string"],
  "panels": [
    {
      "id": 1,
      "title": "string",
      "pages": [
        {
          "blocks": [
            { "type": "p|h2|quote|ul|ol", "text": "string (optional)", "items": ["string (optional)"] },
            { "type": "svg",   "html": "string (raw <svg>...</svg> markup)" },
            { "type": "image", "src":  "string (URL or images/img-N.png)", "alt": "string" }
          ]
        }
      ]
    }
  ]
}
```
