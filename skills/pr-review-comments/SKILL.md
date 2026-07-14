---
name: pr-review-comments
description: Transform security review findings into targeted GitHub PR review comments. Takes a single finding from a differential review report and produces actionable, file-targeted PR review comments using the GitHub API (gh). Use when the user says "/pr-review-comments", "post review comments", "turn findings into PR comments", "post this finding", or asks to convert a security/code review finding into inline PR comments. Two formats - LOW (single code suggestion + concise explanation) and HIGH (architectural diagram + multi-file companion comments).
---

# PR Review Comments

Transform a single security review finding into targeted, actionable GitHub PR review comments.

## Input

The user provides:
1. A **finding** from a differential review report (raw text or reference to a finding ID like "F1", "L1")
2. The **PR number** and **repo** (or infer from current branch/context)
3. The **commit SHA** to anchor comments on (use HEAD of the PR branch)

## Output Formats

Two templates depending on complexity:

### Format A: Single-target fix (LOW/MEDIUM findings)

For findings where the fix is one code change in one location.

Structure:
1. GitHub suggestion block with the fix
2. Bold severity+title: `**[LOW-N] Title that captures the issue**`
3. 2-4 sentences: what's wrong, why it matters, why severity is bounded

Post as a **single PR review comment** targeting the exact file + line.

Example shape:
````
```suggestion
<fixed code>
```

**[LOW-1] TTL evictions share a 2-thread pool with 2PC timeouts**

BundleStatusStore schedules TTL eviction tasks on the same 2-thread `xcall-circ` pool used for 2PC session timeouts. A burst of terminal bundles can queue evictions that delay timeout firing. Risk is low - each eviction is near-zero work and impact is liveness only. Isolate to a dedicated single-thread executor.
````

Rules:
- Title: `[SEVERITY-N]` + noun phrase capturing the defect (not the fix)
- Every word earns its place - reader should absorb the issue in <10 seconds
- No "Recommended fix" section - the suggestion block IS the fix
- Bound the risk in the description (why it's LOW not HIGH)

### Format B: Multi-file architectural issue (HIGH findings)

For findings requiring structural changes across multiple files.

Structure for the **primary comment** (on the most relevant file/line):
1. Suggestion block with the key fix for THIS file
2. Bold severity+title: `**[HIGH-N] - Title**`
3. Explanation of the two/three gaps that chain together
4. ASCII diagrams showing: normal flow, attack/failure flow, information loss
5. TL;DR block: What / Why / Impact / Fix

Post **companion comments** on each additional file that needs changes:
1. Suggestion block with that file's fix (if applicable)
2. Same bold severity+title (links the comments together)
3. Link to the primary comment's actual URL (from the `html_url` returned when posting the primary): `See https://github.com/{owner}/{repo}/pull/{pr}#discussion_r{id}`

For supplementary code changes too large for a suggestion block, post a companion comment with a fenced code block showing the required changes and a mini ASCII diagram of the data flow that must be threaded through.

### Format C: Test coverage gap (`[TEST GAP]`)

For requesting missing tests - no suggestion block needed.

Structure:
1. Bold title: `**[TEST GAP] Title describing what's not covered**`
2. Numbered list of specific missing behaviors, each with:
   - What production code can be deleted/mutated without failing tests
   - What the test should assert
3. Note on feasibility (can it be done with existing harness or does it depend on unimplemented features)

Anchor on the test file (last line or near the gap) rather than production code.

## Procedure

1. **Identify the finding** from the review report
2. **Classify**: single-target (Format A) or multi-file (Format B)
3. **Locate the exact file + line** in the PR diff where the comment anchors
   - Use `gh api repos/{owner}/{repo}/pulls/{pr}/files` to get the diff
   - Use `gh api repos/{owner}/{repo}/contents/{path}?ref={sha}` if needed
4. **STOP - Show the user the draft** comment(s) and target file/line for approval before posting. Display:
   - Target: `{path}:{line}`
   - Format: A or B
   - Full comment body (rendered)
   - For Format B: list all companion comment targets
   - Wait for explicit user approval before proceeding
5. **Post via GitHub API** (only after user approval):
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pr}/comments \
     -f body="<comment>" \
     -f path="<file>" \
     -F line=<line> \
     -f side="RIGHT" \
     -f commit_id="<sha>"
   ```
6. For Format B, post companion comments on secondary files, linking back to the primary (also requires approval in step 4)

## Writing Rules

- **Concise**: reader decides in <30 seconds whether to act
- **No filler**: cut "it would be preferable to" - just state the fix
- **Bound risk**: always state why severity is what it is (not higher)
- **Diagrams over prose**: for anything involving data flow, control flow, or timing - draw it
- **Suggestion blocks must compile**: test mentally that the suggestion is syntactically valid
- **One finding = one comment thread**: don't combine findings
- **No bare `#N` in prose**: GitHub auto-links `#N` to issues/PRs. Write the number without `#` prefix (e.g. "violation 2" not "violation #2"). Ticket references like `#4332` are fine when you intend the link.

## GitHub API Details

For review comments on specific lines:
```bash
# Single comment
gh api repos/{owner}/{repo}/pulls/{pr}/comments \
  -f body="$BODY" \
  -f path="path/to/file.java" \
  -F line=42 \
  -f side="RIGHT" \
  -f commit_id="abc123"

# Multi-line comment (for suggestion spanning lines)
gh api repos/{owner}/{repo}/pulls/{pr}/comments \
  -f body="$BODY" \
  -f path="path/to/file.java" \
  -F start_line=40 \
  -F line=45 \
  -f start_side="RIGHT" \
  -f side="RIGHT" \
  -f commit_id="abc123"
```

For a general PR comment (non-inline, e.g. summary):
```bash
gh api repos/{owner}/{repo}/issues/{pr}/comments -f body="$BODY"
```

## Diagram Style (Format B)

Use box-drawing characters for sequence/architecture diagrams:
```
┌─────────┐          ┌─────────┐
│ Component│──verb──> │Component│
└─────────┘          └─────────┘
```

Show the gap clearly:
```
StreamManager              EezDisconnectAborter
┌──────────────┐           ┌──────────────────┐
│ HAS context  │── only ──>│ LOST context     │
│ (in closure) │  passes   │ (cannot check)   │
└──────────────┘  partial  └──────────────────┘
```

## Checklist Before Posting

- [ ] Suggestion block is syntactically valid code
- [ ] Line number targets a line that exists in the PR diff (RIGHT side)
- [ ] Commit SHA matches the PR head
- [ ] Title captures the DEFECT (not the fix)
- [ ] Risk is bounded in the description
- [ ] For Format B: all companion comments link back to primary
