# What makes this project distinctive?

17 October 2026. Result of a three-round debate between a skeptical challenger agent and a defending designer agent. Both read the current revised project plan and exchanged questions and answers. The dialogue below is condensed from their actual exchange; conclusions are recommendations, not experimental results.

## Verdict

The strongest identity is an **engineering evidence lab**: candidates explain a project decision, investigate a related synthetic incident, justify a conclusion, test code, inspect feedback, and try a fresh case.

The central question is: **“What evidence supports your explanation, and what would change your mind?”**

Voice questions, a resume upload, a code editor, streaming, and an LLM-generated score would not establish a distinctive product. The proposed substance is an application-controlled exercise with fixed facts, an inspectable decision history, verified execution results, and correctable assessment.

This is a proposal. The repository currently contains planning documents, not a working product. “Unique” here means a promising differentiated workflow, not proven worldwide exclusivity.

### Suggested pitch

> An engineering interview lab that asks you to predict, investigate, explain, and verify—not just recite an answer. Review the evidence behind its feedback, correct mistakes, and apply the skill to a fresh problem.

## The debate

### Round 1: What survives existing products?

**Challenger:** Resume defense, voice, debugging, retry/transfer, local speech, and replay already have cited prior art. What precise behavior remains distinctive? What does the application own that the same model in a well-prompted chat would need additional software to reproduce?

**Defender:** Those ingredients are not individually new. The proposed distinction is a reproducible evidence-reconciliation exercise: versioned scenario cards, learner-confirmed hypotheses, chronological disclosure events, findings linked to both observations and task premises, assessment based on what was known then, dependent reassessment after correction, and an uncoached matched variant. Application code and reviewed content own these rules.

**Challenger:** That explains engineering substance, not market exclusivity. A sufficiently engineered competitor or general assistant could reproduce it.

**Defender:** Agreed. The claim is a coherent, auditable workflow whose usefulness must be measured. It is not an exclusive capability or a guaranteed competitive moat.

**Resolution:** Lead with the learning experience and demonstrable guarantees. Do not claim that combining familiar features makes each feature new.

### Round 2: Does an evidence trail make scoring correct?

**Challenger:** Event IDs prove linkage, not truth. What prevents a valid alternative diagnosis from being marked wrong? What prevents rewarding arbitrary mind-changing or treating an edited transcript as proof of the original speech?

**Defender:** Each variant needs authored symptoms, assumptions, immutable evidence, reveal rules, accepted explanations and alternatives, uncertainty boundaries, rubric examples, and verification contracts. Two competent reviewers independently inspect them. An unresolved alternative triggers abstention or review. Justified retention and justified revision both count. Transcript corrections retain the original and are labeled as candidate corrections, not reconstructed audio truth.

**Challenger:** A demonstration can prove software behavior. It cannot prove better learning, hiring validity, or broad engineering competence.

**Defender:** Agreed. Compare against the same model in chat, with the same content, rubric, time budget, and fair access to evidence. Blind reviewers assess validity, coverage, factual drift, correction handling, usefulness, and fresh-case performance. Disable automatic adverse labels if assessment validation fails.

**Resolution:** Auditability is necessary but insufficient. Technical premises and assessment inferences still need independent validation. A single caching family cannot establish competence across arbitrary projects.

### Round 3: Which extras justify their cost?

**Challenger:** Rank at most five actual extensions. Give a user action, minimum implementation, safeguard, and observable demonstration. Avoid renaming existing core behavior as a new feature.

**Defender:** First, record a diagnostic prediction before revealing evidence. Second, compare an authored repair invariant with executed code behavior. Third, include a genuinely underdetermined case. Later, test safety-constrained recovery decisions and a delayed fresh-case return. Reuse the existing event history, authored content, and runner. Defer the last two first.

**Challenger:** What result would make you stop expanding this product?

**Defender:** If fair same-model chat provides equivalent reliability and usefulness with less friction, retain only demonstrated application value or stop expansion. Also reconsider if learners cannot identify an actionable reasoning gap.

**Resolution:** Build one measurable extension first. Do not accumulate novelty claims faster than evidence of usefulness.

## What makes it more than a simple AI wrapper?

A cloud API is a dependency. The important question is how much of the product's behavior exists outside its prompts.

| Application-owned capability | Concrete work beyond prompting | Proof to show |
|---|---|---|
| Fixed scenario facts | Authored, versioned evidence cards and accepted reasoning paths; the model cannot invent diagnostic results | Replaying the same scenario preserves its facts |
| Controlled information disclosure | Backend controls what is revealed and excludes hidden answers from interviewer context | A request cannot reveal an unavailable card or answer key |
| Knowledge-at-the-time assessment | Each decision is associated with evidence already disclosed | A reasonable initial hypothesis receives no hindsight penalty |
| Decision history | Persist hypotheses, requests, predictions, revisions, and support level | Report reconstructs how the conclusion was reached without relying on a model summary |
| Grounded, contestable findings | Separate candidate observation, task premise, inference, and coaching; validate references | A real quote paired with an invalid premise is still rejected |
| Correction propagation | Version transcript corrections and recompute dependent findings | One repaired STT term changes affected judgments while unrelated findings remain stable |
| Verified Python/C++ behavior | Isolated execution, fixed contracts, public/hidden tests, resource limits, and immutable submissions | Report links to actual run results and distinguishes infrastructure failures |
| Controlled practice progression | Separate independent attempts, hints, coaching, and fresh variants | A coached repair is not reported as independent mastery |
| Responsive voice delivery | Client text streaming, chunked local synthesis, audio streaming, bounded queues, and interruption cancellation | Playback starts before completion; cancelled output never resumes |

