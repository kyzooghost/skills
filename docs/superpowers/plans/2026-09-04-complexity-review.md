# Complexity Review Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a skill that reviews PRs for unnecessary complexity, brittle tests, and overengineering, producing a local markdown report with findings and recommendations.

**Architecture:** Three markdown files following the grill-plan pattern. `SKILL.md` delegates to `references/command.md` (workflow) and `references/lenses.md` (detection criteria). The command file is the source of truth, symlinked into the skill.

**Tech Stack:** Markdown skill files, `gh api` for PR data, symlinks for command/skill binding.

**Spec:** `docs/superpowers/specs/2026-09-04-complexity-review-design.md`

---

## File Map

- Create: `commands/complexity-review.md` — workflow, report format, error handling
- Create: `skills/complexity-review/SKILL.md` — entry point, delegates to references
- Create: `skills/complexity-review/references/lenses.md` — detection criteria for all three lenses
- Create: `skills/complexity-review/references/command.md` — symlink to `../../../commands/complexity-review.md`

---

### Task 1: Create the lenses reference

This file defines the detection criteria the agent uses during review. It must exist before the command references it.

**Files:**
- Create: `skills/complexity-review/references/lenses.md`

- [ ] **Step 1: Create the lenses file**

```markdown
# Complexity Review Lenses

Three lenses for reviewing PR changes. Apply each to every changed file. When a signal appears, verify it against the false-positive guards before raising a finding.

## 1. Unnecessary Complexity

Code harder to understand than the problem demands.

### Signals

- **Deep nesting:** 3+ levels of conditionals or loops where flattening (early returns, extraction) is straightforward.
- **Excessive indirection:** Call chains through multiple layers to reach simple logic. A function that delegates to a function that delegates to a function that does one thing.
- **Single-implementation abstractions:** Interfaces, abstract classes, or strategy patterns with exactly one concrete implementation.
- **Unnecessary generics:** Type parameters, parameterization, or configuration solving a single concrete case.
- **Dead configuration:** Configuration-driven behavior where the configuration never varies in practice.

### False-Positive Guards

- An abstraction with one implementation is acceptable when a second is planned and referenced in a ticket or the PR description.
- Deep nesting may be justified by genuinely complex domain logic (e.g. state machines, protocol parsing). If flattening would obscure the logic, it is not a finding.
- Indirection for dependency injection at I/O boundaries is standard practice, not excessive indirection.

## 2. Brittle Tests

Tests that break on implementation changes rather than behavior changes.

### Signals

- **Over-mocking:** Mocking classes, functions, or modules owned by the same codebase rather than external dependencies. The test knows too much about internal wiring.
- **Testing internals:** Assertions against private methods, internal state, or implementation-specific data structures rather than observable behavior.
- **Volatile snapshots:** Snapshot tests on output that changes with timestamps, random IDs, environment state, or formatting.
- **Implementation-coupled values:** Hardcoded expected values derived from how the code works rather than what it should produce. Changing an internal algorithm breaks the test even though the behavior is correct.
- **Setup-heavy tests:** Test setup that is 10x the assertion. The reader cannot tell what is being tested.

### False-Positive Guards

- Mocking external services, databases, file systems, and network I/O is correct - these are boundaries you do not own.
- Some implementation-aware tests are justified for performance-critical paths where the implementation IS the behavior (e.g. verifying an O(n) algorithm is not replaced with O(n^2)).
- Large setup is acceptable in integration tests that exercise a real subsystem.

## 3. Overengineering

Building for requirements that do not exist.

### Signals

- **Speculative features:** Code behind feature flags that are never toggled, or optional parameters that are never exercised.
- **One-consumer patterns:** Plugin systems with one plugin, event buses with one subscriber, factory patterns producing one type, registry patterns with one entry.
- **Premature optimization:** Performance optimization without profiling evidence or documented performance requirements. Caching layers, object pools, or custom data structures where the standard library suffices.
- **Framework-level abstractions:** Building reusable frameworks, SDKs, or libraries when the code serves one application-level use case.
- **Dead extension points:** Hook methods, callback registries, or middleware chains with a single user.

### False-Positive Guards

- Extension points are acceptable when a concrete near-term use case is documented (in a ticket, PR description, or code comment with a ticket reference).
- Performance-sensitive paths (hot loops, latency-critical endpoints) may justify optimization even without profiling, provided the performance requirement is documented.
- Patterns mandated by the framework or platform (e.g. a DI container requiring an interface) are not overengineering.
```

- [ ] **Step 2: Commit**

```bash
git add skills/complexity-review/references/lenses.md
git commit -m "feat(complexity-review): add detection lenses reference"
```

---

### Task 2: Create the command file

The workflow, report format, and error handling. Source of truth lives at `commands/complexity-review.md`.

**Files:**
- Create: `commands/complexity-review.md`

- [ ] **Step 1: Create the command file**

```markdown
Review a pull request for unnecessary complexity, brittle test strategies, and overengineering. Produce a local markdown report with findings and actionable recommendations.

## Input

Accepts a PR URL (e.g. `https://github.com/owner/repo/pull/123`) or shorthand `owner/repo#123`.

Parse the input to extract owner, repo, and PR number.

## Step 1: Fetch PR data

Fetch the diff and metadata:

```bash
# Diff
gh api repos/<owner>/<repo>/pulls/<number> -H "Accept: application/vnd.github.v3.diff"

# Metadata (title, description, changed files)
gh api repos/<owner>/<repo>/pulls/<number>
```

Error handling:
- `gh` not available or not authenticated: stop with `Error: gh CLI is not available or not authenticated.`
- PR not found (404): stop with `Error: PR not found.`
- Empty diff (no changed files): stop with `Nothing to review.`

## Step 2: Review each changed file

