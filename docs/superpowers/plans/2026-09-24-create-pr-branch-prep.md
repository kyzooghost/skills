# Create PR Branch Prep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route a user-started `/create-pr` through branch prep that transplants unpushed commits and uncommitted changes onto a new branch, then publish with the existing command.

**Architecture:** `skills/create-pr/SKILL.md` chooses skip, stacked prep, or normal prep. The two prep references own their procedures and do not publish. `commands/create-pr.md` remains the shared publish path. `ship-from-plan` passes `--skip-prep` and otherwise stays unchanged.

**Tech Stack:** Markdown skill and command docs, Python 3 `unittest` string and file checks.

**Spec:** `docs/superpowers/specs/2026-09-24-create-pr-branch-prep-design.md`

## Global Constraints

- Prep runs only for a new pull request the user starts. `--update` and `--skip-prep` skip it.
- Copy unpushed commits and uncommitted changes. Leave the starting checkout unchanged. Do not stash, reset, checkout, or commit there.
- Unpushed commits are `HEAD` commits not on the current branch upstream. With no upstream, they are commits not on `origin/BASE`.
- Copy staged files, unstaged files, and untracked files that Git does not ignore (`git ls-files --others --exclude-standard`). Do not copy ignored files.
- The new branch name is short kebab-case that describes the transplanted changes. It does not reuse the current branch name. If the name exists, append `-2`, `-3`, and so on.
- On normal prep, an explicit `--base <branch>` is both the branch start and the pull request base. When omitted, both use the remote default branch.
- Stacked prep runs only when the user explicitly names an open pull request by number, URL, or branch. Its pull request base is that standing pull request's branch. Ignore `--base`.
- The stacked merge uses a clean worktree of the fetched remote pull request head, not the dirty local branch. Never force-push.
- If `origin/BASE` is already contained in that head, do not create an empty merge commit.
- Every GitHub check on the pushed standing-pull-request head must succeed before the child branch is created. Pending checks keep polling. There is no fixed timeout. An explicit user request to continue despite failing or pending checks skips that wait. A merge conflict never qualifies for the skip.
- Do not auto-fix a standing pull request's failed CI.
- Push the new branch with `--set-upstream` before the shared publish steps. Publish runs in the new worktree.
- Prep references must not contain `gh pr create`.
- `skills/create-pr/references/command.md` stays a symlink to `commands/create-pr.md`.

## File structure

- `skills/create-pr/SKILL.md` — decision and sensitive-content rule. No prep procedure.
- `skills/create-pr/references/normal-prep.md` — normal prep procedure only.
- `skills/create-pr/references/stacked-prep.md` — stacked prep procedure only.
- `commands/create-pr.md` — publish path. Documents `--skip-prep` without owning prep.
- `skills/ship-from-plan/SKILL.md` — adds `--skip-prep` to its `/create-pr` invocation.
- `tests/test_create_pr_command.py` — file and phrase checks.

---

### Task 1: Route the skill

**Files:**
- Modify: `skills/create-pr/SKILL.md`
- Test: `tests/test_create_pr_command.py`

**Interfaces:**
- Consumes: nothing
- Produces: the router phrases `Skip prep`, `--skip-prep`, `references/stacked-prep.md`, and `references/normal-prep.md` for later tests

- [ ] **Step 1: Write the failing test**

Add this method to `CreatePrCommandTest` in `tests/test_create_pr_command.py`:

```python
def test_skill_routes_one_prep_path_before_publish(self) -> None:
    # Arrange
    skill = REPO_ROOT / "skills" / "create-pr" / "SKILL.md"
    required_fragments = (
        "Skip prep",
        "--skip-prep",
        "references/stacked-prep.md",
        "references/normal-prep.md",
        "references/command.md",
    )

    # Act
    text = skill.read_text(encoding="utf-8")

    # Assert
    for fragment in required_fragments:
        with self.subTest(fragment=fragment):
            self.assertIn(fragment, text)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_create_pr_command.CreatePrCommandTest.test_skill_routes_one_prep_path_before_publish -v`

