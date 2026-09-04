# Complexity Review Skill - Design Spec

**Date:** 2026-09-04
**Status:** Draft

## Purpose

Review a PR for unnecessary complexity, brittle test strategies, and overengineering. Complements grill-plan (which catches these at plan time) by applying the same lens at PR review time.

## Skill structure

```
skills/complexity-review/
  SKILL.md                    # Entry point - delegates to references
  references/
    command.md                # Workflow, report format, error handling (symlinked from commands/)
    lenses.md                 # Detection criteria for each lens
commands/
  complexity-review.md        # Source file, symlinked into references/command.md
```

Follows the grill-plan pattern: `SKILL.md` delegates to `references/command.md` for the workflow and `references/lenses.md` for detection criteria.

## Input

Accepts a PR URL or `owner/repo#N`.

Fetches via `gh api`:

```bash
# Diff
gh api repos/<owner>/<repo>/pulls/<number> -H "Accept: application/vnd.github.v3.diff"

# Metadata (title, description, file list)
gh api repos/<owner>/<repo>/pulls/<number>
```

No local checkout required.

## Three lenses

Each lens has a definition, concrete signals, and false-positive guards. Full criteria live in `references/lenses.md`.

### 1. Unnecessary complexity

Code harder to understand than the problem demands.

**Signals:**
- Deep nesting (3+ levels of conditionals/loops)
- Excessive indirection (call chains through multiple layers to reach simple logic)
- Abstraction layers with only one implementation
- Generics/parameterization solving a single concrete case
- Configuration-driven behavior that's never reconfigured

**False-positive guards:**
- Abstraction with one implementation is fine when a second is planned and referenced in a ticket
- Deep nesting may be justified by genuinely complex domain logic

### 2. Brittle tests

Tests that break on implementation changes rather than behavior changes.

**Signals:**
- Over-mocking (mocking what you own rather than what you don't)
- Testing private internals or implementation details
- Snapshot tests on volatile output
- Hardcoded values coupled to implementation detail rather than behavior
- Excessive setup relative to the assertion

**False-positive guards:**
- Mocking external services and I/O boundaries is correct
- Some implementation-aware tests are justified for performance-critical paths

### 3. Overengineering

Building for requirements that don't exist.

**Signals:**
- Speculative features behind flags nobody uses
- Plugin systems with one plugin
- Event buses with one subscriber
- Premature optimization without profiling evidence
- Framework-level abstractions for application-level problems
- Dead configuration or unused extension points

**False-positive guards:**
- Extension points are fine when a concrete near-term use case exists and is documented
- Performance-sensitive paths may justify optimization even without profiling

## Findings format

Each finding includes:

| Field | Description |
|-------|-------------|
| **Lens** | Which of the three lenses |
| **File:line** | Location in the diff |
| **What** | One-sentence description |
| **Why it matters** | Concrete cost (readability, maintenance, test fragility) |
| **Recommendation** | Specific action (simplify to X, inline Y, replace mock with real, remove Z) |
| **Impact** | LOW / MEDIUM / HIGH based on blast radius and maintenance cost |

## Report structure

Saved to `<REPO>_COMPLEXITY_REVIEW_<DATE>.md` in the working directory.

### 1. Header

PR number, title, date, file count, diff size.

### 2. Summary

Finding count per lens, high-impact count, overall assessment sentence (e.g. "7 findings across 2 lenses, 2 high-impact").

### 3. Findings

Grouped by lens. Within each lens, sorted by impact (HIGH first).

Each finding rendered as:

```markdown
### [LENS] Finding title

**File:** `path/to/file.ts:L42-L58`
**Impact:** HIGH

**What:** One-sentence description.

**Why it matters:** Concrete cost explanation.

**Recommendation:** Specific action to take.
```

### 4. Recommendations summary

Deduplicated action items across all findings, ordered by impact.

## Workflow

1. Parse PR input (URL or `owner/repo#N`), extract owner, repo, number.
2. Fetch PR diff and metadata via `gh api`.
3. Walk each changed file in the diff. Review the diff hunks, but read surrounding context from the full file when needed to judge abstractions or test structure. When a finding's validity depends on codebase-wide context (e.g. checking whether other implementations of an interface exist), explore beyond the diff via `gh api` for file contents or repo search. Scope this exploration to specific findings that demand it - do not perform a general codebase sweep. Apply all three lenses from `references/lenses.md`.
4. Collect findings, deduplicate overlapping signals.
5. Write report to `<REPO>_COMPLEXITY_REVIEW_<DATE>.md` in the working directory.
6. Print summary to terminal with file path.

## Error handling

- `gh` CLI missing or not authenticated: stop with error message.
- PR not found (404): stop with error message.
- Empty diff (no changed files): stop with "Nothing to review."
- Report write fails: fall back to terminal output.

## Out of scope

- Posting findings as PR comments (use `pr-review-comments` for that).
- Security analysis (use `differential-review`).
- Code correctness bugs (use `/code-review`).
- Auto-fixing findings.
