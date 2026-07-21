---
name: pr-review-comments
description: Transform security review findings into targeted GitHub PR review comments. Takes a single finding from a differential review report and produces actionable, file-targeted PR review comments using the GitHub API (gh). Use when the user says "/pr-review-comments", "post review comments", "turn findings into PR comments", "post this finding", or asks to convert a security/code review finding into inline PR comments. Three formats - Format A (single code suggestion + concise explanation), Format B (concise multi-file or structural thread with B-current default and evidence-backed B-split scope), and Format C (standalone test coverage gaps).
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

### Format B: Multi-file or structural finding

Use Format B when the finding spans multiple files, needs non-contiguous edits, or requires structural explanation. Format B describes comment shape; it does not decide whether work leaves the current PR.

**Choose one delivery mode before drafting:**

- **B-current (default):** the complete production fix and regression coverage land in this PR. Multi-file scope, structural work, lack of a suggestion block, additional tests, and LOW severity do not justify a follow-up ticket by themselves.
- **B-split (exception):** part of the fix cannot reasonably land in this PR because the user, maintainer, or governing ticket excludes it; an unmet prerequisite blocks it; it belongs to another repository, owner, release, or deployment boundary; or required test infrastructure cannot be added within the current ticket. Cite the qualifying evidence in the draft. "Too large," "architectural," and "better as follow-up" do not qualify without a concrete blocker.

If no qualifying evidence exists, use B-current.

**B-current primary - three parts, fixed order:**

````
**[SEVERITY-N] Title that captures the defect**

<What's wrong: 2-4 sentences, plain English. What breaks, when it breaks, why
it matters. No citations, no diagrams.>

**Recommended fix**

