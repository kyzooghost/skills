# Grill Plan Impact-Gated Interview Design

## Summary

Replace `grill-plan`'s exhaustive interview policy with an impact-gated adaptive interview. The skill will inspect the plan and codebase, inventory uncertainties privately, and ask the user only about material decisions that remain genuinely ambiguous and require human authority. Routine implementation choices remain visible when consequential, but move to agent ownership or an explicit downstream stage.

The interview should normally use 5-40 questions depending on design scope. Forty is a soft ceiling, not a quota or automatic stopping point. At that ceiling, the skill pauses, identifies any remaining major ambiguities, and recommends stopping or continuing.

## Problem

The current command says to interview the user "relentlessly about every aspect" and to walk down "each branch of the design tree." This encourages 100-150-question sessions that spend human attention on implementation mechanics and routine error handling. Repeatedly accepting the agent's recommendation adds little design value and drains the user's energy before implementation begins.

The desired workflow already has downstream stages suited to those details:

1. `superpowers:brainstorming` establishes the design.
2. `grill-plan` pressure-tests major architecture, design, and UX decisions.
3. `superpowers:writing-plans` resolves concrete implementation structure and mechanics.
4. `superpowers:subagent-driven-development` implements and reviews each task.
5. `differential-review` checks the completed change for security regressions and review gaps.

`grill-plan` should therefore protect human attention rather than attempting to eliminate every implementation-level uncertainty.

## Goals

- Focus questions on unresolved decisions with material architecture, product, UX, security/privacy, data, or compatibility consequences.
- Use an adaptive question range that makes the expected attention cost visible.
- Ask foundational, high-impact questions before their downstream consequences.
- Infer answers from the plan, codebase, history, local conventions, and prior decisions whenever evidence is sufficient.
- Preserve material agent-owned assumptions and deferred risks for downstream workflows without asking for approval.
- Stop when further questions no longer justify their human attention cost.

## Non-goals

- Resolve every implementation, error-handling, naming, testing, or code-organization detail during `grill-plan`.
- Guarantee a minimum of five questions when no material ambiguity exists.
- Treat 40 questions as a hard limit when major design ambiguity remains.
- Depend on `differential-review` to discover product, architecture, or UX intent after implementation.
- Add runtime subagents or validation overhead to ordinary `grill-plan` use.

## Runtime Workflow

### 1. Inspect and inventory

Before asking the user anything:

1. Read the active plan or design document.
2. Inspect the codebase, documentation, and history for answers that can be established locally.
3. Build a private inventory of unresolved decisions and their dependencies.
4. If the proposal contains multiple independent subsystems, recommend decomposition before starting a long interview.

### 2. Classify each uncertainty

Place each material uncertainty into one of three outcomes:

- **Human-owned:** passes the question gate and must be asked.
- **Agent-owned:** evidence, conventions, or an established decision principle supports a safe choice.
- **Deferred:** can be resolved safely by `writing-plans`, implementation, testing, or review without changing the intended contract.

Do not inventory or record trivial naming, formatting, or line-level choices.

### 3. Estimate the interview

Announce the expected question band and the major risk themes before the first question:

- Small design: 5-10 questions.
- Medium design: 10-25 questions.
- Large design: 25-40 questions.

These bands are forecasts, not quotas. Stop below the range when no question passes the gate. Revise the estimate only when newly discovered design risk materially changes the scope.

### 4. Ask in dependency and impact order

Ask one numbered question at a time. Each question includes the recommended answer and a concise explanation of the material tradeoff.

Order questions by:

1. Decisions that change or decompose scope.
2. Foundational decisions that constrain other choices.
3. Remaining decisions by consequence and reversibility.

After every answer, update the active plan or design document before asking the next question.

### 5. Reassess and stop

At the estimated upper bound, reassess whether remaining questions justify their attention cost. At 40 questions, pause and provide:

- The remaining major ambiguities, if any.
- The consequences of leaving them unresolved.
- A recommendation to stop or continue.

Continue beyond 40 only after the user accepts the recommendation. Stop immediately if the user asks to stop or shows attention fatigue, then produce the normal handoff with residual risks.

