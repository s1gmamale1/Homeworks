# NETS — Academic Integrity & Anti-Cheat Research and Mapping

**Purpose:** Maps the academic integrity, anti-cheat, and AI-misuse policies of the three major credential authorities (AP / IB / Cambridge), the standardized testing bodies relevant to Class A's outcome tracks (SAT, IELTS, TOEFL), and the LMS-side detection technology landscape — then connects each piece to how Class A's NETS system should handle the same problems.

**Status:** Research + mapping in one document. Treat the policy recommendations in Section 10 as drafts for the AI Use Matrix work in Issue 1 of the Strategic Issues list, not final decisions.

**Sources:** Project research files (`AP_Advanced_Placement.md`, `IB_International_Baccalaureate.md`, `Cambridge_Assessment_International_Education.md`), plus targeted web research on AP Bluebook 2026 security and Turnitin AI detection accuracy. Gaps noted at end.

---

## 1. The Shape of Anti-Cheat Across the Three Systems

Before going into individual systems, the broader pattern: **none of the three credential authorities relies primarily on detection software for academic integrity.** All three rely primarily on *process supervision* — teacher knowledge of the student, documented checkpoints during work, and authentication of authorship by an adult who has been present throughout the production process. Detection is a fallback, not the primary defense.

This is a deliberate choice and it's well-grounded. The detection-software landscape (Section 6) is unreliable enough that institutions are increasingly stepping back from it, while the process-supervision approach has held up across decades of academic misconduct. For Class A this is significant because the natural instinct of an AI-driven platform is to lean on detection — and the credential authorities are explicitly telling us that's the wrong instinct.

The three systems differ in *how* they implement process supervision, in *what* counts as misconduct, and in *how* they handle AI specifically. Those differences matter for Class A's policy design.

---

## 2. Advanced Placement (College Board)

### 2.1 Defined misconduct

The College Board defines a comprehensive spectrum: copying from other students, using unauthorized materials, accessing electronic devices during testing or breaks, impersonation (taking an exam for another or vice versa), sharing or posting unreleased exam content on social media, using AI in ways prohibited by course-specific policy, attempting to gain prior access to test content, and disabling security features on testing devices.

### 2.2 Sanctions

Severe and immediate: score cancellation for the affected exam, bans from future College Board tests (including the SAT — a significant escalation since this affects college admissions broadly), notification to schools and sometimes to colleges, and criminal prosecution for serious offenses like impersonation or theft of exam materials. The College Board describes itself as using "advanced methods to detect and investigate" — digital forensics and statistical analysis on response patterns.

### 2.3 Process supervision: the AP Capstone checkpoint model

For AP Capstone (Seminar and Research), where AI use is *permitted* as a research aid, the College Board has implemented a **checkpoint and affirmation system** worth studying carefully because it's the most directly transferable to Class A:

- Teachers set in-class or documented checkpoints where students discuss progress
- Teachers affirm, to the best of their knowledge, that submissions are authentic
- Checkpoints include oral defenses, draft submissions, annotated sources, recorded meetings
- Failure to complete checkpoints can result in a score of zero

This is the College Board explicitly saying that *process documentation, not AI detection software, is the most effective safeguard against inappropriate AI use*. It's a substantial signal about where the credential authority thinks anti-cheat should sit.

### 2.4 Digital exam security: AP Bluebook 2026

Most AP exams are now delivered through Bluebook, the College Board's testing application. The 2026 security stack includes:

- Device lockdown and verified mode (prevents unauthorized software, disables tools, restricts extensions, runs continuous integrity checks)
- AI-powered proctoring (webcam and microphone analyzed by AI models during and after the exam)
- Test Day Toolkit for proctors
- Room codes and ID verification
- 28 digital AP exams in 2026 (16 fully digital, 12 hybrid)

New for 2026: smart-glasses guidance for proctors, and Proctor Preview mode. The Terms and Conditions are a legal contract that students accept on exam day. Prohibited explicitly: bypassing Bluebook security features, malware on testing device, internet-capable devices, communication during exam, photos of exam content, social media posts about specific questions within specified timeframes.

### 2.5 Course-specific AI policies

This is AP's distinctive contribution. Rather than a blanket policy, AP differentiates by course:

