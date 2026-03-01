# CLAUDE.md

# Strict Rules

If anything about the user's request is unclear, interview me relentlessly and very in-depth using the AskUserQuestionTool about literally anything: technical implementation, system design, bottlenecks, UX, concerns, tradeoffs, etc. 

Always include unit tests (with /test-driven-development and /unit-test in mind) when implementing new methods, functions, or any code changes. Do not consider a task complete until tests are written and passing.

If an environment variable is added or removed, update the corresponding .env.* template files in the same project to match.

Use shared const enums or constant objects instead of raw string literals when introducing new string values. Never scatter raw strings across files.

When installing new dependencies, pin exact versions. Do NOT use floating versions, ranges, wildcards, or "latest".

When writing code comments or documentation, be concise - every word should earn its place. No redundant sentences; each should register a new concept.

Any code comments should be written for a developer with zero prior context on the codebase. Explaining 'why' is more important than 'what' - the code should be self-documenting.

Never commit code that logs sensitive details (credential tokens, RPC URLs, etc.) - mask them if they must appear in output. Temporary unmasked logging for local debugging is acceptable if reverted before committing.

All bash scripts must start with `set -euo pipefail`.

Do not write with emdash `—`, write with regular dash `-` instead

When you significantly course-correct during a task - wrong architecture, misunderstood pattern, missed convention - suggest that I add the lesson to CLAUDE.md. Be specific: state what you got wrong, why, and what the rule should say.

# Coding Guidelines

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Error Handling

- Fail fast with clear, actionable messages
- Never swallow exceptions silently
- Include context (what operation, what input, suggested fix)

# Technical Writing & Analysis

When writing technical documentation or doing deep technical analysis:
- Use EXACT values from source material - never approximate (e.g., "exactly 1 block" not "~1
block", specific fee percentages not vague descriptions).
- Do NOT invent steps, mechanisms, or details not in the source.
- Flag uncertain claims with [NEEDS VERIFICATION] rather than guessing.
- For protocol/contract descriptions, cite the specific file and line.

## Mermaid Diagrams

When creating Mermaid diagrams:
- Never split a single statement across multiple lines. Each diagram statement (e.g., `A->>B:
message`) must be on one line.
- Validate syntax mentally before presenting - watch for stray `end` keywords, unclosed blocks,
and incorrect nesting.

## Tables

When writing tables, provide both ASCII (plain text) and Markdown formats so the output is copy-pasteable into any tool.