These are proposed software/content responsibilities, not implemented guarantees. Structured JSON, timestamps, or tests alone do not make every assessment correct.

**Provider replacement test:** changing the LLM should preserve scenario facts, disclosure rules, event history, execution results, corrections, and assessment coverage accounting. Wording and judgment quality may change. If replacing the API erases the whole experience, the application has not yet established much independent substance.

### Substance versus differentiation

- **Necessary engineering:** streaming, interruption handling, sandboxing, consent, deletion, and recovery. Valuable, but not novelty headlines.
- **Differentiation hypothesis:** prospective diagnostic reasoning, fixed staged evidence, inspectable feedback, code verification, and a matched fresh case in one focused workflow.
- **Potential longer-term advantage:** independently reviewed scenario quality, validated alternative-answer handling, reliable corrections, and measured learning usefulness. These take work to develop; none is an established moat yet.

Current deployment is **local STT/TTS with cloud reasoning and code review**, plus a second Ubuntu laptop for isolated code execution. Raw microphone audio remains local under the proposed design; selected text and code leave the machine. Do not describe it as fully offline or fully private local inference.

## Extra features

These are optional proposals, not additional mandatory first-release scope. The timeline, corrections, and same-symptom/different-cause variant are already core and are not counted again as new extras.

### 1. Predict before reveal — add first

**Experience:** Before opening a diagnostic card, the candidate states an expected result and what that result would support or rule out.

**Example:** “If this response comes from the stale cache, the request trace should show a cache hit. A cache miss would weaken that explanation.” Reveal the fixed trace and ask the candidate to reconcile it with the prediction.

**Minimum addition:** One short prediction field or confirmed spoken statement, linked to the chosen diagnostic and recorded before reveal. Preserve later edits as revisions. Reuse the existing event timeline.

**Value:** Makes prospective reasoning visible. A polished explanation written after seeing the answer cannot replace the recorded prediction.

**Safeguard:** Predictions are provisional. Reward neither lucky guesses nor answer-changing automatically. Assess whether the predicted observation distinguishes plausible explanations, using reviewed anchors. A failed prediction is not inherently a failure if the candidate updates appropriately.

**Demo acceptance:** The report shows prediction time before reveal time, actual evidence, and the candidate's explanation of agreement or disagreement. Retrospective edits cannot overwrite the original prediction.

**Cost:** Small software change; moderate rubric/content review. No exclusive-market claim.

### 2. Explanation-to-code verification — add next

**Experience:** The candidate selects or states a testable repair property, submits Python/C++, and compares the explanation with an authored regression result.

**Example:** “After updating a price, the next read must return the new value.” An authored update-then-read case shows that the submitted repair still returns the old value. The candidate explains why the implementation does not establish the promised property.

**Minimum addition:** Link a confirmed repair property to a pre-authored public regression and immutable code submission. Reuse the sandbox and execution records.

**Value:** Goes beyond verbal fluency: the candidate must connect an explanation to observed behavior.

**Safeguard:** Restrict verification to authored, executable properties. Do not claim arbitrary natural-language requirements can be proven automatically. A passed regression establishes only that tested case, not universal correctness. Wrong output does not itself establish why the code failed.

**Demo acceptance:** One plausible verbal repair fails the linked regression; a corrected submission passes. The report attributes each outcome to the right source version and identifies infrastructure errors separately.

**Cost:** Moderate integration and authored-test work. Code verification already exists elsewhere; the explanation-to-evidence connection is the proposed product emphasis.

### 3. Insufficient-evidence cases — controlled experiment

**Experience:** Some cases genuinely lack enough information to distinguish causes. The candidate names the missing observation and recommends a conditional next step.

**Example:** The packet shows an old response and a successful write but omits request-path evidence. Neither stale caching nor replica lag can be established from that packet alone.

**Minimum addition:** One reviewed underdetermined variant with explicit missing facts and acceptable conditional responses.

**Value:** Practices responsible uncertainty instead of rewarding a confident guess for every question.

**Safeguard:** Mix resolvable and underdetermined cases. “Not enough information” without a relevant missing observation is not automatically a strong answer. Do not make missing evidence an undisclosed trick.

**Demo acceptance:** A justified conditional answer is accepted in the underdetermined case; the same blanket abstention is not treated as sufficient when decisive evidence is available.

**Cost:** Small software change, substantial content validation relative to its size.

### 4. Recovery under explicit safety constraints — later

**Experience:** Choose a simulated rollback, mitigation, or repair under fixed downtime and data-loss constraints. Explain what makes the choice acceptable and what must be verified first.