| AP Course / Program | AI Policy | Key Requirement |
|---|---|---|
| AP Capstone (Seminar & Research) | Permitted as optional aid | Checkpoints with teacher; teacher affirms authenticity |
| AP Computer Science Principles | Permitted as supplementary | Must understand and explain AI-generated code on exams |
| AP Art and Design | **Categorically prohibited** | No AI use at any stage of creative process |
| All other AP courses | Generally not permitted for assessed work | Grammar checking may be allowed; content generation prohibited |

The differentiation matters: AP is saying that what counts as cheating depends on what the discipline values. For Art, the creative process *is* the assessment; AI use destroys the construct. For CSP, AI is an industry tool and engaging with it is part of preparation. This per-discipline thinking should inform Class A's AI Use Matrix.

---

## 3. International Baccalaureate

### 3.1 Defined misconduct

Six categories: plagiarism (using others' words, ideas, or work without proper attribution), collusion (unauthorized collaboration on individual assessments), cheating (using unauthorized materials or assistance during examinations), fabrication (inventing data, sources, or evidence), misconduct during examinations (any behavior that violates examination regulations), and duplication (submitting the same work for multiple assessments).

### 3.2 Sanctions

Severe and escalating. First offense on a minor assignment typically results in a warning, required resubmission, and educational intervention about citation. Second offense (or first offense on major components like Extended Essay, TOK essay, or final examinations) triggers a formal investigation involving the DP Coordinator and principal. Serious misconduct can result in zero credit for the assignment, removal from the specific subject, expulsion from the Diploma Programme, or expulsion from the school. External assessment misconduct is governed by Article 21 of the General Regulations and can lead to score cancellation, disqualification from diploma award, and bans from future IB examinations.

### 3.3 Restorative philosophy

IB schools typically use a 5-stage sanctions ladder (verbal warning → written warning → internal exclusion → fixed-term suspension → permanent exclusion), with mandatory parental involvement at each stage. The philosophy is explicitly restorative: meaningful behavioral change must come from the student's own reflection and choice, not from external coercion alone. Records are maintained meticulously and may be shared with future schools or universities.

### 3.4 Attendance as integrity

A point that doesn't get enough attention: IB attendance requirements are strict (>5 unexcused absences in a semester forfeits participation; missing the May exam without documented medical excuse forfeits the diploma). This isn't usually classified as anti-cheat but it functions as one — it eliminates the "I wasn't there for that work, so I'll redo it under different conditions" loophole. Worth noting for Class A's design.

### 3.5 AI policy: the most progressive of the three

IB's foundational statement is explicit: *"The IB will not ban the use of AI software. The simplest reason is that it is an ineffective way to deal with innovation."* The IB compares AI to spell-checkers, translation software, and calculators — disruptive at first, eventually integrated into legitimate practice.

The IB's distinction is **AI for learning, not for replacement**. One IB English teacher articulated it: *"If the AI is designed to learn and to increase the student's knowledge, they consider that ethical. If it's designed to do the work for that student, that's considered unethical."*

| Permitted in IB work | Prohibited in IB work |
|---|---|
| Gathering initial ideas and exploring topic structures | Writing or substantially generating essays, IA sections, reflections |
| Clarifying complex concepts and checking understanding | Creating content submitted as student's own original work |
| Grammar correction and language polishing | Replacing independent analysis, synthesis, argumentation |
| Research assistance and source discovery | Bypassing the learning process for any assessed component |
| Brainstorming research questions for the Extended Essay | |
| Formatting references and bibliographies (with verification) | |

### 3.6 Transparency requirements

IB's approach prioritizes transparency over prohibition. When AI is used, students must clearly acknowledge it through:

- In-text citation including the AI tool used, the prompt given, and the date
- Bibliography entries referencing the AI tool in the school's established style
- Annex submission: a transcript of AI interactions may be included for teacher review
- Declaration statement after the work describing how AI was used

The IB explicitly warns that *an essay predominantly AI-generated "will not get many, if any, marks with an IB mark scheme"* — not as punishment but because such work fails to demonstrate the independent thinking IB assessment values.

---

## 4. Cambridge Assessment International Education

### 4.1 Defined misconduct

Cambridge calls it **malpractice** and defines six categories: plagiarism (using others' work without proper acknowledgment), collusion (unauthorized collaboration on individual assessments), cheating in examinations (using unauthorized materials or assistance), fabrication (inventing data, sources, or evidence), impersonation (having someone else take an examination), and disruptive behavior (any behavior that disturbs other candidates).

### 4.2 Sanctions

Multi-stage and escalating, similar to IB. First minor offense: zero mark for the component, warning, academic integrity education. Repeated or serious offense: zero mark for the subject, disqualification from the qualification. Examination malpractice: score cancellation, ban from future Cambridge examinations, notification to universities.

Cambridge schools typically combine academic sanctions (grade modifications, F for the assignment or course) with administrative sanctions (disciplinary action up to and including expulsion). Severity considers extent of misconduct, level of intent, and whether the offense was premeditated.

### 4.3 Banned disciplinary practices

This is distinctive to Cambridge and sets a floor on how schools can respond. Cambridge explicitly prohibits:

- Physical punishment
- Lowering or threatening to lower grades as punishment for behavior (important: grades are academic, not disciplinary)
- Group punishment for an individual's misconduct
- Assigning additional school work as a disciplinary measure
- Mocking or humiliating students
- Denying access to washrooms or food

Students with special educational needs must not face more severe consequences than other students for comparable violations.

For Class A this is a useful design constraint: any disciplinary feedback the platform might surface must not bleed into grade penalties or punitive task assignment. The integrity response is separate from the academic record.

### 4.4 AI policy: process-supervision-first

Cambridge's policy rests on four principles:

1. **AI as a valuable resource**: generative AI "has the potential to provide a valuable resource for students and can support the learning process as students research, design and plan coursework projects."
2. **Inappropriate use as malpractice**: "The inappropriate use of generative AI to create or enhance student work without acknowledgement risks being classed as plagiarism."
3. **Teacher responsibility**: *"The primary responsibility for identifying any inappropriate use of generative AI by students remains with centres and teachers who know the students best."*
4. **Acknowledgment requirement**: all AI use must be acknowledged in the work and referenced.

| Permitted in Cambridge work | Prohibited |
|---|---|
| Initial research into a topic | Generating substantive content submitted as student's own work |
| Quoting briefly from AI-generated text and engaging in critical discussion of it | Failing to acknowledge AI assistance |
| Using AI to plan or organize a project | Using AI beyond initial research and brief quotation without syllabus authorization |

### 4.5 The "AI detection is unreliable" position

Cambridge explicitly states that **AI detection software is unreliable** and that teacher knowledge of students is the most effective safeguard against malpractice. This is the most important sentence in Cambridge's anti-cheat philosophy for Class A's purposes: the credential authority is saying that buying detection software is *not* the answer, and that the answer is having an adult who knows the student supervise the production process.

Cambridge requires teachers to: keep student work under supervision during production, be able to authenticate work as the candidate's own, monitor the production process to identify inappropriate AI use, and reference AI use clearly if any AI-generated material is included.

---

## 5. Standardized Testing Bodies (SAT, IELTS, TOEFL)

These matter to Class A specifically because they're the outcome targets for the IELTS, SAT Math, SAT Reading-Writing, and TOEFL tracks in the Outcome Track Library. Class A isn't designing these exams, but is preparing students for them, and the anti-cheat posture of the receiving body shapes what Class A can and can't simulate.

### 5.1 SAT (College Board, via Bluebook)

Same Bluebook security stack as AP (Section 2.4). As of 2024, the SAT is fully digital. The College Board can detect anomalies in response patterns through digital forensics. Banned items overlap with AP. Social media restrictions apply post-exam. Score cancellation and future-test bans for misconduct.

### 5.2 IELTS (Cambridge / IDP / British Council partnership)

Speaking test is face-to-face with an examiner (or live video for IELTS Online) — impersonation has been a historical concern, so identity verification is heavy: passport check, photograph taken at test centre, sometimes biometric (fingerprint or iris). Listening, Reading, Writing components are paper-based or computer-delivered with proctored testing centres. IELTS has dealt with industrial-scale cheating attempts in some markets, leading to result invalidation for entire test sessions. Result: IELTS now has cross-referencing across test sessions to detect identity reuse.

### 5.3 TOEFL (ETS)

Computer-delivered at test centres with substantial AI proctoring (webcam recording, microphone analysis, screen recording, biometric verification). ETS has been more aggressive than Cambridge in deploying detection AI — analyzing speech patterns, typing patterns, response timing — to flag suspicious behavior. TOEFL Home Edition (introduced 2020) is fully AI-proctored: continuous webcam monitoring, room scans before exam, lockdown browser, suspicious-behavior flagging that can result in test invalidation.

### 5.4 What this means for Class A's outcome tracks

Class A's IELTS / SAT / TOEFL tracks should *prepare* students for proctored conditions, not just for the content. That means: at some point in the track, students should encounter timed sections in a lockdown-like simulation (no copy-paste, no external tool access, timed pressure). If Class A's homework engine is the supervision layer for the entire prep flow, then the prep itself is the integrity training — students who've been doing supervised homework blocks at school for months will not be surprised by the proctored exam environment. This is a strategic advantage over prep providers who give untimed home-practice and then send students unprepared into proctored testing.

---

## 6. The AI Detection Technology Landscape

### 6.1 Turnitin (the dominant player)

The most widely deployed AI detection tool in education, integrated into Canvas, Blackboard, Moodle, Google Classroom. Same vendor as the dominant plagiarism checker. The 2026 stack runs two parallel analyses on each submission:

- **Similarity checking** (compares against billions of web pages, academic publications, previously submitted papers)
- **AI detection** (looks for writing-pattern signals correlated with how LLMs produce text — perplexity and burstiness metrics)

Turnitin's official claim: 98%+ accuracy with under 1% false positives on documents with more than 20% AI-generated text. Turnitin itself catches around 85% of unmodified AI text and deliberately accepts missing up to 15% to keep false positives below 1%.

### 6.2 The accuracy problem (significant)

Independent research is much less favorable than Turnitin's own numbers. A 2026 follow-up to Stanford research reports **a mean false positive rate of 61.3% for TOEFL essays written by Chinese students, compared with 5.1% for essays from US students** in the same setup. The pattern: detectors flag writing that's low in perplexity (predictable, generic, regular), which correlates with non-native English speakers, formal academic writing, and any precise technical writing. The detector cannot distinguish between "regular because the writer is an LLM" and "regular because the writer is a careful non-native speaker."

Institutional responses have been telling: Vanderbilt University disabled Turnitin's AI detection feature entirely, citing false-positive risk. Australian Catholic University recorded nearly 6,000 alleged misconduct cases in 2024 (about 90% AI-related), with a substantial share dismissed after investigation. ACU subsequently abandoned the Turnitin tool entirely.

**Most institutions now treat AI-detection scores above 20% as triggering further review, not as proof.** Turnitin itself recommends scores should not be the sole basis for adverse action against a student. That's an extraordinary disclaimer for a product woven into integrity workflows.

### 6.3 Competitor detection tools

GPTZero, Copyleaks, ZeroGPT, Originality.AI, and several others operate in the same space with broadly similar accuracy profiles. None has solved the false-positive problem in a way that the credential authorities accept. The IB and Cambridge have both explicitly stated they do not rely on detection software; AP doesn't rely on it for misconduct cases.

### 6.4 Online proctoring services

The established landscape: Proctorio (browser lockdown + webcam AI proctoring), Honorlock (live human proctors + AI flagging), ProctorU (live human proctors), Examity (similar), ExamSoft (offline proctored testing with lockdown). All have come under sustained criticism for bias (facial recognition fails for darker skin tones, gaze-tracking flags neurodivergent students disproportionately), privacy concerns (continuous webcam recording), and false-positive rates. Universities have been pulling back from them since 2022.

**Net of this section:** the credential authorities have correctly identified that detection-first approaches don't work. Class A should follow their lead, not the venture-funded detection-software industry's marketing.

---

## 7. LMS-Native Anti-Cheat Features

### 7.1 AP Classroom (College Board)

Doesn't have anti-cheat features per se — it's a content + practice + assessment platform. Anti-cheat for AP students lives in Bluebook (the exam delivery app), not in AP Classroom (the prep platform). The implicit message: prep is honor-system; the high-stakes test is where the security stack lives.

### 7.2 ManageBac (IB)

Has some integrity features for IB-specific workflows: eCoursework submission goes through a managed pipeline to IBIS (IB's exam system), CAS reflections are linked to documented activities, and the assessment criteria are enforced through the platform. ManageBac doesn't have native AI detection but integrates with Turnitin for schools that want it.

### 7.3 Canvas, Blackboard, Moodle, Schoology

The generic LMS layer that most schools use alongside ManageBac or AP Classroom. Integrates with Turnitin (most common), Respondus LockDown Browser (for proctored quizzes), various proctoring services. The integrity stack is opt-in per assignment.

### 7.4 What's missing across all of them

None of the existing LMS platforms has a *process-supervision-first* integrity stack — they all default to either honor-system (most assignments) or detection-after-submission (high-stakes work). The Cambridge / IB / AP Capstone insight — that authentication-by-supervised-process is the right primary mechanism — isn't built into the LMS layer. **This is a gap Class A can fill.**

---

## 8. The "Class A Is the AI" Problem

Here's the question that the three credential authorities don't have to answer but Class A does: when the platform delivering the curriculum is *itself* AI-powered (lesson generation, tutoring, hint provision, free-response grading), what does anti-cheat even mean?

**First, the AI integrated into Class A's product is not "cheating AI."** When a student uses the Socratic Tutor inside a lesson to understand a concept, that's Class A's intended pedagogy operating as designed — equivalent to a student asking a question of a teacher. The Tutor is built to teach, not to do work. This needs to be stated clearly in any Class A integrity policy because parents, teachers, and credentialing bodies will ask.

**Second, AI external to Class A is the real concern.** A student opening ChatGPT in another tab while completing a Class A free-response item is doing what the credential authorities call inappropriate AI use. The platform has limited ability to detect this directly — but the *supervised-homework architectural insight* (private schools doing homework at school during teacher-supervised blocks) substantially reduces the surface for this. The teacher in the room sees what the student is doing.

**Third, the answer-leak boundary in Class A's own AI matters.** The Socratic Tutor, the Final Boss generator, the Real Life Challenge content — all of these are AI-generated by Class A. If a student manages to manipulate the AI into revealing answers to an upcoming assessment, that's a cheat vector created by Class A itself. The homework engine already addresses this through the case-based preview standard (formula unnamed, student commits before consequence) — extending that discipline to the AI tutor's responses is a design requirement.

This third point is the deepest one: **Class A has integrity responsibilities the credential authorities don't have, because Class A is operating the AI.** This needs to be a design constraint, not an afterthought.

---

## 9. Mapping to Class A's System

This is the operational section. Each item connects to a specific Class A architectural element discussed in prior decision logs and taskboard items.

### 9.1 The supervised-homework architectural insight changes the picture fundamentally

The most important Class A architectural decision relevant to anti-cheat (recorded in the Osiyo Street 1 pivot decision log): **private-school homework is done at school during a supervised block with a teacher present.** This is not the home-alone-with-AI design assumption the original homework engine was built on.

The implication for integrity is enormous. In supervised blocks:

- The teacher *is* the process supervisor (the Cambridge and AP Capstone model)
- The teacher can affirm authorship (the AP Capstone affirmation mechanic)
- External AI use is observable — a student opening another tab is visible
- Sub-threshold runs (the homework engine's 60% threshold + 3 retries logic) feed teacher dashboards as intelligence, not failure records — which means the teacher has more information than they would from raw grades

This is also the **CFO value proposition**: AI supervision enables schools to reduce teacher labor hours, but only because the teacher is still in the room providing the integrity layer. The pitch is not "AI replaces teachers" — it's "AI plus a single supervising teacher replaces multiple subject-specific teachers."

For public schools where homework is done at home, the integrity picture is different and weaker. Class A's policy and product framing should distinguish between these two deployment contexts.

### 9.2 The Hybrid Grading + Review Queue is the integrity backbone

The existing Hybrid Grading architecture (AI grades first-pass, human reviews flagged items in a Review Queue) is already the right integrity mechanic for Class A's free-response items. It needs to be named and exposed as such, not just used internally:

- Free-response items go through AI first-pass scoring with confidence indicators
- Items below confidence threshold OR flagged for authenticity concerns (e.g., abrupt sophistication jump, AI-pattern markers, sub-threshold-but-too-perfect responses) route to the Review Queue
- A teacher with student context affirms or contests the AI's assessment
- This *is* the AP Capstone checkpoint model, implemented in software

This connects to the "Hybrid Grading + Review Queue visibility design" item in Issue 4 (Differentiation Specifications). The integrity framing strengthens the case for making this visible to teachers and parents — it's not just a quality mechanism, it's the credibility mechanism for the platform.

### 9.3 The AI Use Matrix needs to be published per content type

Following AP's course-specific approach more than IB's blanket-transparency approach. Draft:

| Content type | Class A's own AI tutoring | External AI tools |
|---|---|---|
| Case-Based Preview | Permitted (Socratic Tutor active) | Not permitted (supervised block) |
| Flashcard Learning | Permitted (hints, explanations) | Permitted (study, not assessment) |
| Practice section | Permitted (hints) | Not permitted |
| Real Life Challenge | Limited (no formula reveals, no answer leaks) | Not permitted |
| Final Boss | None (assessment moment) | Not permitted |
| Free-response items | None (assessment moment) | Not permitted |
| Capstone artifact (if implemented) | Permitted with acknowledgment (IB model) | Permitted with acknowledgment |
| Outcome track exam simulation | None (simulating proctored conditions) | Not permitted |

This needs to be published as a policy document students, parents, and teachers can read. Following AP's lead: the policy is part of the social contract for using Class A, not a hidden setting.

### 9.4 Sub-threshold data routing is also integrity data

The existing decision that sub-threshold homework attempts feed teacher/parent/school dashboards rather than being failure-marked is exactly the right design. It doubles as integrity intelligence:

- A student who hits 100% on first try every time, with no struggle visible, after a history of sub-threshold runs, is a flag
- A student whose sub-threshold runs show confused engagement followed by sudden mastery is a flag
- A student whose response style abruptly shifts in vocabulary or structure is a flag

None of these is *proof* of misconduct — Cambridge and Turnitin both warn against treating signals as proof — but they're the kind of process intelligence that a teacher with student context can act on. The Review Queue handles the routing.

### 9.5 The Final Boss / Real Life Challenge mechanics carry intrinsic integrity

The Final Boss and Real Life Challenge mechanics already have an integrity property worth noting: because Real Life Challenge is the reverse-test variant (same story, different numbers, student infers formula), a student who has obtained answers externally still has to infer the underlying mechanic. The mechanic, not the answer, is being tested. This is the "novel situation application" Cambridge philosophy implemented at the homework-engine level — and it's structurally cheat-resistant in a way that traditional homework isn't.

For the AI Use Matrix and the outcome-track design, the principle generalizes: **Class A's assessment items should test inference, not retrieval, wherever possible.** A student who used AI to memorize answer patterns will still fail a Real Life Challenge that asks them to infer the rule from a novel scenario. This is the same insight that motivates AP free-response and IB IA designs.

### 9.6 The Authentication-of-Authorship affirmation should be a real workflow

Modeled directly on AP Capstone's affirmation system, Class A should implement an affirmation workflow for outcome-track capstone artifacts:

- Student submits the artifact
- Teacher reviews progress checkpoints documented during the production process (drafts, milestones, in-supervised-block-work records)
- Teacher affirms in the platform that the work is authentic to their knowledge
- The affirmation is recorded as part of the artifact's metadata, visible to school admins and parents

This is *not* the same as AI detection. It's process supervision documented in software. It works because the teacher knows the student.

### 9.7 What Class A should *not* build

A direct application of the credential authorities' position: **Class A should not build AI-detection software as a primary integrity mechanism, and should not integrate Turnitin or competitor tools as default-on features.** The reasons:

- The accuracy is too poor (61% false positive rate for non-native English speakers — and Class A's user base is overwhelmingly non-native English speakers)
- The credential authorities explicitly don't rely on it
- Doing so would make Class A look behind the curve relative to IB/Cambridge/AP, not ahead of it
- The supervised-homework architecture already provides better integrity than any detection software

Class A *can* offer optional Turnitin integration for schools that want it (some will, especially elite-segment Cambridge / IB schools), but it should not be marketed or relied on as the primary defense.

---

## 10. Class A Academic Integrity Policy — Recommended Components

Draft outline for the policy document Class A should publish:

1. **Statement of principles** — Class A treats integrity as a teacher-affirmed process, not a detection-software-flagged outcome. Modeled on AP Capstone and the Cambridge supervision-first approach.
2. **Defined misconduct** — six categories adopted from the credential authorities: plagiarism, collusion, cheating, fabrication, impersonation, disruptive behavior. Adapted to Class A's content types.
3. **The AI Use Matrix** — per content type, what Class A's own AI does and what external AI is permitted (Section 9.3).
4. **Authentication requirements** — for capstone artifacts and outcome-track summative items: teacher affirmation, documented checkpoints.
5. **The supervised-block expectation** — private school deployments operate with teacher supervision during homework; integrity expectations reflect this.
6. **Sanctions framework** — graduated, restorative, modeled on Cambridge / IB. Explicitly does *not* include the Cambridge-banned practices (grade penalties for non-academic behavior, additional work as discipline, humiliation).
7. **Detection software position** — Class A does not rely on AI detection software. Optional integrations available for schools that want them, with explicit disclosure that scores are signals, not proof.
8. **Student transparency requirements** — when Class A's own AI tutor is used, that's part of the platform; when external AI is used in permitted contexts, the IB-style acknowledgment requirements apply.
9. **Teacher's role** — explicit framing of teacher as the primary integrity supervisor, not the platform. Connects to the CFO value proposition (one teacher supervising AI-driven instruction replaces multiple subject teachers).
10. **Appeals and review** — students whose work is flagged have a defined process. Following Turnitin's own warning: a flag is never the sole basis for adverse action.

---

## 11. Open Questions

Items not resolvable from this research alone, flagged for team decision:

- **Should Class A offer optional Turnitin (or competitor) integration?** Recommendation: yes, optional, for schools that ask. But this is a product decision with sales implications.
- **What's the appeals process when a student is flagged by Class A's own intelligence (sub-threshold pattern analysis, etc.)?** Needs to be defined before launch. The teacher-affirmation mechanic provides the answer in supervised contexts but is weaker in unsupervised home-homework contexts.
- **How does Class A handle outcome-track exam simulations under proctored conditions?** The IELTS / SAT / TOEFL prep tracks should culminate in proctored-condition simulations. Does Class A integrate with an existing proctoring service, build a lightweight lockdown mode itself, or rely on school-administered proctored sessions?
- **For ADC-elite schools running IB or Cambridge, does Class A integrate with ManageBac's integrity workflows?** ManageBac handles IBIS eCoursework submission and CAS documentation; if Class A is the LMS-layer alternative, it needs to handle equivalent workflows or interoperate.
- **What's Class A's policy on AI use in teacher-side content authoring (lesson plans generated by Course Maker)?** The credential authorities don't directly address this, but it's a transparency question Class A should answer publicly.

---

## 12. Research Gaps

Areas where this document is incomplete and would benefit from additional searching:

- **Online proctoring vendor landscape in 2026** — Proctorio, Honorlock, ExamSoft, ProctorU, Examity feature sets and reputational status
- **IELTS / SAT / TOEFL 2026-specific security stacks** — particularly the AI-proctoring features in TOEFL Home Edition and the SAT digital Bluebook stack as they evolve
- **ManageBac's specific academic integrity feature set** — what the dominant IB LMS provides natively vs requires Turnitin integration for
- **Plagiarism detection alternatives to Turnitin** — Copyleaks, GPTZero, ZeroGPT, Originality.AI — accuracy comparisons in non-native-speaker contexts
- **UK GCSE / A-Level boards beyond Cambridge** (AQA, OCR, Edexcel) — their AI policies and whether they differ from Cambridge's
- **State-level US AP equivalents** — California's A-G requirements, Texas's TEKS — for context on what public-school-aligned integrity policies look like

When these gaps are filled, the policy framework in Section 10 should be revisited to incorporate the findings.

---

## Document Identity

Research + mapping in one document. The previous comparative mapping (`NETS_AP_IB_Cambridge_Comparative_Mapping.md`) covered pedagogy and assessment philosophy. The curriculum delivery research (`NETS_AP_IB_Cambridge_Curriculum_Delivery_Research.md`) covered books, platforms, time frames. This one covers integrity — the third dimension of how the three systems operate, and the one most directly relevant to Class A's design responsibilities as an AI-driven platform.

When the three systems update their AI policies (which they do roughly annually now), this document should be regenerated rather than edited.
