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