- **In this PR (#TICKET, omit if none):** <the complete production fix and regression coverage; include a ```suggestion``` block here when the fix is a small self-contained change on this file; otherwise point to the file or companion where the change lands>

---

<details>
<summary><b>Problem detail and implementation scope</b></summary>

<Citations, failure scenario, exploitability bound, the full fix description
when it does not fit above the fold, and a numbered In-PR task list. Nothing
here restates the Recommended fix bullet or the what's-wrong intro.>

</details>
````

**B-split primary - three parts, fixed order:**

````
**[SEVERITY-N] Title that captures the defect**

<What's wrong: 2-4 sentences, plain English. What breaks, when it breaks, why
it matters. No citations, no diagrams.>

**Recommended fix**

- **In this PR (#TICKET, omit if none):** <a safe and independently complete in-PR change; include a ```suggestion``` block here when the change is small and self-contained on this file; otherwise point to the file or companion where the change lands>
- **Follow-up ticket (#ISSUE):** <deferred work and the concrete blocker that prevents it from landing in this PR>

---

<details>
<summary><b>Problem detail and implementation scope</b></summary>

<Citations, failure scenario, exploitability bound, cited split evidence,
and separate numbered task lists for the current PR and follow-up ticket.
Nothing here restates the Recommended fix bullets or the what's-wrong intro.>

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
- Summary line is always `<b>Problem detail and implementation scope</b>` - bold via `<b>` tags, since markdown `**` does not render inside `<summary>`.
- A `---` rule sits above the `<details>` block, separating it from the Recommended fix section.
- Leave a blank line after `<summary>...</summary>` and before `</details>` so GitHub renders the markdown inside.
- Diagrams live only inside `<details>`.

**Regression coverage.** Tests that prove a production finding stays fixed are part of the current PR by default. Defer them only in B-split when the required harness or prerequisite does not exist and cannot be added within the current ticket; cite that blocker. Use Format C when the finding itself is solely a test gap.

**Follow-up ticket linking (B-split only).** Link the specific GitHub issue that tracks the evidence-backed deferred work. `#N` auto-links within the same repo; use the full issue URL for a cross-repo ticket. If no issue exists, first obtain approval for the review-comment draft, then show the proposed issue title and body and request separate approval to create it. Approval of the review-comment draft does not authorize issue creation. Do not post a placeholder or unlinked split comment if creation is declined or fails; revise to B-current or use an existing issue supplied by the user.

**Companion comments.** Post a stub on each additional file:

````
**[SEVERITY-N] Exact same title as the primary - verbatim**

<1-2 sentences: this file's specific angle on the finding.>

<```suggestion``` block, only if this file carries an in-PR fix>

See primary comment: https://github.com/{owner}/{repo}/pull/{pr}#discussion_r{id}
````

- No Recommended fix section, no `<details>`, no problem detail. Site-specific reasoning
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

**Recommended fix**

- **In this PR (#4333):** fail startup when `--plugin-xcall-eez-fixpoint-loop-enabled=true` until the follower-pass override substrate is threaded through the loop seam. See `XCallPlugin.java:254` companion for the exact suggestion.
- **Follow-up ticket (#4350):** wire both follower passes through the execution contexts `EezSimulator` already implements - too large for this PR; task breakdown in the details block.

---

<details>
<summary><b>Problem detail and implementation scope</b></summary>

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

1. Identify the finding from the review report.
2. Classify the comment shape: A is one self-contained target with valid suggestion; B is multi-file, non-contiguous, or structural; C is standalone test gap.
3. Select Format B delivery mode: default B-current with complete production fix and regression coverage; B-split only with concrete evidence from user direction, ticket scope, dependency state, ownership, release boundaries, or unavailable test infrastructure; cite evidence and state complexity/file count/severity/test effort are not evidence.
4. Locate exact PR diff file/line using the existing gh API commands.
   - Use `gh api repos/{owner}/{repo}/pulls/{pr}/files` to get the diff.
   - Use `gh api repos/{owner}/{repo}/contents/{path}?ref={sha}` if needed.
5. STOP and show draft before any GitHub mutation: target, format A/B-current/B-split/C, full rendered body including details, every companion, and for B-split the exact evidence plus existing issue or clearly pending issue. Wait for explicit comment approval.
6. STOP again before issue creation for approved B-split without existing issue: search open and closed issues to avoid duplicates; show proposed title/body; request separate issue approval; if declined do not create or post and revise/use existing issue; if creation fails report GitHub error and stop.
7. Post through the existing gh API command only after required approvals.
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pr}/comments \
     -f body="<comment>" \
     -f path="<file>" \
     -F line=<line> \
     -f side="RIGHT" \
     -f commit_id="<sha>"
   ```
8. Post Format B companions after primary using its real html_url.

## Writing Rules

- **Concise**: reader decides in <30 seconds whether to act
- **Every word earns its place above the fold (Format B).** Everything outside `<details>` - title, what's-wrong intro, and **Recommended fix** - is what a 0-context reader uses to decide whether to act. Depth belongs inside `<details>`. Apply this discipline hard:
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
- **Current-PR scope is the default**: for B-current, name the complete production fix and regression coverage under **In this PR**. Do not add follow-up language merely because the work is multi-file, structural, lacks a suggestion block, adds tests, or is LOW severity.
- **Split scope requires evidence**: for B-split, state the concrete blocker and keep the in-PR change safe and independently complete. Never infer a split from size or complexity alone.
- **Structure is fixed for Format B**: title + what's-wrong intro -> **Recommended fix** -> `---` + `<details>`. B-current has one **In this PR** bullet; B-split adds one **Follow-up ticket** bullet. Save citations, diagrams, failure scenarios, and task breakdowns for the `<details>` block.
- **No duplication across the fold (Format B)**: each point appears exactly once above or below the fold. The `<details>` block adds evidence and implementation task breakdown; it never restates the Recommended fix bullets.
- **Suggestion block placement (Format B)**: if the in-PR fix is a small self-contained code change on the file this comment anchors, put the ```suggestion``` block inside the "In this PR" bullet of **Recommended fix**. Never inside `<details>`.
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
- [ ] Every Format B draft identifies B-current or B-split before posting.
- [ ] B-current contains one **In this PR** bullet covering the complete production fix and regression coverage, with no follow-up placeholder, ticket search, or issue creation.
- [ ] B-split cites qualifying evidence, keeps the in-PR change safe and independently complete, and includes both **In this PR** and **Follow-up ticket** bullets.
- [ ] A posted B-split comment links a real GitHub issue; creating a new issue had separate explicit approval after review-comment approval.
- [ ] Any Format B code suggestion lives inside the **In this PR** bullet of **Recommended fix**, never inside `<details>`, with no suggestion preamble.
- [ ] Every Format B `<details>` block has a `---` rule above it, summary line `<b>Problem detail and implementation scope</b>`, blank lines after `</summary>` and before `</details>`, and no content duplicated from above the fold.
- [ ] Every Format B companion is a stub with the primary title verbatim, a 1-2 sentence file-specific angle, an optional suggestion, and a `See primary comment:` link using the primary's real `html_url`. It has no Recommended fix section or `<details>` block. Only `[TEST GAP]` companions may use a different marker.
- [ ] Any recommendation to "add an inline comment / TODO / marker / Javadoc line / placeholder test" is expressed as a ```suggestion``` block containing the exact edited code, NOT as prose describing the comment.
- [ ] Read the above-the-fold text out loud. If any clause makes you stumble, or if any word could be cut without loss of meaning, rewrite before posting. It must not carry filler ("In plain terms:", redundant adjectives, negative framing when positive would read faster, or qualifiers that just restate the setup).
