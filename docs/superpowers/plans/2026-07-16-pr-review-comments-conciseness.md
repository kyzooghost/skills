# pr-review-comments Format B Conciseness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure Format B in `skills/pr-review-comments/SKILL.md` so primary comments read at roughly half their current length (what's-wrong + Fix above the fold, evidence behind `<details>`) and companions become stubs.

**Architecture:** All changes land in one prose file. The four-section Format B skeleton is replaced by a three-part shape; companion rules, worked examples, writing rules, procedure, diagram-style note, and checklist are updated to match. Spec: `docs/superpowers/specs/2026-07-16-pr-review-comments-conciseness-design.md`.

**Tech Stack:** Markdown only. Verification is by reading and grep. One commit at the end (intermediate commits would leave stale cross-references within the single file).

**Note on fences:** `SKILL.md` wraps comment examples in 4-backtick fences because they contain 3-backtick ```suggestion``` blocks. This plan wraps those in 5-backtick fences. When copying replacement text into `SKILL.md`, keep the inner fences exactly as shown.

---

### Task 1: Replace the Format B section

**Files:**
- Modify: `skills/pr-review-comments/SKILL.md` - the entire `### Format B: Multi-file architectural issue (MEDIUM/HIGH findings)` section, from that heading up to (not including) the `### Format C: Test coverage gap (`[TEST GAP]`)` heading.

- [ ] **Step 1: Replace the section**

Delete everything between the two headings and insert:

`````markdown
### Format B: Multi-file architectural issue (MEDIUM/HIGH findings)

For findings requiring structural changes across multiple files, or where the recommendation splits between "fix in this PR" and "track in a follow-up ticket."

**Primary comment - three parts, fixed order:**

````
**[SEVERITY-N] Title that captures the defect**

<What's wrong: 2-4 sentences, plain English. What breaks, when it breaks, why
it matters. No citations, no diagrams.>

**Fix**

- **In this PR (#TICKET):** <one-line summary of the in-PR change, then the
  ```suggestion``` block if the fix is a small self-contained change on this
  file. If no code change is needed on this file, say so and point at the
  file/line where the in-PR fix lands.>
- **Follow-up ticket (new, or scope-expansion of #TICKET):** <one line: what
  splits out and why it does not fit this PR>

<details>
<summary>Problem detail and follow-up scope</summary>

<Citations (file:line), ASCII diagram, end-to-end failure scenario,
exploitability bound, and the numbered follow-up task list the ticket must
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
- **Follow-up ticket (new, or scope-expansion of #4342):** widen the `FollowerReSimulationPlanner` seam to return `StateOverrideMap` alongside `CallParameter`, thread overrides through both `LoopSimulator.simulateCall` sites, and delegate to `EezSimulator` (which already implements the correct contexts).

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
`````

- [ ] **Step 2: Verify**

Read the replaced section top to bottom. Confirm: no `---` separators inside the primary skeleton, no "Recommendation summary" / "Problem detail" / "Recommendation detail" headings anywhere in the section, and both worked examples parse (4-backtick outer fences, 3-backtick inner fences balanced).

### Task 2: Update the frontmatter description

**Files:**
- Modify: `skills/pr-review-comments/SKILL.md` - the `description:` line in the YAML frontmatter.

- [ ] **Step 1: Rewrite the Format B clause**

In the `description:` value, replace:

```
Format B (four-section skeleton with explicit "in this PR" vs "follow-up ticket" split-scope for MEDIUM/HIGH multi-file findings, with ASCII diagrams and multi-file companion comments)
```

with:

```
Format B (concise what's-wrong + Fix with a collapsed detail block and stub companions, explicit "in this PR" vs "follow-up ticket" split for MEDIUM/HIGH multi-file findings)
```

Leave the Format A and Format C clauses untouched.

### Task 3: Update the Writing Rules section

**Files:**
- Modify: `skills/pr-review-comments/SKILL.md` - the `## Writing Rules` bullet list.

- [ ] **Step 1: Rewrite the "every word earns its place" bullet**

Replace the bullet beginning `**Every word earns its place in Section 1 and Section 2 (Format B).**` (its lead-in sentences only - keep all existing sub-bullets: no preambles, no repeated adjectives, positive framing, merge adjacent clauses, parallel structure, power notation, drop obvious qualifiers, cut "however"/"as-is"/"specifically"/"actually") with this lead-in:

```markdown
- **Every word earns its place above the fold (Format B).** Everything outside `<details>` - title, what's-wrong intro, and **Fix** - is what a 0-context reader uses to decide whether to act. Depth belongs inside `<details>`. Apply this discipline hard:
```

In the final sub-bullet, replace `**Read Section 1 out loud once.**` with `**Read the above-the-fold text out loud once.**` (rest of the sub-bullet unchanged).