For each file in the diff:

1. Read the diff hunks.
2. When judging an abstraction or test structure requires more context, fetch the full file via `gh api repos/<owner>/<repo>/contents/<path>?ref=<head-sha>`.
3. When a finding's validity depends on codebase-wide context (e.g. checking whether other implementations of an interface exist), explore beyond the diff via `gh api` for file contents or code search. Only follow this path when a specific finding demands it. Do not perform a general codebase sweep.
4. Apply all three lenses from `references/lenses.md`.
5. For each signal detected, check the false-positive guards before recording a finding.

## Step 3: Collect and deduplicate findings

Collect all findings. Where the same code triggers signals under multiple lenses, merge into a single finding under the most specific lens. Prefer overengineering > unnecessary complexity > brittle tests when choosing the primary lens.

## Step 4: Write report

Save to `<REPO>_COMPLEXITY_REVIEW_<DATE>.md` in the working directory. Use the format below.

If the file write fails, fall back to printing the full report to the terminal.

### Report format

```markdown
# Complexity Review: <repo>#<number>

**PR:** <title>
**Date:** <YYYY-MM-DD>
**Files reviewed:** <count>
**Diff size:** +<additions> / -<deletions>

## Summary

<N> findings across <M> lenses. <X> high-impact.

| Lens | Findings | High | Medium | Low |
|------|----------|------|--------|-----|
| Unnecessary Complexity | ... | ... | ... | ... |
| Brittle Tests | ... | ... | ... | ... |
| Overengineering | ... | ... | ... | ... |

## Findings

### Unnecessary Complexity

#### <Finding title>

**File:** `path/to/file.ts:L42-L58`
**Impact:** HIGH | MEDIUM | LOW

**What:** One-sentence description.

**Why it matters:** Concrete cost explanation.

**Recommendation:** Specific action to take.

---

### Brittle Tests

(same format per finding)

### Overengineering

(same format per finding)

## Recommendations

1. <Highest-impact action>
2. <Next action>
...
```

Omit any lens section that has zero findings.

## Step 5: Print summary

After writing the report, print to the terminal:

```
Report saved: <filename>
<N> findings (<X> high, <Y> medium, <Z> low)
```
```

- [ ] **Step 2: Commit**

```bash
git add commands/complexity-review.md
git commit -m "feat(complexity-review): add command workflow and report format"
```

---

### Task 3: Create SKILL.md and symlink

The skill entry point and the symlink binding command into the skill's references directory.

**Files:**
- Create: `skills/complexity-review/SKILL.md`
- Create: `skills/complexity-review/references/command.md` (symlink to `../../../commands/complexity-review.md`)

- [ ] **Step 1: Create SKILL.md**

```markdown
---
name: complexity-review
description: Review a PR for unnecessary complexity, brittle test strategies, and overengineering. Produces a local markdown report with findings and actionable recommendations. Use when the user says "/complexity-review", "review this PR for complexity", or asks to check a PR for overengineering.
---

# Complexity Review

Read and follow `references/command.md`. Use `references/lenses.md` for the detection criteria.

Review the PR diff through three lenses: unnecessary complexity, brittle tests, and overengineering. For each finding, explain the concrete cost and recommend a specific action.

Write the report to a local markdown file. Print a summary to the terminal.
```

- [ ] **Step 2: Create the symlink**

```bash
ln -s ../../../commands/complexity-review.md skills/complexity-review/references/command.md
```

- [ ] **Step 3: Verify the symlink resolves**

```bash
cat skills/complexity-review/references/command.md | head -3
```

Expected output:
```
Review a pull request for unnecessary complexity, brittle test strategies, and overengineering. Produce a local markdown report with findings and actionable recommendations.

## Input
```

- [ ] **Step 4: Commit**

```bash
git add skills/complexity-review/SKILL.md skills/complexity-review/references/command.md
git commit -m "feat(complexity-review): add skill entry point and command symlink"
```

---

### Task 4: Sync skill locally

Use the sync-skill installer to create symlinks for Claude, Agents, and Codex.

**Files:**
- No new files. Creates symlinks at `~/.claude/skills/complexity-review`, `~/.agents/skills/complexity-review`, `~/.codex/skills/complexity-review`.

- [ ] **Step 1: Run the sync-skill installer**

```bash
python3 skills/sync-skill/scripts/install_local_skill.py complexity-review
```

Expected output (three links created or unchanged):
```
claude: created ~/.claude/skills/complexity-review -> /Users/tangj19/Desktop/repos/moi-skills/skills/complexity-review
agents: created ~/.agents/skills/complexity-review -> ~/.claude/skills/complexity-review
codex: created ~/.codex/skills/complexity-review -> ~/.claude/skills/complexity-review
```

- [ ] **Step 2: Verify SKILL.md is readable through the symlink**

```bash
cat ~/.claude/skills/complexity-review/SKILL.md | head -5
```

Expected output:
```
---
name: complexity-review
description: Review a PR for unnecessary complexity, brittle test strategies, and overengineering. Produces a local markdown report with findings and actionable recommendations. Use when the user says "/complexity-review", "review this PR for complexity", or asks to check a PR for overengineering.
---
```

- [ ] **Step 3: Commit (nothing to commit - symlinks are outside the repo)**

No git action needed. Report completion.

---

### Task 5: Sync to remote main

Push the skill to the remote repository via `/sync-main`.

- [ ] **Step 1: Run /sync-main**

```
/sync-main
```

This commits any remaining changes, creates a feature branch, opens a PR, squash-merges, and syncs local main. If `git push` fails, the command falls back to the GitHub Git Data API.

- [ ] **Step 2: Verify the merge**

```bash
git log --oneline -3
```

Expected: the complexity-review commits appear on main.
