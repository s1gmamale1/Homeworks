# Enterprise AI Architecture & Prompting — Part 2
## Twin's Edits, Additions, and Pushback
### 2026-05-07

> **What this is:** Your Part 1 doc is solid — I'm not overwriting it. This is a companion file with (a) one *critical* update that ages your Klarna section, (b) two new verified case studies that are stronger evidence than what you have, (c) sources you missed, and (d) honest pushback on a few of your claims. Stack this on top of your original.
>
> **My confidence levels** (same scheme you used):
> - **Verified** = first-party engineering blog or official customer story / docs
> - **Vendor-reported** = published by vendor or customer, useful direction but not independent
> - **Inference** = my reading of public material, not a direct quote
> - **Opinion** = my call, marked as such

---

## 0. TL;DR of the Edits

| # | Change | Severity |
|---|---|---|
| A | **Klarna update** — they walked the AI strategy back in May 2025. Treat the original "700 agents" number as a cautionary tale, not a success story. | Critical — your doc reads as outdated without this. |
| B | **DoorDash case study added** — best public technical writeup of an LLM support system in production (RAG + two-tier guardrails + simulation flywheel). | Major addition. |
| C | **Uber GenAI Gateway added** — concrete model gateway architecture from a company with 60+ LLM use cases. Strengthens your §3.3 "model gateway" claim with a real example. | Major addition. |
| D | **Anthropic publishes system prompts** — your doc says prompts are usually private. Mostly true, but Anthropic ships Claude's system prompts in release notes, and the CL4R1T4S GitHub repo archives leaked prompts from ChatGPT, Cursor, Replit, Lovable, etc. This is a *primary source* for prompt construction patterns and you should mine it. | Major addition. |
| E | **OWASP Top 10 for LLMs 2025** — your security section talks about NIST/ISO but skips the framework most teams actually use day-to-day for LLM security. Add it. | Medium. |
| F | **Conversation simulators / synthetic eval** — DoorDash and others have published this pattern. Your evals section (§8) doesn't cover it. | Medium. |
| G | **Pushback on a few of your claims** — see §F below. | Minor. |
| H | **Self-critique** — what I might be wrong about. | Required honesty. |

---

## A. CRITICAL UPDATE: The Klarna Story Aged Badly

**Status:** **Verified via multiple outlets quoting Klarna's CEO.**

Your §2.1 frames Klarna as proof that LLM support can operate at high volume. That framing was reasonable in early 2024. By May 2025 the story had reversed publicly.

What actually happened, in order:

1. **Feb 2024** — Klarna and OpenAI publish the now-famous numbers: AI assistant handling 2.3M conversations, equivalent of 700 full-time agents, 35+ languages, $40M projected profit improvement.<sup>[a1]</sup>
2. **Through 2024** — Klarna runs a complete hiring freeze, headcount drops from ~5,500 to ~3,400. CEO Sebastian Siemiatkowski tells Bloomberg in Dec 2024 that "AI can already do all of the jobs that we, as humans, do."<sup>[a2]</sup>
3. **May 2025** — Same CEO, also to Bloomberg: "Cost, unfortunately, seems to have been a too predominant evaluation factor when organising this. What you end up having is lower quality." Klarna announces it is hiring humans again, starting with an "Uber-style" gig model for remote support agents.<sup>[a3]</sup>
4. **Sep–Oct 2025** — After Klarna's US IPO, the company formally restores human staffing in customer service, citing customer dissatisfaction and the AI's inability to handle nuanced/empathetic cases.<sup>[a4]</sup>
5. **Industry-wide echo** — IBM's 2025 CEO survey: only ~25% of enterprise AI projects deliver promised ROI; only ~16% scale across the org.<sup>[a5]</sup>

### What this changes about your doc