Expected: FAIL because `SKILL.md` does not contain `references/normal-prep.md`.

- [ ] **Step 3: Write the router**

Replace `skills/create-pr/SKILL.md` with:

```markdown
---
name: create-pr
description: Use when the user asks to create, update, draft, or generate a GitHub pull request, including /create-pr behavior or equivalent workflow.
---

# Create PR

Choose exactly one path, then follow `references/command.md` for publish.

1. **Skip prep.** The invocation includes `--update` or `--skip-prep`. Read no prep reference.
2. **Stacked prep.** The user explicitly named an open pull request to stack on, by number, URL, or branch. Read and follow `references/stacked-prep.md`.
3. **Normal prep.** Every other new pull request. Read and follow `references/normal-prep.md`.

On normal prep, resolve `--base` before the branch is created. Stacked prep ignores `--base`. `--draft` stays on the publish path.

Preserve the command behavior exactly, including the preview step before creating or updating a PR.

**Before publishing the PR**, review it (PR descriptions/titles, commit messages, issue/PR comments, code comments, changelog entries) for sensitive content picked up during the chat and strip it out. Never include:

- Internal metrics or impact numbers (error rates, % of users/transactions affected, revenue, analytics results from Mixpanel, Sentry, Grafana, etc.)
- PII or user-identifiable data (names, emails, addresses, transaction hashes, account IDs)
- Incident narratives or details of unfixed/current production issues (what's broken, how to trigger it, who reported it)
- Internal links or names of internal sources (Slack threads, Jira tickets beyond a plain ID, Notion, Zoom, dashboards) and coworker names

Instead, describe the change technically and neutrally - keep incident context out of the PR.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m unittest tests.test_create_pr_command.CreatePrCommandTest.test_skill_routes_one_prep_path_before_publish -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/create-pr/SKILL.md tests/test_create_pr_command.py
git commit -m "$(cat <<'EOF'
docs: route create-pr through one prep path

EOF
)"
```

---

### Task 2: Normal prep reference

**Files:**
- Create: `skills/create-pr/references/normal-prep.md`
- Test: `tests/test_create_pr_command.py`

**Interfaces:**
- Consumes: the router name `references/normal-prep.md`
- Produces: a normal-prep procedure that publishes nothing itself. Later publish uses the branch and base this file selects.

- [ ] **Step 1: Write the failing test**

Add this method to `CreatePrCommandTest`:

```python
def test_normal_prep_transplants_without_publishing(self) -> None:
    # Arrange
    path = REPO_ROOT / "skills" / "create-pr" / "references" / "normal-prep.md"
    required_fragments = (
        "origin/BASE",
        "--base",
        "cherry-pick",
        "git ls-files --others --exclude-standard",
        "Do not stash",
        "git push --set-upstream origin",
        "nothing to publish",
    )
    self.assertTrue(path.is_file())

    # Act
    text = path.read_text(encoding="utf-8")

    # Assert
    self.assertNotIn("gh pr create", text)
    for fragment in required_fragments:
        with self.subTest(fragment=fragment):
            self.assertIn(fragment, text)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_create_pr_command.CreatePrCommandTest.test_normal_prep_transplants_without_publishing -v`

Expected: FAIL because `normal-prep.md` does not exist.

- [ ] **Step 3: Write the reference**

Create `skills/create-pr/references/normal-prep.md` with:

