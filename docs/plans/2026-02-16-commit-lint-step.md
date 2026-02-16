# Commit Lint Step Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a linting pre-step to the `/commit` command so lint runs before committing, with auto-fix and re-staging.

**Architecture:** Single edit to `commands/commit.md` - insert a new step 6 with sub-steps describing project detection, lint command discovery, execution, and re-staging. Renumber current step 6 to 7.

**Tech Stack:** Markdown (command definition file)

---

### Task 1: Insert lint step and renumber

**Files:**
- Modify: `commands/commit.md:22-23`

**Step 1: Edit commit.md**

Replace lines 22-23 (current steps 5-6):

```
5. If multiple distinct changes are detected, suggests breaking the commit into multiple smaller commits
6. For each commit (or the single commit if not split), creates a commit message
```

With:

```
5. If multiple distinct changes are detected, suggests breaking the commit into multiple smaller commits
6. For each distinct logical change, checks for and runs project linting:
   a. For each group of changed files, walk up the directory tree to find the nearest `package.json` (TS/JS) or `build.gradle`/`build.gradle.kts` (Gradle). Deduplicate so each project is linted only once.
   b. **TS/JS projects:** Read the nearest `package.json` `scripts` field. If `lint:fix` exists, run it (e.g., `npm run lint:fix`). Otherwise if `lint` exists, run that. If neither exists, skip.
   c. **Gradle projects:** Check `build.gradle` or `build.gradle.kts` for lint-related task definitions. If found, run the matching task via `./gradlew <task>` from that project directory.
   d. If linting produces auto-fixes, re-stage the fixed files with `git add` before proceeding.
   e. If no lint command is found for a project, skip silently - this is fine.
7. For each commit (or the single commit if not split), creates a commit message
```

**Step 2: Verify the edit**

Read `commands/commit.md` and confirm:
- Steps 1-5 are unchanged
- New step 6 has sub-steps a-e
- Old step 6 is now step 7
- No other content was modified

**Step 3: Commit**

```bash
git add commands/commit.md
git commit -m "feat: add lint step to commit command"
```