**§2.1 Klarna section** — keep the architecture read (it's still accurate as a description of what they *built*), but reframe the lesson. Currently your doc says:

> "Klarna is useful as proof that LLM support can operate at high volume when wired into real backend systems."

I'd rewrite it to:

> "Klarna is useful as a **two-part case study**. Part 1 (2024): an LLM support system *can* operate at high volume across 35+ languages with real backend integration. Part 2 (2025): high volume is not the same as quality. After ~12+ months of running the AI-first model, Klarna's CEO publicly stated the cost-first framing produced lower quality, and the company began rebuilding a human layer. The lagging indicator (CSAT, retention, brand) caught up to the leading indicator (deflection rate, cost) about a year later."

This is actually the *most useful* version of the Klarna story for someone building a support bot in 2026: you get the architecture lessons *and* the warning about what to measure.

### Operational rule I'd add to your doc

**Inference + Opinion:** Build a *satisfaction floor gate* before publicly attributing savings to AI. Concretely:

- Track CSAT, reopen rate, repeat-contact rate, and cancellation rate **per channel** (AI-only, AI+human, human-only) for at least 6 months before the savings number ships in any deck.
- If CSAT moves more than ~5 points down vs human baseline, the deflection number is borrowed from future revenue. Don't ship the press release.
- Model the lag: customer dissatisfaction takes 6–12 months to show up in retention, 12–18 months to correlate with revenue. Most AI rollout celebrations happen at month 2.

---

## B. NEW CASE STUDY: DoorDash Support — RAG + Guardrails + Simulation Flywheel

**Status:** **Verified via DoorDash engineering blog (multiple posts) and InfoQ coverage.** This is the strongest publicly documented LLM support architecture I know of.

### What they replaced
A traditional decision-tree workflow system. DoorDash engineers explicitly say LLMs achieved "higher-quality resolutions than deterministic workflows could because they are more flexible and conversational, allowing them to make human-like decisions beyond the capabilities of our previous system."<sup>[b1]</sup>

### Architecture pattern (verified from blogs)

```text
Dasher / Customer message
        ↓
Conversational AI agent (LLM)
        ↓
RAG over knowledge-base articles
        ↓
LLM Guardrail (real-time, two-tier)
   - Tier 1: cheap fast checks
   - Tier 2: deeper checks if Tier 1 flags
        ↓
LLM Judge (offline / sampled online quality monitoring)
   - 5 quality dimensions
        ↓
Response to user OR escalation to human
        ↓
Knowledge-base auto-improvement
   - Cluster failed conversations
   - LLM drafts new KB articles from clusters
   - Human reviewer approves
```

### Numbers reported by DoorDash

- **~90% reduction in hallucinations** after guardrail deployment.<sup>[b2]</sup>
- **~99% reduction in severe compliance issues.**<sup>[b2]</sup>
- Simulation flywheel runs **hundreds of synthetic multi-turn conversations in minutes** before any prompt change ships.<sup>[b1]</sup>

### The simulation flywheel — this is what your §8 (Evaluation) is missing

DoorDash built an **AI-driven conversation simulator**: an LLM plays the customer with realistic pushback, frustration, clarifying questions; the production chatbot responds; a separate LLM-as-judge framework grades the multi-turn outcome.<sup>[b3]</sup>

The flywheel loop:

1. Engineer identifies a failure mode from production transcripts.
2. Engineer writes an LLM-as-judge eval calibrated against human ratings.
3. Simulator generates hundreds of synthetic conversations covering that failure mode.
4. Engineer iterates on prompts / context / tools until pass rate clears threshold.
5. Full guardrail suite runs as a pre-deploy gate.
6. Production traces feed step 1 next round.

**Why this matters for your doc:** your §8.2 lists "golden test set" and "human review" but doesn't mention *synthetic multi-turn conversation simulation*, which is the only way to test agent behavior at scale before real customers see it. Add it as a row.

### Knowledge base self-maintenance — also useful pattern

DoorDash uses clustering + LLMs to *auto-draft new KB articles* from gaps in existing coverage, then routes them to a human review queue.<sup>[b4]</sup> The model surfaces policy parameters, conditional paths, and privacy redactions inside the draft so reviewers can split or annotate.

This is the inverse of your §3.4 RAG ingestion pipeline — instead of waiting for humans to write content for the index, the system mines the support transcripts to discover what's missing.

---

## C. NEW CASE STUDY: Uber GenAI Gateway — A Real Model Gateway in the Wild

**Status:** **Verified via Uber engineering blog.**

Your §3.3 talks about the "model gateway" pattern abstractly. Uber published a concrete one. Worth name-dropping in your doc as a verified example.

### Key facts

- **60+ LLM use cases** identified across Uber, ranging from process automation to customer support to content generation.<sup>[c1]</sup>
- The gateway is a **Go service** that wraps third-party vendors (OpenAI, Vertex AI, etc.) and Uber-hosted open-source models (Llama, Mixtral) behind a unified interface.<sup>[c1]</sup>
- **Mirrors the OpenAI HTTP/JSON API** as the public contract — chosen specifically because the open-source ecosystem aligns with that interface.<sup>[c1]</sup>
- Includes a **PII redactor** at the gateway layer, security review, and budgeting/usage attribution per team.<sup>[c1]</sup>

### Architecture (from Uber's diagrams + my reading)

```text
Internal product team
        ↓
GenAI Gateway (Go service, OpenAI-compatible HTTP/JSON)
   - Auth & team attribution
   - PII redactor
   - Usage / budget tracking
   - Security review gate at onboarding
        ↓
Provider clients
   - OpenAI fork
   - Vertex AI client (Uber open-sourced this)
   - Uber-hosted Llama/Mistral via Michelangelo
        ↓
Selected model
        ↓
Response back through gateway → product team
```

### What to learn (Opinion)

The "OpenAI-API-compatible" choice is the most reusable lesson. Whatever gateway you build, mirror the most-targeted public API — your downstream code should work with `OPENAI_BASE_URL=...` style env-var swaps. This is also how LiteLLM, vLLM, Bedrock's OpenAI-compatible endpoints, and most internal gateways at other companies converged. Don't invent a proprietary interface.

### Companion: Michelangelo for LLMOps

Uber extended their existing ML platform Michelangelo with LLMOps capabilities: prompt registry with version control, fine-tuning data prep, evaluation framework, in-house Ray-based trainer, model parallelism for >4B-parameter fine-tuning.<sup>[c2]</sup> This is a relevant reference for your §6 Prompt Management — Uber's "Prompt Engineering Toolkit" stores prompt templates centrally with code-review-style governance.

---

## D. NEW SECTION: Public System Prompts — A Source Your Doc Skipped

Your §1 says exact production prompts are usually not published. Mostly true — but you missed the most useful exceptions.

### D.1 Anthropic publishes Claude's system prompts officially

**Status:** **Verified.** Anthropic posts the system prompts for Claude.ai web/mobile in their release notes for each model version (e.g., Claude Opus 4 / Sonnet 4 / Opus 4.7).<sup>[d1][d2]</sup> They don't publish the *tool prompts* — Simon Willison and others have noted this gap and the leaked prompts fill it.<sup>[d3]</sup>

What's actually inside a published Claude system prompt (paraphrased from the public material):
- Identity, model family, current date
- Behavioral defaults (tone, refusal style, hedging style)
- Sensitive-topic handling (legal, medical, mental health, political, child safety)
- Tool use rules
- File and search behavior
- Memory and continuity rules
- Formatting rules

**Why this matters for your prompt-construction section (§4):** these are the most polished publicly-released system prompts in the industry. They show, at frontier-model scale, how to layer (a) identity, (b) behavioral norms, (c) safety carve-outs, (d) tool rules, (e) formatting rules in a single artifact. Even if you don't use Claude, the *structure* is a reference design.

### D.2 The CL4R1T4S archive — leaked prompts from everyone else

**Status:** **Real, controversial, useful.** A GitHub repository at `elder-plinius/CL4R1T4S` archives extracted/leaked system prompts from ChatGPT, Gemini, Grok, Perplexity, Cursor, Lovable, Replit, and others.<sup>[d4]</sup>

**Caveats:** these are *extracted*, not officially published. They can be partial, slightly outdated, and the legal/ethical status is debated. **Opinion:** treat them as field intel, not gospel. The patterns repeat enough across the archive that the patterns themselves are reliable even if any single leak is approximate.

### D.3 OWASP LLM07:2025 — System Prompt Leakage

A direct consequence of the above: OWASP's 2025 Top 10 added **LLM07: System Prompt Leakage** as a new category, separate from prompt injection.<sup>[d5]</sup> The risk isn't just the prompt being public — it's that prompts often contain credentials, internal API endpoints, tenant identifiers, or business rules that shouldn't be there.

**Rule for your prompts:**
- Never put secrets in a system prompt. Pass them server-side and have the tool layer attach them to outbound calls.
- Assume the system prompt *will* leak. Design it so leakage is embarrassing but not catastrophic.
- Don't hardcode tenant identifiers — pass them via runtime context.

### D.4 Prompt patterns I see repeated across published / leaked prompts

These are common shapes, abstracted from the public corpus (verified prompts where available, leaked otherwise):

| Pattern | Where I see it | Purpose |
|---|---|---|
| Identity + date prelude | Claude, ChatGPT, Cursor, Lovable | Anchor the model to current time and product identity |
| XML-ish section tags | Claude system prompts heavily; Cursor; Lovable | Delimit role / scope / rules / context unambiguously |
| "Trust ladder" — system > tools > retrieved > user | Claude, Cursor | Defends against prompt injection in retrieved content |
| Refusal style + recovery | Claude (extensive), ChatGPT (lighter) | Avoid abrupt refusals; offer alternatives |
| Negative examples | Lovable, Cursor | Show what NOT to do — surprisingly common, even though some prompt guides advise against negatives |
| Tool-use carveouts ("use this tool when…") | All | Reduce over- and under-tool-calling |
| Formatting hard rules | Claude (extensive — bullets, emphasis) | Keep voice consistent across millions of users |
| End-with-user-message | Universal | Recency bias means user message at the end gets followed best |

**Inference:** the consistency of these patterns suggests convergent evolution. If a brand-new team in 2026 builds a fresh prompt without these patterns, they're going to rediscover them painfully. Save the time.

---

## E. NEW SECTION: OWASP Top 10 for LLMs 2025 — The Security Framework You're Missing

Your §7 Security mentions NIST/ISO governance frameworks. Both are real, but the framework most security teams actually reference for LLM-specific threats is the **OWASP Top 10 for LLM Applications** (2025 version).<sup>[e1]</sup>

### The 2025 list

| # | Risk | One-liner |
|---|---|---|
| LLM01 | Prompt Injection | Direct + indirect (the latter via retrieved docs / tool outputs / user-uploaded files). Still ranked #1. |
| LLM02 | Sensitive Information Disclosure | Jumped from #6 to #2 after real-world data leaks. |
| LLM03 | Supply Chain | Compromised model weights, poisoned datasets, malicious fine-tunes. |
| LLM04 | Data and Model Poisoning | Includes both training-time and RAG-time poisoning. |
| LLM05 | Improper Output Handling | LLM output passed unsanitized to other systems → XSS, RCE, SQLi. |
| LLM06 | Excessive Agency | Tools have too much permission / autonomy / scope. |
| LLM07 | **System Prompt Leakage** (NEW) | Prompts containing secrets / business logic get extracted. |
| LLM08 | **Vector and Embedding Weaknesses** (NEW) | RAG-specific: cross-tenant leakage, poisoning, embedding inversion. |
| LLM09 | Misinformation | Replaces "Overreliance"; expanded to include hallucination consequences. |
| LLM10 | Unbounded Consumption | Resource exhaustion / cost attacks / model theft. |

### Why this changes your doc

Your §7.2 has good practical rules but it's organized around what you should do, not the threats. Pair it with this list and you get a defense-in-depth model that maps to a published industry framework.

**Strong recommendation (Opinion):** for any vendor / customer who asks "how do you handle AI security?" — answer with OWASP LLM Top 10 mapping. It's the closest thing to a common language the field has, and security teams already know the OWASP brand from the regular Top 10 webapp list.

---

## F. THINGS LACKING IN YOUR DOC

These are gaps I'd fill regardless of the new case studies.

### F.1 Conversation simulation as an eval method

Your §8.2 lists evals: golden set, human review, LLM-as-judge, citation checker, tool checker, conversation outcome, safety eval. **Missing: synthetic conversation simulator** (per DoorDash). Add as a row:

| Eval type | Use |
|---|---|
| Synthetic conversation simulator | Multi-turn agent testing at scale before deploy. LLM plays customer with pushback/frustration; production chatbot responds; LLM-as-judge grades outcome. Catches turn-taking and recovery failures that single-turn evals miss. |

This is the single most underused eval pattern at small/mid teams. It's also the best defense against the "demo passes, prod fails" failure mode.

### F.2 Multi-agent / orchestrator patterns

Your §3.1 architecture diagram has an "Orchestrator (single agent loop OR manager + specialist agents)" line but doesn't go into when to choose which. **Opinion-based field guide:**

| Pattern | Use when | Don't use when |
|---|---|---|
| Single-prompt agent | <5 tools, 1–2 turn workflows, classification + answer. | Long-horizon tasks; ambiguous tool selection. |
| Single agent with tool loop | Most chatbots. RAG + a few backend tools + escalation. | Tasks requiring true parallel work. |
| Manager + specialist agents | Long-horizon research, code review, multi-domain tasks (billing + technical + legal). | Latency-sensitive UX (each layer adds round trips and tokens). |
| Reflection / critic loop | High-stakes outputs (compliance, legal, financial). | Casual chat (kills latency for marginal gain). |
| Plan → execute → verify | Tasks with clear sub-steps and verifiable results. | Open-ended creative tasks. |

**Specific pitfall:** manager-worker setups are *seductive* in design docs and brutal in production — they multiply tokens, latency, and failure surface. Default to single-agent unless you have a real reason. Coinbase's CB-GPT and Uber's gateway both expose multiple use-case-specific bots, not multi-agent monsters per use case.

### F.3 "Context engineering" as a discipline

The field is quietly pivoting from "prompt engineering" to "context engineering." Same idea: the model isn't being instructed; it's being *configured by what's in its context window* — system prompt, tool schemas, retrieved snippets, conversation summary, tool results.

DoorDash's blog post on hallucination reduction explicitly attributes the win to **context engineering improvements**, not model swaps.<sup>[b3]</sup> This matches what I see across other published stories.

**Practical rules I'd add to your §4:**
- Treat the context window as a budget, not a bucket. Every token that's not load-bearing is taking attention away from the load-bearing ones.
- Retrieved snippets at the wrong position get ignored. Anthropic's own prompting docs note that information at the start and end of a long prompt is recalled better than the middle. Put the most critical instructions at the top and re-state the question at the bottom.
- Tool result summaries beat raw tool dumps. If a tool returns 4KB of JSON, summarize it into the 200 bytes the model needs before next turn.
- When summarization is unsafe (e.g., compliance review), pass full data + tell the model exactly what to look for.

### F.4 Prompt drift / decay in production

Not in your doc anywhere. Real phenomenon, important enough to warrant its own subsection:

- **Model-side drift** — provider ships a new model version, behavior on edge cases changes. Mitigation: pin model versions; run regression evals on every provider release.
- **Data-side drift** — new policy docs, new product features, new edge-case tickets. Old prompt examples become stale or contradicted. Mitigation: prompt versions tied to retrieval index versions.
- **User-side drift** — user phrasing shifts as the product changes (new features, new errors, new jargon). Mitigation: weekly sample of low-confidence transcripts for human review; feed those back into eval set.
- **Prompt-side drift** — engineers patch the prompt for one bug, regress on another. Mitigation: every prompt change → eval suite → canary in staging → 5% production canary → 100%.

**Opinion:** if you're not running regression evals weekly, you're flying blind. Klarna's reversal is partially a story of prompt/system drift outpacing measurement.

### F.5 The "70% problem" — why most AI projects fail to scale

The IBM 2025 CEO survey: ~75% of AI projects don't deliver promised ROI; only ~16% scale across the org.<sup>[a5]</sup> Common failure modes I've seen documented:

1. **Demo on cherry-picked queries** — the team picks 50 happy-path examples; production has 50,000 long-tail edge cases.
2. **No clear success metric** — "improve customer support" instead of "reduce L1 ticket resolution time by 30%."
3. **Replaces the human, doesn't help the human** — fully-autopilot is harder than copilot. Coinbase's Agent Assist works because it augments humans first.
4. **Cost dashboard but no quality dashboard** — see Klarna.
5. **Built once, never maintained** — prompts treated as one-time setup, not ongoing product.
6. **No handoff design** — escalations go to humans without context, humans repeat the bot's questions, customer rage-quits.
7. **Stale embeddings** — order/account state in the vector store, not behind tools. Goes wrong silently.

If your doc is going to be a guide for someone building this, list these failure modes explicitly.

---

## G. PUSHBACK ON YOUR DOC

Things I'd argue with, even after your good corrections.

### G.1 "RAG is for knowledge. Tools are for live state." — directionally right, slightly oversimplified

You wrote this as a strong rule (§3.4 and §14). It's mostly correct, but real systems often blur the line:

- **Hybrid retrieval** — many production systems retrieve *both* a policy snippet (RAG) *and* a live tool result (API), then ground the answer on both. Don't frame these as either/or.
- **Cached tool results** — for read-heavy queries (e.g., "what are your business hours?"), running a tool every time wastes latency and money. A short-TTL cache between tool and prompt is fine. Just expire it correctly.
- **Some "knowledge" is actually live** — pricing pages, promotions, capacity limits. These look like knowledge but are state. Use tools.

Edited rule: "RAG is for *stable* knowledge. Tools are for *changing* state. Some 'knowledge' (price, promo, capacity) is actually state — don't be fooled by the file format."

### G.2 "Never let long LLM work block your main web request thread" — agreed, but you understate the streaming case

Your §3.2 table is good but "streaming sync" should be flagged as the *default* for chat UX. People read at 200–250 wpm; a model streaming at 50 tok/s feels instant even for 30-second total responses. Async should kick in only when there's no human waiting.

### G.3 "Use 100 Q&A evals minimum" being demoted to "heuristic"

You corrected this in your doc (rightly). I'd go further: the right number depends on the failure-mode diversity, not the count. 30 well-distributed adversarial cases >> 300 happy-path cases. The metric to track is **eval-set coverage of production failure modes**, not count.

### G.4 "Compound AI systems"

Your §0 says big companies build a compound AI system, not a single magic prompt. **Strongly agree.** I'd cite the Berkeley AI Research / Databricks framing here — they coined the term "compound AI systems" and it gives the concept a name to point at in conversations with execs.<sup>[g1]</sup>

### G.5 The XML-tag prompt style isn't universal

Your prompt templates use XML-style tags (`<role>`, `<scope>`, `<context>`). This is **Claude-leaning**. OpenAI's models do fine with it but their docs lean toward markdown headers; some teams use a custom delimiter style. Mention that the *structure* matters more than the syntax — pick one and be consistent. Mixing styles in one prompt confuses the model.

---

## H. SELF-CRITIQUE — What I Might Be Wrong About

Honest section. I'm an LLM; I have failure modes worth flagging.

1. **The DoorDash 90% / 99% numbers** are from DoorDash's own engineering blog. Vendor-reported. I treated them as verified because they're first-party engineering, not marketing — but that's still a self-reported number with no independent telemetry. Treat as directionally true, not precise.
2. **My OWASP framing** assumes the 2025 list is stable. The 2026 update may already be in draft. Check `owasp.org/www-project-top-10-for-large-language-model-applications` before quoting in any external doc.
3. **The "model gateway" advice** to mirror the OpenAI API is current as of mid-2026. If a different provider's API becomes dominant, the right answer changes. The principle (mirror the dominant interface) is durable; the specific choice is not.
4. **The Klarna postmortem** has been heavily covered by press; press accounts trim and reshape. Siemiatkowski's quotes are real but I haven't seen a full Klarna engineering postmortem. The *strategic* reversal is verified; the *technical* root cause (was it the prompt? the routing? the lack of escalation? all three?) is not publicly detailed.
5. **My pushback on multi-agent patterns** is opinion-flavored. Some teams have made multi-agent work in production (Anthropic's own Multi-Agent Research System, certain code-agent systems). I still default to single-agent first, but reasonable people disagree.
6. **CL4R1T4S** is a third-party archive. I haven't audited every prompt in it. Patterns are robust across the archive; any individual prompt may be partial or outdated.

---

## I. UPDATED CORRECTIONS TABLE (additions to your §13)

| Claim | Status | Note |
|---|---|---|
| Klarna AI replaced 700 agents successfully | **Aged** | Verified as a 2024 *claim*. **By May 2025**, Klarna publicly walked it back, citing lower quality, and began rehiring humans. Reframe as a two-part lesson, not a success story. |
| Most companies don't publish their production prompts | **Mostly true, important exception** | Anthropic publishes Claude system prompts in release notes; CL4R1T4S archives leaks for ChatGPT, Cursor, Replit, etc. Use these as primary sources. |
| Klarna $40M is "estimated profit improvement" | **Now also**: should carry an asterisk that the strategy was reversed | Even the $40M number is contested in retrospective coverage. |
| "RAG for knowledge, tools for live state" | **Directionally correct, oversimplified** | Some "knowledge" is actually state (prices, promos, capacity). Hybrid retrieval is common. |
| 100 Q&A evals minimum | **Heuristic** (your doc) | Even more so: failure-mode coverage matters more than count. 30 diverse adversarial cases > 300 happy-path. |

---

## J. ADDITIONAL SOURCE REGISTER

Append to your existing source register; numbered to avoid collision.

[^a1]: OpenAI, "Klarna's AI assistant does the work of 700 full-time agents," https://openai.com/index/klarna/ (same as your `[^klarna-openai]`, kept for cross-reference)
[^a2]: Bloomberg / multiple secondary, December 2024 Siemiatkowski statements: "AI can already do all of the jobs that we, as humans, do." Coverage at https://www.entrepreneur.com/business-news/klarna-ceo-reverses-course-by-hiring-more-humans-not-ai/491396
[^a3]: Bloomberg via Fortune, "Klarna plans to hire humans again, as new landmark survey reveals most AI projects fail to deliver," May 9, 2025, https://fortune.com/2025/05/09/klarna-ai-humans-return-on-investment/
[^a4]: MLQ.ai, "Klarna CEO admits aggressive AI job cuts went too far, starts hiring again after US IPO," October 2025, https://mlq.ai/news/klarna-ceo-admits-aggressive-ai-job-cuts-went-too-far-starts-hiring-again-after-us-ipo/
[^a5]: IBM CEO survey 2025 (cited via Fortune coverage at [^a3])
[^b1]: DoorDash Engineering Blog, "A Simulation and Evaluation Flywheel to Develop LLM Chatbots at Scale," January 2026, https://careersatdoordash.com/blog/doordash-simulation-evaluation-flywheel-to-develop-llm-chatbots-at-scale/
[^b2]: ZenML LLMOps Database / DoorDash, "LLM-Based Dasher Support Automation with RAG and Quality Controls," https://www.zenml.io/llmops-database/llm-based-dasher-support-automation-with-rag-and-quality-controls
[^b3]: InfoQ coverage of DoorDash simulation flywheel, https://www.infoq.com/news/2026/03/doordash-llm-chatbot-simulator/
[^b4]: DoorDash Engineering Blog, "A scalable LLM approach to enhancing chatbot knowledge with user-generated content," August 2025, https://careersatdoordash.com/blog/doordash-llm-chatbot-knowledge-with-ugc/
[^c1]: Uber Engineering Blog, "Navigating the LLM Landscape: Uber's Innovation with GenAI Gateway," https://www.uber.com/blog/genai-gateway/
[^c2]: Uber Engineering Blog, "From Predictive to Generative — How Michelangelo Accelerates Uber's AI Journey," https://www.uber.com/blog/from-predictive-to-generative-ai/
[^d1]: Anthropic release notes (system prompts published per model release). Discussed in: Simon Willison, "Highlights from the Claude 4 system prompt," https://simonwillison.net/2025/May/25/claude-4-system-prompt/
[^d2]: Coverage of Anthropic publishing Claude Opus 4.7 system prompt: https://startupfortune.com/anthropic-publishes-claude-system-prompts-setting-new-ai-transparency-bar/
[^d3]: Simon Willison's review of what's *missing* from the published prompts (tool definitions): same source as [^d1]
[^d4]: CL4R1T4S leaked-prompts archive, https://github.com/elder-plinius/CL4R1T4S
[^d5]: OWASP, "OWASP Top 10 for LLM Applications 2025," https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf
[^e1]: same as [^d5]
[^g1]: Berkeley AI Research, "The Shift from Models to Compound AI Systems," https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/

---

## K. The Single Sentence

If your doc deserves one merged thesis after both editions:

> **The chatbot is the costume; the system around it is the actor.** Companies that win at this don't write better prompts — they build better routers, better retrieval, better tools, better guardrails, better evals, better escalation, and they measure quality on a 12-month horizon, not a 2-month one. Klarna built the costume and forgot to hire the actor. DoorDash and Coinbase didn't.