```markdown
# Normal prep

Run this in the starting checkout. Do not publish from this file.

## Select the start ref

Resolve `BASE` with the repository default branch lookup already in `commands/create-pr.md` (`gh repo view` `defaultBranchRef.name`).

An explicit `--base <branch>` replaces `BASE` for both the new branch and the pull request. When `--base` is omitted, both use that default. Fetch it:

```bash
git fetch origin "$BASE"
```

Record `START_REF=origin/$BASE` and `PR_BASE="$BASE"`.

## Select the transplant

Record `SOURCE` as `git rev-parse --show-toplevel` and `SOURCE_HEAD` as `git rev-parse HEAD`.

Unpushed commits are `git rev-list --reverse @{upstream}..HEAD` when the current branch has an upstream. When it has no upstream, they are `git rev-list --reverse origin/$BASE..HEAD`.

Uncommitted changes are staged files, unstaged files, and untracked files that Git does not ignore. List ignored-excluded untracked files with:

```bash
git ls-files --others --exclude-standard
```

If that commit list is empty and `git status --porcelain=v1 -unormal` is empty, stop. There is nothing to publish. Do not create a worktree.

## Name and create the branch

Read the unpushed commits and the uncommitted diff. Choose a short kebab-case branch name that states what those changes do. Do not reuse the current branch name. Example: `fix-ready-pr-default`.

If `refs/heads/<name>` or `refs/remotes/origin/<name>` exists, append `-2`, then `-3`, and so on until the name is free.

Create a worktree at `<repo-parent>/create-pr-worktrees/<name>` from `START_REF`:

```bash
mkdir -p "$(dirname "$WORKTREE")"
git worktree add -b "$BRANCH_NAME" "$WORKTREE" "$START_REF"
```

Do not stash, reset, checkout, or commit in the starting checkout.

## Transplant

In the new worktree, cherry-pick the unpushed SHAs in order:

```bash
git cherry-pick $UNPUSHED_SHAS
```

Skip that command when the SHA list is empty. If cherry-pick conflicts, stop in the new worktree. Do not open the pull request. Do not modify the starting checkout.

Copy the uncommitted tracked diff with `git -C "$SOURCE" diff HEAD` and `git apply` inside the worktree. Copy non-ignored untracked files from `SOURCE` into the worktree with their relative paths. If the copy or apply conflicts, stop in the new worktree. Do not open the pull request.

If the worktree is dirty, run `/commit` there. If the transplant was only commits and the worktree is clean, do not create an empty commit.

## Hand off

Push the new branch, then continue with `commands/create-pr.md` in the new worktree. The pull request base is `PR_BASE`.

```bash
git push --set-upstream origin "$BRANCH_NAME"
```
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m unittest tests.test_create_pr_command.CreatePrCommandTest.test_normal_prep_transplants_without_publishing -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/create-pr/references/normal-prep.md tests/test_create_pr_command.py
git commit -m "$(cat <<'EOF'
docs: add normal create-pr branch prep

EOF
)"
```

---

### Task 3: Stacked prep reference

**Files:**
- Create: `skills/create-pr/references/stacked-prep.md`
- Test: `tests/test_create_pr_command.py`

**Interfaces:**
- Consumes: the same transplant and branch-name rules as `normal-prep.md`
- Produces: a standing-pull-request update, then a child branch whose publish base is that pull request's branch

- [ ] **Step 1: Write the failing test**

Add this method to `CreatePrCommandTest`:

```python
def test_stacked_prep_updates_the_remote_pr_before_the_child_branch(self) -> None:
    # Arrange
    path = REPO_ROOT / "skills" / "create-pr" / "references" / "stacked-prep.md"
    required_fragments = (
        "origin/$PR_BRANCH",
        "Do not force-push",
        "already up to date",
        "statusCheckRollup",
        "mergeStateStatus",
        "failing or pending checks",
        "merge conflict",
        "git push --set-upstream origin",
    )
    self.assertTrue(path.is_file())

    # Act
    text = path.read_text(encoding="utf-8")

    # Assert
    self.assertNotIn("gh pr create", text)
    for fragment in required_fragments:
        with self.subTest(fragment=fragment):
            self.assertIn(fragment, text)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_create_pr_command.CreatePrCommandTest.test_stacked_prep_updates_the_remote_pr_before_the_child_branch -v`

Expected: FAIL because `stacked-prep.md` does not exist.

- [ ] **Step 3: Write the reference**