**Example:** A rollback could restore availability but cannot safely read data written by the new version. The candidate must address compatibility rather than reflexively choosing rollback.

**Minimum addition:** An authored decision branch with explicit system constraints, acceptable alternatives, and simulated consequences.

**Safeguard:** No real infrastructure actions. Do not penalize an alternative satisfying the stated constraints. Do not introduce previously hidden constraints after the decision to manufacture failure.

**Demo acceptance:** Report connects a decision to a disclosed constraint and its simulated outcome; justified alternatives remain accepted.

**Cost:** Higher content-authoring and validation effort. Defer before expanding the core case family.

### 5. Delayed fresh-case return — later

**Experience:** With consent, return on a later day for a fresh case exercising the same principle with changed cues and cause.

**Minimum addition:** More independently reviewed content and retained skill/support history. No recurring reminder system is required for the initial experiment; the learner can return voluntarily.

**Value:** Provides a stronger observation of later application than repeating the answer immediately after coaching.

**Safeguard:** Record prior exposure, hints, and elapsed time. Use comparable prerequisites. One return cannot prove durable learning or exclude outside practice. Respect deletion and retention choices.

**Demo acceptance:** Report separates baseline, assisted practice, immediate fresh attempt, and later attempt. It reports observations without attributing all changes causally to the product.

**Cost:** Moderate content and study-design effort. Defer with safety-constrained recovery if time is limited.

## A convincing demonstration

Use one coherent authored caching exercise, rather than unrelated feature screens:

1. Candidate confirms a real resume claim and its limits. Label the following incident synthetic.
2. Candidate proposes a cache hypothesis and predicts a diagnostic result before reveal.
3. Backend reveals the fixed card; candidate justifies retaining or revising the explanation.
4. Candidate submits a related Python/C++ repair and checks an authored regression.
5. Candidate reconciles an explanation/code mismatch, if one exists.
6. Correct a deliberately injected transcript error; recompute only dependent findings and preserve the original.
7. Present the fresh stale-response case caused by replica lag, with comparable prerequisites. Do not coach this attempt.
8. Show the report's evidence trail, actual execution results, assistance levels, and uncertainty.

Do not script a failure that every candidate must make. The demonstration must also support a correct initial answer, a sound alternative diagnosis, justified retention, and candidate disagreement with an invalid finding.

This demonstration can establish intended application behavior. It cannot by itself establish better learning outcomes.

## How to test whether the differentiation matters

Compare the application with a well-prompted chat using the **same model, same scenario content, same rubric, same time budget, and fair evidence access**. Give the baseline adequate instructions; do not compare against a deliberately weak generic chatbot.

Use counterbalanced equivalent cases to reduce order effects. Hide the condition from reviewers where practical. Review:

- Supported findings and assessable-criterion coverage, with exact denominators.
- Invented diagnostic facts or premature answer leakage.
- Whether judgments respect what the candidate knew at the time.
- Treatment of valid alternative answers and justified uncertainty.
- Correction propagation and unchanged unrelated findings.
- Actual execution attribution and separation of runner errors.
- Task completion, interaction friction, and an actionable next practice step.
- Fresh-case reasoning, with hints and prior exposure recorded.

Retain the plan's proposed small assessment gates: at least 90% supported actionable findings, at least 80% assessable-criterion coverage, and no observed unsupported severe finding in the reviewed sample. These are exploratory release checks, not production reliability guarantees. An early pilot cannot establish causal learning gains.

**Disconfirmation:** If the same-model baseline is equally reliable and useful with less friction, do not claim superiority. Revise the task, retain only demonstrated event/runner value, or stop expansion. If assessment validity fails, remove automatic adverse labels rather than hiding uncertainty behind a score.

## Prior art and limits on claims

The following official sources were researched earlier in this conversation on 17 October 2026. They were not independently re-tested or reverified during this debate.

| Proposed ingredient | Existing overlap | Implication |
|---|---|---|
| Resume cross-examination | [Rolewyn](https://rolewyn.com/products/interview) | Not an exclusive proposition |
| Own-project explanation and live changes | [RoundJump](https://roundjump.com/) | Project grounding alone is insufficient differentiation |
| Code comprehension and planted defects | [PrepLinx](https://www.preplinx.com/ai-mock-interview/code-comprehension) | Debugging alone is insufficient differentiation |
| Voice debugging and process feedback | [MockIF](https://mockif.com/debugging-interview-practice) | Voice plus diagnostic practice has prior art |
| Retry, transfer, and spaced return | [Frontend Interviews methodology](https://frontendinterviews.com/methodology) | Sound pedagogy, not a newly invented method |
| Local voice-model pipeline | [DeepInterview release](https://github.com/ngoanpv/DeepInterview/releases/tag/v0.3.0) | Local processing is an implementation property, not uniqueness proof |

Do not claim: world's first; absent from every released product; fake-resume detection; verified historical ownership; learning proven by one retry; arbitrary-project competence from one incident family; or assessment correctness merely because a criticism has a quote and timestamp.

**Recommended first extra:** predict before reveal. It is the smallest addition that makes the project's reasoning-centered identity more visible and testable. Leave other extras optional until the complete core works.
