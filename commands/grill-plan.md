Pressure-test this plan by spending human attention only on unresolved decisions whose consequences justify it. Reach shared understanding of the product and design contract without forcing implementation details into the interview.

## Before asking

1. Read the active plan or design document.
2. Inspect the codebase, documentation, and history for answers available locally.
3. Build a private inventory of unresolved decisions and their dependencies.
4. If the proposal contains multiple independent subsystems, recommend decomposition before starting a long interview.

Classify each material uncertainty as:

- **Human-owned:** must pass the question gate below.
- **Agent-owned:** evidence, conventions, or an established decision principle supports a safe choice.
- **Deferred:** `writing-plans`, implementation, testing, or review can resolve it without changing the intended contract.

Do not inventory or record trivial naming, formatting, or line-level choices.

## Question gate

Ask a question only when all four conditions hold:

1. The choice materially affects scope, architecture, product behavior, UX, security or privacy boundaries, irreversible data behavior, or external compatibility.
2. At least two plausible answers have meaningfully different consequences.
3. The answer cannot be inferred from the plan, codebase, prior decisions, history, or local conventions.
4. Choosing autonomously would require product or design authority that the agent should not assume.

Do not ask when the decision is local, reversible, implementation-specific, strongly supported by evidence, or safely owned by a downstream workflow. Never ask merely to obtain approval for your recommendation.

Ask about a security concern when resolving it changes scope, trust boundaries, UX, cost, or another human-owned tradeoff. When one implementation is clearly safe, record it as agent-owned.

## Estimate the interview

Before the first question, announce the major risk themes and an expected band:

- Small design: 5-10 questions.
- Medium design: 10-25 questions.
- Large design: 25-40 questions.

These are forecasts, not quotas. Stop below five when no question passes the gate. Revise the estimate only when newly discovered design risk materially changes scope.

## Interview

Ask questions one at a time. Number each with an ordinal label such as `1st Q`, `2nd Q`, `3rd Q`, or `50th Q`. Include your recommended answer and the material tradeoff.

Ask in this order:

1. Decisions that change or decompose scope.
2. Foundational decisions that constrain other choices.
3. Remaining decisions by consequence and reversibility.

After every answer, immediately update the active plan or design document with the resolved principle, rationale, and affected downstream decisions before asking the next question.

Treat an accepted answer as a reusable governing principle, not blanket delegation over a broad category. Apply it to a later choice only when the same tradeoff applies, no materially new consequence appears, and no evidence conflicts. Otherwise apply the full question gate again.

If an answer contradicts an earlier decision, identify the exact conflict and ask only what is needed to resolve it. If evidence is unavailable, mark the claim `[NEEDS VERIFICATION]` and ask the user only when progress requires human judgment.

## Reassess and stop

At the estimated upper bound, reassess whether remaining questions justify their attention cost. At 40 questions, pause and state:

- The remaining major ambiguities.
- The consequences of leaving them unresolved.
- Your recommendation to stop or continue.

Continue beyond 40 only when the user explicitly chooses to continue after seeing the reassessment. If the user asks to stop or shows attention fatigue, stop immediately and produce the handoff with residual risks.

Stop whenever every remaining uncertainty is inferable, agent-owned, safely deferred, or too low-impact to justify human attention. Do not manufacture questions to reach the estimated range.

## Plan ledger and handoff

Maintain only material entries under:

- **Human-owned decisions**
- **Agent-owned decisions**
- **Deferred implementation decisions**
- **Residual risks**

At completion, report:

- Actual question count against the estimated band.
- Major decisions and reusable principles.
- Material assumptions made without asking.
- Deferred risks and their downstream owner.
- One readiness verdict: ready for `writing-plans`, needs another focused design pass, or requires scope decomposition.