Create `skills/create-pr/references/stacked-prep.md` with:

```markdown
# Stacked prep

Run this only when the user explicitly asks to stack on an open pull request and names it by number, URL, or branch. Do not publish from this file. Ignore `--base`.

## Update the standing pull request

Resolve the pull request:

```bash
gh pr view "$PR_REF" --json number,headRefName,url
```

Record `PR_NUMBER` and `PR_BRANCH` (`headRefName`). Fetch that branch. Leave the starting checkout unchanged.

```bash
git fetch origin "$PR_BRANCH"
```

Create a detached worktree at `<repo-parent>/create-pr-worktrees/stack-update-$PR_NUMBER` from `origin/$PR_BRANCH`. Do not check out the dirty local branch.

```bash
git worktree add --detach "$STACK_WORKTREE" "origin/$PR_BRANCH"
```

In that worktree, merge the remote default branch. Resolve `BASE` the same way `commands/create-pr.md` resolves the repository default, then:

```bash
git fetch origin "$BASE"
git merge "origin/$BASE" -m "merge: update with latest $BASE"
```

If Git reports already up to date, do not create an empty merge commit. If the merge conflicts, resolve the conflicts and commit that resolution. If the conflict cannot be resolved, stop in this worktree. Do not push a conflicted tree.

Push only that merge or conflict-resolution commit to the standing pull request. Do not push the user's unpushed commits or uncommitted files. Do not force-push.

```bash
git push origin "HEAD:refs/heads/$PR_BRANCH"
```

## Wait for the quality gate

Poll with:

```bash
gh pr view "$PR_NUMBER" --json statusCheckRollup,mergeStateStatus
```

There is no fixed poll timeout.

- `mergeStateStatus` of `DIRTY` is a merge conflict. Stop. Do not create the child branch. The user cannot override this stop.
- `mergeStateStatus` of `UNKNOWN` means GitHub is still calculating. Poll again.
- An empty `statusCheckRollup` satisfies the CI part of the gate.
- A check passes when its conclusion is `SUCCESS`, `SKIPPED`, or `NEUTRAL`.
- A conclusion of `FAILURE`, `CANCELLED`, `TIMED_OUT`, or `ACTION_REQUIRED` stops prep.
- A check with no conclusion yet is pending. Keep polling.
- When the user explicitly asks to continue despite failing or pending checks, skip the CI wait. Still stop on `mergeStateStatus` `DIRTY`.

Do not auto-fix the standing pull request's CI.

## Create the child branch

Fetch `origin/$PR_BRANCH` again. Create the child branch from that updated remote head, in a new worktree at `<repo-parent>/create-pr-worktrees/<child-name>`.

Name the child from the transplanted changes, using the same kebab-case rule as `normal-prep.md`. Do not reuse the current branch name. Append `-2`, `-3`, and so on when the name exists.

Copy only the user's unpushed commits and uncommitted changes from the starting checkout. Use the same unpushed, untracked, cherry-pick, and copy rules as `normal-prep.md`. Do not stash or otherwise modify the starting checkout. If cherry-pick or copy conflicts, stop in the child worktree and do not open the pull request.

If the child worktree is dirty, run `/commit` there. Do not create an empty commit.

If there is nothing to transplant, stop. There is nothing to publish.

Push, then continue with `commands/create-pr.md` in the child worktree. The pull request base is `PR_BRANCH`.

```bash
git push --set-upstream origin "$BRANCH_NAME"
```
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m unittest tests.test_create_pr_command.CreatePrCommandTest.test_stacked_prep_updates_the_remote_pr_before_the_child_branch -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/create-pr/references/stacked-prep.md tests/test_create_pr_command.py
git commit -m "$(cat <<'EOF'
docs: add stacked create-pr branch prep

EOF
)"
```

---

### Task 4: Document the skip flag on the publish command

**Files:**
- Modify: `commands/create-pr.md`
- Test: `tests/test_create_pr_command.py`

