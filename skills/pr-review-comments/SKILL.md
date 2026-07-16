---
name: pr-review-comments
description: Transform security review findings into targeted GitHub PR review comments. Takes a single finding from a differential review report and produces actionable, file-targeted PR review comments using the GitHub API (gh). Use when the user says "/pr-review-comments", "post review comments", "turn findings into PR comments", "post this finding", or asks to convert a security/code review finding into inline PR comments. Three formats - Format A (single code suggestion + concise explanation, LOW), Format B (concise what's-wrong + Fix with a collapsed detail block and stub companions, explicit "in this PR" vs "follow-up ticket" split for MEDIUM/HIGH multi-file findings), and Format C (test coverage gaps).
---

# PR Review Comments

Transform a single security review finding into targeted, actionable GitHub PR review comments.

## Input

The user provides:
1. A **finding** from a differential review report (raw text or reference to a finding ID like "F1", "L1")
2. The **PR number** and **repo** (or infer from current branch/context)
3. The **commit SHA** to anchor comments on (use HEAD of the PR branch)

## Output Formats

Three templates depending on complexity:

### Format A: Single-target fix (LOW findings, or MEDIUM where the fix is trivially self-contained)

For findings where the fix is one code change in one location AND the recommendation does not need to be split between this PR and a follow-up ticket. If either condition fails, use Format B.

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

### Format B: Multi-file architectural issue (MEDIUM/HIGH findings)

For findings requiring structural changes across multiple files, or where the recommendation splits between "fix in this PR" and "track in a follow-up ticket."

**Primary comment - three parts, fixed order:**

````
**[SEVERITY-N] Title that captures the defect**

<What's wrong: 2-4 sentences, plain English. What breaks, when it breaks, why
it matters. No citations, no diagrams.>

**Fix**

- **In this PR (#TICKET, omit if none):** <one-line summary of the in-PR change, then the
  ```suggestion``` block if the fix is a small self-contained change on this
  file. If no code change is needed on this file, say so and point at the
  file/line where the in-PR fix lands.>
- **Follow-up ticket (new, or scope-expansion of #TICKET):** <one line: what
  splits out and why it does not fit this PR>

<details>
<summary>Problem detail and follow-up scope</summary>

<Citations (file:line), ASCII diagram, end-to-end failure scenario,
exploitability bound, the full description of an in-PR fix too large for a
suggestion block, and the numbered follow-up task list the ticket must
cover (include tests and preconditions on other tickets). Nothing here
restates the Fix bullets or the what's-wrong intro - this block only adds
evidence and task breakdown.>

</details>
````

**Where the ```suggestion``` block lives.**
- If the in-PR fix is a small, self-contained code change on the file this
  comment anchors: inside the "In this PR" bullet, so the code and its
  rationale sit together at the top.
- Even "add an inline comment / TODO / marker" recommendations go in a
  ```suggestion``` block, containing the exact edited line(s) - never as
  prose. The reader should be one click away from applying the change.
- If the fix is too large for a suggestion block, or spans multiple
  non-contiguous edits: the "In this PR" bullet carries a one-line summary;
  the full description (fenced code block or ASCII diagram) goes inside
  `<details>`.
- Never put a ```suggestion``` block inside `<details>` - GitHub's apply
  button and scanning reviewers must see it above the fold.

**`<details>` conventions.**
- Summary line is always `Problem detail and follow-up scope`.
- Leave a blank line after `<summary>...</summary>` and before `</details>`
  so GitHub renders the markdown inside.
- Diagrams live only inside `<details>`.

**Companion comments.** Post a stub on each additional file:

````
**[SEVERITY-N] Exact same title as the primary - verbatim**

<1-2 sentences: this file's specific angle on the finding.>

<```suggestion``` block, only if this file carries an in-PR fix>

See primary comment: https://github.com/{owner}/{repo}/pull/{pr}#discussion_r{id}
````

- No Fix section, no `<details>`, no problem detail. Site-specific reasoning
  that needs depth goes into the primary's `<details>` block instead.
- Title is the primary's `**[SEVERITY-N] ...**` title verbatim - no
  sub-title, no rewording. A reader scanning the PR must instantly recognize
  the comments as one finding. The companion's specific angle (driver-side /
  test-side / follow-up anchor / etc.) is expressed in the 1-2 sentence
  intro, NOT in the title.
- The footer uses the primary's real `html_url`.
- The only exception is `[TEST GAP]` companions, which by convention use
  their own `**[TEST GAP] ...**` marker (a different severity category). They
  still end with a `See primary comment:` link.

The primary is the comment on the file/line where the defect is most
concentrated; companions cover other affected files and can also "anchor" the
follow-up ticket at the driver-side / consumer-side landing zone even when no
in-PR code change happens there.

**Worked example - primary:**

````
**[MEDIUM-1] Follower loop bypasses the required proxy and system-address execution contexts**

Once an operator flips `--plugin-xcall-eez-fixpoint-loop-enabled=true`, any inbound cross-chain call with a nested callback fails. The follower's subsequent simulation is sent from the remote wire caller, but the L2 contract accepts it only from `SYSTEM_ADDRESS` with exact `msg.value`. The first pass has the mirror-image problem: no source-proxy derivation, no dispatcher-code install, no static-call enforcement.

**Fix**

- **In this PR (#4333):** fail startup when `--plugin-xcall-eez-fixpoint-loop-enabled=true` until the follower-pass override substrate is threaded through the loop seam. See `XCallPlugin.java:254` companion for the exact suggestion.
- **Follow-up ticket (new, or scope-expansion of #4342):** wire both follower passes through the execution contexts `EezSimulator` already implements - too large for this PR; task breakdown in the details block.

<details>
<summary>Problem detail and follow-up scope</summary>

Two gaps chain together:

1. **First pass (`FixpointLoopDriver.buildFollowerCall` L815-820, invoked at L534):** calls `originalAddress` directly from the remote wire `caller` - no canonical source proxy, no dispatcher runtime, no manager sender, no funding. A `STATIC` inbound executes as an ordinary call.
2. **Subsequent pass (this planner L75-116, invoked at `FixpointLoopDriver` L578-579):** sends `executeIncomingCrossChainCall` from the remote `caller` with `Optional.empty()` overrides. `EEZL2.sol:332-347` requires `SYSTEM_ADDRESS` (`onlySystemAddress`) and `msg.value == value` (`ValueMismatch`).

`EezSimulator.java:98-150` already implements both contexts - the newly wired loop does not use it.

```
planner.planNextPass ──> SimpleCallParameter(caller, manager, value, calldata)
simulator.simulateCall(nextCall, Optional.empty())
                  ├─> onlySystemAddress  REVERT
                  └─> msg.value == value REVERT
                        └─> final SimulateResponse = FAILED
```

**Failure scenario.** An authenticated peer sends a non-static inbound whose first pass discovers a callback. The loop calls this planner, runs the returned call with empty overrides, and `onlySystemAddress` rejects immediately. The loop returns that infrastructure failure as the final `SimulateResponse`. Not reachable while the flag defaults to false; one authenticated peer message suffices once it is enabled.

**Follow-up ticket scope:**
1. Widen `FollowerReSimulationPlanner` so `planNextPass` returns both `CallParameter` and `StateOverrideMap`.
2. Thread `StateOverrideMap` through `LoopSimulator.simulateCall` at `FixpointLoopDriver.java:534` and `:579`.
3. Replace direct `SimpleCallParameter` construction (driver L815-820, planner L116) with delegation to `EezSimulator.followerFirstSimulate` / `followerSubsequentSimulate`.
4. Add an integration test exercising the on-chain `onlySystemAddress` + `ValueMismatch` boundary.
5. Enable the flag in production only after this ticket and #4342 land.

</details>
````

**Worked example - companion carrying the in-PR fix:**

````
**[MEDIUM-1] Follower loop bypasses the required proxy and system-address execution contexts**

In-PR landing zone: enabling the loop today gives operators a driver that fails at the first nested-callback inbound, so refuse to boot instead of constructing a partially functional planner.

```suggestion
      cliOptions.validateEezFixpointLoopOptions();
      // MEDIUM-1: refuse to construct the loop until the follower-pass state-override
      // substrate is threaded through FollowerReSimulationPlanner and LoopSimulator.
      throw new IllegalStateException(
          "EEZ fixpoint loop cannot be enabled: follower-pass system-address / funding /"
              + " proxy-context substrate is not yet wired through the LoopSimulator seam.");
```

See primary comment: https://github.com/{owner}/{repo}/pull/{pr}#discussion_r{id}
````

### Format C: Test coverage gap (`[TEST GAP]`)

For requesting missing tests - no suggestion block needed.

Structure:
1. Bold title: `**[TEST GAP] Title describing what's not covered**`
2. Numbered list of specific production behaviors that have no test catching their removal:
   - Which production code path is untested (file + line reference)
   - What the test should assert to cover it
3. Note on feasibility (can it be done with existing harness or does it depend on unimplemented features)

Framing: "this behavior is untested" / "no test would catch removal of X" - NOT "delete this production code."

Anchor on the test file (last line or near the gap) rather than production code.

## Procedure

1. **Identify the finding** from the review report
2. **Classify**:
   - Format A (single-target): fix is one code change in one location, no split between "this PR" and "follow-up ticket."
   - Format B (multi-file / split-scope): defect spans multiple files OR the recommendation naturally splits into "in this PR" (small, contained) plus "follow-up ticket" (architectural). Use Format B whenever you'd otherwise need to explain "this fix is only partial" - the **Fix** section's two bullets make the split explicit.
   - Format C: test coverage gap.
3. **Locate the exact file + line** in the PR diff where the comment anchors
   - Use `gh api repos/{owner}/{repo}/pulls/{pr}/files` to get the diff
   - Use `gh api repos/{owner}/{repo}/contents/{path}?ref={sha}` if needed
4. **Decide the split** (Format B only): before drafting, name the in-PR change (concrete, small, landable now) and the follow-up ticket scope (architectural, out-of-scope for this PR). If you cannot cleanly name both, either expand the in-PR scope until it stands alone (making the "In this PR" bullet the whole fix) or step down to Format A.
5. **STOP - Show the user the draft** comment(s) and target file/line for approval before posting. Display:
   - Target: `{path}:{line}`
   - Format: A, B, or C
   - Full comment body (rendered, including the `<details>` block content for Format B)
   - For Format B: list all companion comment targets
   - Wait for explicit user approval before proceeding
6. **Post via GitHub API** (only after user approval):
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pr}/comments \
     -f body="<comment>" \
     -f path="<file>" \
     -F line=<line> \
     -f side="RIGHT" \
     -f commit_id="<sha>"
   ```
7. For Format B, post the primary first, capture its `html_url`, then substitute that URL into each companion's "See primary comment:" footer before posting the companions.

## Writing Rules

- **Concise**: reader decides in <30 seconds whether to act
- **Every word earns its place above the fold (Format B).** Everything outside `<details>` - title, what's-wrong intro, and **Fix** - is what a 0-context reader uses to decide whether to act. Depth belongs inside `<details>`. Apply this discipline hard:
  - **No "In plain terms:", "Basically,", "Essentially," preambles.** The section is plain English by convention. Just state the defect.
  - **No adjectives that repeat the setup.** "Silent narrowing" when the whole point is that it's silent → drop "silent". "Weak size-only assertions" when the whole comment argues weakness → drop "Weak".
  - **Positive framing over negative.** "so X can find them" beats "otherwise X cannot find them". "no `SimulateResponse` sent" beats "without sending any `SimulateResponse`".
  - **Merge adjacent clauses when they share a subject.** "It ONLY asks for direct children and it emits ..." → "It only asks for its direct children and emits ...".
  - **Parallel structure** for three-item lists. "no source-proxy derivation, no dispatcher-code install, no static-call enforcement" reads faster than "it skips X, Y, and Z".
  - **Numeric ranges: use power notation.** `[2^31, 2^32-1]` beats `[2,147,483,648, 4,294,967,295]` - readers scan the exponent instantly.
  - **Drop qualifiers that are obvious from the frame.** "one small change" as a hint that the in-PR fix is small is unnecessary if the suggestion block is already visible. "the review's clause" > "This is the ... clause of the review".
  - **Cut over "however", "as-is", "specifically", "actually".** These usually add length without content. If the contrast is real, the reader picks it up from the substance.
  - **Read the above-the-fold text out loud once.** If you stumble on a clause, rewrite it. If you re-read a sentence to parse it, split it.
- **No filler**: cut "it would be preferable to" - just state the fix
- **Bound risk**: always state why severity is what it is (not higher)
- **Diagrams over prose**: for anything involving data flow, control flow, or timing - draw it
- **Suggestion blocks must compile**: test mentally that the suggestion is syntactically valid
- **One finding = one comment thread**: don't combine findings
- **Split scope explicitly**: for any non-trivial finding, name what lands in THIS PR vs what splits to a follow-up ticket. Reviewers should never have to guess whether a recommendation is blocking merge.
- **Structure is fixed for Format B**: title + what's-wrong intro → **Fix** → `<details>`. Do not reorder. The intro is plain English; save citations, diagrams, and failure scenarios for the `<details>` block.
- **No duplication across the fold (Format B)**: each point appears exactly once - above the fold or inside `<details>`, never both. The `<details>` block adds evidence and the follow-up task breakdown; it never restates the Fix bullets.
- **Suggestion block placement (Format B)**: if the in-PR fix is a small self-contained code change on the file this comment anchors, put the ```suggestion``` block inside the "In this PR" bullet of **Fix**. Never inside `<details>`.
- **No bare `#N` in prose**: GitHub auto-links `#N` to issues/PRs. Write the number without `#` prefix (e.g. "violation 2" not "violation #2") EXCEPT when quoting a real ticket reference like `#4342`.
- **Preamble discipline for suggestion blocks**: never precede a ```suggestion``` block with a "Suggested code:" or "Here is the fix:" preamble - the block is self-explanatory. Any accompanying explanation goes AFTER as "Notes on the suggestion above: ..." if needed.
- **Inline-comment recommendations MUST be suggestion blocks**: if the recommendation is "add an inline comment / TODO / marker / Javadoc line", render it as a ```suggestion``` block containing the exact edited code - never as prose that describes the comment. The reader should be one click away from applying the change. This includes:
  - Adding a leading comment line above an existing statement (include the existing statement in the suggestion so GitHub applies the change).
  - Adding a trailing `// ...` comment on an argument or field (include the whole line the argument sits on).
  - Inserting a placeholder test method (`@Disabled` skeleton) between existing test methods (include the closing `}` of the preceding test in the suggestion so the insertion point is anchored).
  - Extending a class-level Javadoc block (include the full replacement Javadoc, or - if the anchor lands mid-Javadoc - the enclosing paragraph).
- **When a comment recommends "annotate with a TODO/FIXME/marker", it MUST be a suggestion**: prose like "add a TODO(FOO) here noting X" is not enough - the reader has to translate that into an edit themselves, which is friction. Always ship the ready-to-apply diff.

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

Use box-drawing characters for sequence/architecture diagrams. Diagrams appear only inside the `<details>` block - never above the fold.
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
- [ ] For Format B primaries: above the fold contains only the title, the what's-wrong intro (2-4 sentences), and **Fix** with both "In this PR (#TICKET)" and "Follow-up ticket" bullets
- [ ] For Format B primaries: any code suggestion lives inside the "In this PR" bullet of **Fix** (never inside `<details>`), with no "Suggested code:" preamble
- [ ] For Format B primaries: `<details>` block present with summary line `Problem detail and follow-up scope`, a blank line after `</summary>` and before `</details>`, and no content duplicated from above the fold
- [ ] For Format B: every companion is a stub - the primary's `**[SEVERITY-N] ...**` title verbatim (no sub-title, no rewording; the companion's angle goes in the 1-2 sentence intro), an optional suggestion block, and a `See primary comment:` link using the primary's real `html_url`. No Fix section, no `<details>`. Only `[TEST GAP]` companions may use a different marker.
- [ ] Any recommendation to "add an inline comment / TODO / marker / Javadoc line / placeholder test" is expressed as a ```suggestion``` block containing the exact edited code, NOT as prose describing the comment.
- [ ] Read the above-the-fold text out loud. If any clause makes you stumble, or if any word could be cut without loss of meaning, rewrite before posting. It must not carry filler ("In plain terms:", redundant adjectives, negative framing when positive would read faster, or qualifiers that just restate the setup).
