# Deterministic PR Review Comment Posting Helper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic Python CLI that safely posts approved primary and companion GitHub review comments without shell interpolation or broken primary links.

**Architecture:** A JSON spec describes the approved rendered bodies and exact diff anchors. The CLI validates the entire spec before mutation, invokes `gh api` through `subprocess.run` argument arrays, captures the primary comment URL, substitutes it into companion templates, and verifies every response before continuing. Unit tests inject a fake runner at the `gh` boundary.

**Tech Stack:** Python 3 standard library, `argparse`, `json`, `subprocess`, and `unittest` only.

---

### Task 1: Define the spec and validation contract

**Files:**
- Create: `skills/pr-review-comments/scripts/post_review_comments.py`
- Test: `tests/test_post_review_comments.py`

- [x] **Step 1: Write the failing posting test**

Create a test spec with Markdown backticks, a primary target, and one companion whose body ends in `See primary comment: {primary_url}`. Use a fake runner returning deterministic primary and companion responses. Assert the result preserves the backticks and replaces the token with the real primary URL.

- [x] **Step 2: Run the focused test and verify the expected RED failure**

Run: `python3 -m unittest tests.test_post_review_comments.PostReviewCommentsTest.test_posts_companion_with_real_primary_url_and_preserves_markdown -v`

Expected: FAIL because `skills/pr-review-comments/scripts/post_review_comments.py` does not exist.

- [x] **Step 3: Implement the validation contract**

Add `load_spec`, `validate_spec`, and immutable target representations. Require a non-empty repository, positive PR and line numbers, a 40-character commit SHA, one primary target, and companion bodies with exactly one `{primary_url}` token and matching first-line titles. Reject `$primary_url`, angle-bracket primary placeholders, and unresolved `{owner}`, `{repo}`, `{pr}`, or `{id}` markers before any runner call.

- [x] **Step 4: Re-run the focused test and verify the next RED failure**

Run the same focused test. Expected: FAIL at the posting boundary because no runner invocation exists yet, confirming the intended spec passes validation.

- [x] **Step 5: Commit the contract tests**

```bash
git add tests/test_post_review_comments.py
git commit -m "test: define review comment posting contract"
```

### Task 2: Implement deterministic posting and response validation

**Files:**
- Modify: `skills/pr-review-comments/scripts/post_review_comments.py`
- Test: `tests/test_post_review_comments.py`

- [x] **Step 1: Add failing tests for dry-run and fail-fast behavior**

Add one AAA test that verifies `dry_run=True` validates without invoking the runner. Add one test that returns a mismatched primary body and asserts `PostReviewCommentsError` before any companion call. Add one test that returns a mismatched first companion response and asserts no later companion call occurs.

- [x] **Step 2: Run the focused tests and verify RED failures**

Run: `python3 -m unittest tests.test_post_review_comments -v`

Expected: FAIL because posting and response validation are not implemented.

- [x] **Step 3: Implement the `gh api` boundary**

Implement `post_review_comments(spec, runner=run_gh_api, dry_run=False)` and `run_gh_api(args)`. Build argument arrays equivalent to `gh api repos/{repo}/pulls/{pr}/comments -f body={body} -f path={path} -F line={line} -f side=RIGHT -f commit_id={commit}`. Use `subprocess.run(args, check=False, capture_output=True, text=True)` with no shell string. Parse JSON, require a real GitHub discussion URL, and compare returned body, path, and line with submitted values. Replace `{primary_url}` only after the primary response passes validation. Verify every companion footer equals `See primary comment: <primary URL>` before posting the next target. Return responses in posting order.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run: `python3 -m unittest tests.test_post_review_comments -v`

Expected: all helper tests pass with no shell errors.

- [x] **Step 5: Commit the implementation and tests**

```bash
git add skills/pr-review-comments/scripts/post_review_comments.py tests/test_post_review_comments.py
git commit -m "feat: add deterministic review comment poster"
```

### Task 3: Add the CLI and integrate the skill instructions

**Files:**
- Modify: `skills/pr-review-comments/scripts/post_review_comments.py`
- Modify: `skills/pr-review-comments/SKILL.md`
- Test: `tests/test_post_review_comments.py`

- [x] **Step 1: Add failing CLI tests**

Create a temporary JSON spec and invoke the script with `--dry-run`; assert exit code zero, target summary output, and no runner dependency. Add an unresolved-placeholder case that asserts exit code one and an actionable stderr message.

- [x] **Step 2: Run the CLI tests and verify RED**

Run: `python3 -m unittest tests.test_post_review_comments -v`

Expected: FAIL for the missing command-line entry point.

- [x] **Step 3: Implement CLI parsing and skill integration**

Add `--spec` and `--dry-run`, print posted URLs or validated targets, and return exit code one for `PostReviewCommentsError`. Update the skill procedure and API section to require the helper for primary and companion posting, include the JSON spec shape, and explicitly forbid unquoted shell heredocs or shell command strings for Markdown bodies. Preserve the existing approval and issue-creation gates.

- [x] **Step 4: Run the CLI and full unit suite**

```bash
python3 -m unittest tests.test_post_review_comments -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass with no warnings or shell errors.

- [x] **Step 5: Commit the CLI and skill documentation**

```bash
git add skills/pr-review-comments/scripts/post_review_comments.py skills/pr-review-comments/SKILL.md tests/test_post_review_comments.py
git commit -m "docs: route review comment posting through validator"
```

### Task 4: Final verification and handoff

**Files:**
- Verify: `docs/superpowers/specs/2026-07-21-pr-review-comments-post-helper-design.md`
- Verify: `docs/superpowers/plans/2026-07-21-pr-review-comments-post-helper.md`
- Verify: `skills/pr-review-comments/scripts/post_review_comments.py`
- Verify: `skills/pr-review-comments/SKILL.md`
- Verify: `tests/test_post_review_comments.py`

- [ ] **Step 1: Run repository checks**

```bash
python3 -m unittest discover -s tests -v
git diff --check origin/main...HEAD
```

Expected: all tests pass and `git diff --check` emits no output.

- [ ] **Step 2: Audit shell safety and placeholders**

Run: `rg -n "shell=True|cat <<EOF|\\$primary_url|primary html_url inserted|{owner}|{repo}|{pr}|{id}" skills/pr-review-comments/scripts/post_review_comments.py skills/pr-review-comments/SKILL.md`

Expected: no unsafe shell construction or unresolved placeholder instructions remain in the helper workflow; rejection tests may mention rejected markers only in the test file.

- [ ] **Step 3: Confirm exact changed files and a clean worktree**

```bash
git diff --name-only origin/main...HEAD
git status --short --branch
```

Expected: only the design, plan, helper, skill, and unit-test files are changed, with no generated `__pycache__` files tracked or left in the worktree.