**Interfaces:**
- Consumes: `--skip-prep` from the router
- Produces: usage text that keeps the existing `--draft` and `--update` lines and adds `--skip-prep`

- [ ] **Step 1: Write the failing test**

Add this method to `CreatePrCommandTest`:

```python
def test_publish_command_documents_skip_prep(self) -> None:
    # Arrange
    required_fragments = (
        "--skip-prep",
        "/create-pr [--base <branch>] [--draft]",
        "/create-pr --update [--base <branch>]",
        'gh pr create --base "$BASE_BRANCH" --draft',
    )

    # Act
    command = COMMAND.read_text(encoding="utf-8")

    # Assert
    for fragment in required_fragments:
        with self.subTest(fragment=fragment):
            self.assertIn(fragment, command)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_create_pr_command.CreatePrCommandTest.test_publish_command_documents_skip_prep -v`

Expected: FAIL because `commands/create-pr.md` does not contain `--skip-prep`.

- [ ] **Step 3: Document the flag**

In `commands/create-pr.md`, keep the existing usage lines and add a third line plus one bullet:

```text
/create-pr [--base <branch>] [--draft]
/create-pr [--base <branch>] [--draft] [--skip-prep]
/create-pr --update [--base <branch>]
```

Add this bullet after the `--draft` bullet:

```markdown
- `--skip-prep` skips branch prep. `--update` skips branch prep too. This command does not create the prep worktree. When prep already ran, publish from the prep worktree and its branch.
```

Do not add cherry-pick, worktree, or CI-poll steps to this file.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_create_pr_command -v`

Expected: PASS, including `test_command_supports_draft_creation_but_rejects_draft_updates` and `test_packaged_skill_uses_the_canonical_command`.

- [ ] **Step 5: Commit**

```bash
git add commands/create-pr.md tests/test_create_pr_command.py
git commit -m "$(cat <<'EOF'
docs: document create-pr skip-prep flag

EOF
)"
```

---

### Task 5: Skip prep from ship-from-plan

**Files:**
- Modify: `skills/ship-from-plan/SKILL.md:96`
- Test: `tests/test_create_pr_command.py`

**Interfaces:**
- Consumes: `--skip-prep` from Task 4
- Produces: a ship-from-plan invocation that still passes `--base` only when the user supplied `BASE_BRANCH`, and still omits `--draft`

- [ ] **Step 1: Write the failing test**

Add this method to `CreatePrCommandTest`:

```python
def test_ship_from_plan_skips_create_pr_prep(self) -> None:
    # Arrange
    skill = REPO_ROOT / "skills" / "ship-from-plan" / "SKILL.md"

    # Act
    text = skill.read_text(encoding="utf-8")

    # Assert
    self.assertIn("/create-pr --skip-prep", text)
    self.assertIn('Add `--base "$BASE_BRANCH"` only when the user supplied `BASE_BRANCH`', text)
    self.assertNotIn("/create-pr --draft", text)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_create_pr_command.CreatePrCommandTest.test_ship_from_plan_skips_create_pr_prep -v`

Expected: FAIL because the invocation is `/create-pr` without `--skip-prep`.

- [ ] **Step 3: Pass the flag**

In `skills/ship-from-plan/SKILL.md`, replace the invoke sentence with:

```markdown
Invoke `/create-pr --skip-prep` without `--draft`. Add `--base "$BASE_BRANCH"` only when the user supplied `BASE_BRANCH`; otherwise allow `/create-pr` to resolve the configured repository default. Standing authorization covers its routine preview and any AI-resolvable `/doc-update` changes. Preserve create-PR sensitive-content scrubbing.
```

Change no other ship-from-plan behavior.

- [ ] **Step 4: Run the full test module**

Run: `python3 -m unittest tests.test_create_pr_command -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/ship-from-plan/SKILL.md tests/test_create_pr_command.py
git commit -m "$(cat <<'EOF'
docs: skip create-pr prep from ship-from-plan

EOF
)"
```