- [ ] **Step 2: Rewrite the section-order bullet**

Replace the bullet beginning `**Section order is fixed for Format B**` with:

```markdown
- **Structure is fixed for Format B**: title + what's-wrong intro → **Fix** → `<details>`. Do not reorder. The intro is plain English; save citations, diagrams, and failure scenarios for the `<details>` block.
```

- [ ] **Step 3: Rewrite the suggestion-block-placement bullet**

Replace the bullet beginning `**Suggestion block placement (Format B)**` with:

```markdown
- **Suggestion block placement (Format B)**: if the in-PR fix is a small self-contained code change on the file this comment anchors, put the ```suggestion``` block inside the "In this PR" bullet of **Fix**. Never inside `<details>`.
```

- [ ] **Step 4: Add the no-duplication bullet**

Immediately after the rewritten structure bullet from Step 2, insert:

```markdown
- **No duplication across the fold (Format B)**: each point appears exactly once - above the fold or inside `<details>`, never both. The `<details>` block adds evidence and the follow-up task breakdown; it never restates the Fix bullets.
```

### Task 4: Update Procedure and Diagram Style

**Files:**
- Modify: `skills/pr-review-comments/SKILL.md` - `## Procedure` steps 4-5 and `## Diagram Style (Format B)`.

- [ ] **Step 1: Fix the stale reference in Procedure step 4**

In step 4 ("Decide the split"), replace `either widen Section 4's "In this PR" bullet or step down to Format A` with `either widen the "In this PR" bullet of Fix or step down to Format A`.

- [ ] **Step 2: Update Procedure step 5**

Replace `Full comment body (rendered, including all four sections for Format B)` with:

```markdown
   - Full comment body (rendered, including the `<details>` block content for Format B)
```

- [ ] **Step 3: Add placement note to Diagram Style**

After the `## Diagram Style (Format B)` heading's first sentence ("Use box-drawing characters..."), add:

```markdown
Diagrams appear only inside the `<details>` block - never above the fold.
```

### Task 5: Update the Checklist Before Posting

**Files:**
- Modify: `skills/pr-review-comments/SKILL.md` - `## Checklist Before Posting`.

- [ ] **Step 1: Replace the Format B checklist items**

Keep these items unchanged: suggestion block syntactically valid; line number in PR diff; commit SHA matches head; title captures the defect; risk bounded; the "inline comment / TODO / marker as suggestion block" item.

Replace the four `For Format B:` items and the final read-aloud item with:

```markdown
- [ ] For Format B: above the fold contains only the title, the what's-wrong intro (2-4 sentences), and **Fix** with both "In this PR (#TICKET)" and "Follow-up ticket" bullets
- [ ] For Format B: any code suggestion lives inside the "In this PR" bullet of **Fix** (never inside `<details>`), with no "Suggested code:" preamble
- [ ] For Format B: `<details>` block present with summary line `Problem detail and follow-up scope`, a blank line after `</summary>` and before `</details>`, and no content duplicated from above the fold
- [ ] For Format B: every companion is a stub - the primary's `**[SEVERITY-N] ...**` title verbatim (no sub-title, no rewording; the companion's angle goes in the 1-2 sentence intro), an optional suggestion block, and a `See primary comment:` link using the primary's real `html_url`. No Fix section, no `<details>`. Only `[TEST GAP]` companions may use a different marker.
- [ ] Read the above-the-fold text out loud. If any clause makes you stumble, or if any word could be cut without loss of meaning, rewrite before posting. It must not carry filler ("In plain terms:", redundant adjectives, negative framing when positive would read faster, or qualifiers that just restate the setup).
```

### Task 6: Consistency check and commit

**Files:**
- Modify: `skills/pr-review-comments/SKILL.md` (fixes only, if the check finds stragglers)

- [ ] **Step 1: Grep for stale skeleton references**

Run: `rg -n 'Section [1-4]|four-section|Recommendation summary|Recommendation detail|Problem detail' skills/pr-review-comments/SKILL.md`

Expected: matches only for the `<details>` summary line text `Problem detail and follow-up scope` (skeleton, conventions, worked example, checklist). Any other match is a stale reference - rewrite it per the new shape.

- [ ] **Step 2: Read the full file**

Read `skills/pr-review-comments/SKILL.md` end to end. Confirm Format A and Format C sections are byte-identical to before (`git diff` should show no hunks in those sections) and the Procedure's STOP gate (step 5) is intact.

- [ ] **Step 3: Commit**

```bash
git add skills/pr-review-comments/SKILL.md
git commit -m "refactor(pr-review-comments): halve Format B verbosity with fold structure and stub companions"
```