## Question Gate

Ask a question only when all four conditions hold:

1. The choice materially affects scope, architecture, product behavior, UX, security/privacy boundaries, irreversible data behavior, or external compatibility.
2. At least two plausible answers have meaningfully different consequences.
3. The answer cannot be inferred from the plan, codebase, prior decisions, history, or local conventions.
4. Choosing autonomously would require product or design authority that the agent should not assume.

Do not ask when:

- The decision is local, reversible, or implementation-specific.
- One answer is strongly supported by evidence.
- The question merely asks the user to approve the recommendation.
- A prior answer establishes the same governing tradeoff and the later choice introduces no materially new consequence.
- A downstream workflow can resolve the choice without changing the intended contract.

A security concern belongs in the interview when resolving it changes scope, trust boundaries, UX, cost, or another human-owned tradeoff. When there is one clearly safe implementation, record it as agent-owned instead of asking for approval.

## Reusing Earlier Decisions

Do not delegate by broad categories such as "UX," "architecture," or "error handling." These labels can hide later decisions with different stakes.

Treat an accepted answer as a reusable governing principle. Apply it autonomously to a later choice only when:

- The same underlying tradeoff applies.
- The later choice adds no material consequence.
- No new evidence conflicts with the earlier principle.

Otherwise, apply the full question gate again.

For example, an approved retry strategy can resolve equivalent transient-failure cases. It cannot automatically resolve retries for non-idempotent payments because the consequences differ.

## Plan Updates and Handoff

After each answer, record the resolved principle, rationale, and affected downstream decisions. Maintain only material entries under:

- **Human-owned decisions:** choices resolved through questions.
- **Agent-owned decisions:** consequential defaults inferred from evidence or approved principles.
- **Deferred implementation decisions:** material details assigned to `writing-plans`, implementation, testing, or review.
- **Residual risks:** unresolved concerns remaining when the interview stops.

At completion, report:

- Actual question count against the estimated band.
- Major decisions and reusable principles established.
- Material assumptions made without asking.
- Deferred risks and their downstream owner.
- One readiness verdict: ready for `writing-plans`, needs another focused design pass, or requires scope decomposition.

## Exceptions and Failure Handling

- If an answer conflicts with an earlier decision, identify the exact contradiction and ask only the decision needed to resolve it.
- If a factual question can be answered from the codebase, documentation, or history, investigate it instead of asking the user.
- If evidence is unavailable, mark the claim `[NEEDS VERIFICATION]`; ask the user only when progress requires human judgment.
- If a new major ambiguity appears, insert it according to dependency and impact. Revise the estimated band only when the risk materially changes scope.
- If no uncertainty passes the gate, stop without manufacturing questions.

## Skill Changes

Update the shared command source at `commands/grill-plan.md`. The existing `skills/grill-plan/references/command.md` symlink will continue exposing that command to the skill.

Update `skills/grill-plan/SKILL.md` so its concise top-level rules reinforce the impact gate, adaptive 5-40 range, plan updates, and codebase-first investigation. Remove wording that asks for relentless, exhaustive coverage of every implementation decision.

Review `skills/grill-plan/agents/openai.yaml` against the revised behavior. Its current interface copy can remain if it still accurately describes the skill after implementation.

## One-Time Behavioral Validation

Validation occurs only while developing this change or a future material revision. It is not part of normal `grill-plan` runtime behavior.

Use fresh subagents on three representative plans:

1. A mature small design containing many routine implementation choices.
2. A medium feature with several genuine architecture and UX ambiguities.
3. A large proposal containing independent subsystems that should be decomposed.

First run the scenarios against the current skill to capture the failing baseline. Then run equivalent scenarios against the revised skill and verify that it:

- Announces an appropriate question band.
- Prioritizes foundational, high-impact ambiguities.
- Avoids questions about safely delegated implementation details.
- Reuses established principles without suppressing new consequences.
- Stops early when the gate is empty.
- Reassesses rather than running past its estimated range.
- Produces the material decision ledger and readiness verdict.

Finally, run the repository's skill validator and confirm the agent metadata remains consistent with the revised skill.
