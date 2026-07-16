---
name: pr-review-comments
description: Transform security review findings into targeted GitHub PR review comments. Takes a single finding from a differential review report and produces actionable, file-targeted PR review comments using the GitHub API (gh). Use when the user says "/pr-review-comments", "post review comments", "turn findings into PR comments", "post this finding", or asks to convert a security/code review finding into inline PR comments. Three formats - Format A (single code suggestion + concise explanation, LOW), Format B (four-section skeleton with explicit "in this PR" vs "follow-up ticket" split-scope for MEDIUM/HIGH multi-file findings, with ASCII diagrams and multi-file companion comments), and Format C (test coverage gaps).
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

**Every Format B comment (primary and companions) uses the same four-section skeleton in this exact order:**

```
**[SEVERITY-N] Title that captures the defect**

<Section 1: short human-readable description of the issue - 2-5 sentences,
plain English, "in plain terms" framing. What breaks, when it breaks, why it
matters. No diagrams here.>

---

**Recommendation summary**

- **In this PR (#TICKET):** <one-line summary of the in-PR change>. <If the
  fix is small enough to inline as a suggestion, put the ```suggestion``` block
  INSIDE this bullet.> <If no code change is needed on this file, say so
  explicitly and point at the file/line where the in-PR fix lands.>
- **Follow-up ticket (new, or scope-expansion of #TICKET):** <one-line summary
  of what must be split out and why it does not fit this PR>.

---

**Problem detail**

<Section 3: precise technical description of the defect. Enumerate the gaps
that chain together, cite exact file:line references, show ASCII diagrams for
data/control flow, describe the failure scenario end-to-end, and bound
exploitability.>

---

**Recommendation detail**

<Section 4: expanded version of Section 2.

**In this PR (#TICKET)** - list the specific code changes with file paths and
what they do. Cross-reference companion comments for the exact suggestions.

**Follow-up ticket (new, or scope-expansion of #TICKET)** - numbered list of
concrete tasks the ticket must cover before the change described is
production-safe. Include tests. Include any preconditions on other tickets.>
```

**Where the ```suggestion``` block lives.**
- If the in-PR fix is a small, self-contained code change on the file this
  comment anchors: put the ```suggestion``` block INSIDE the "In this PR"
  bullet of the Recommendation summary, so the code and its rationale sit
  together at the top of the comment.
- Even "add an inline comment / TODO / marker" recommendations go in a
  ```suggestion``` block, containing the exact edited line(s) - never as
  prose. The reader should be one click away from applying the change.
- If the fix is too large for a suggestion block, or spans multiple
  non-contiguous edits: describe it in Section 4 (Recommendation detail) with
  a fenced code block or an ASCII data-flow diagram.
- If this file needs no code change (e.g., a companion anchoring the
  follow-up ticket's landing zone): say so explicitly in Section 2 - "no code
  change at this line" - and point at the file/line where the in-PR fix
  actually lands.
- If the in-PR fix is a suggestion inside Section 2, Section 4's "In this PR"
  entry can be a single line ("see suggestion above") plus any notes on
  narrower alternatives, follow-up cleanup, or removal timing.

**Companion comment linking.** Post companion comments on each additional
file. Each companion:
- Uses the same four-section skeleton.
- Uses the **EXACT SAME** `**[SEVERITY-N] Title of the defect**` as the
  primary - verbatim, no sub-title variation, no rewording. Reader scanning
  the PR must instantly recognize the comments as one finding. The
  companion's specific angle (driver-side / test-side / follow-up anchor / etc.)
  is expressed in the Section 1 plain-English intro, NOT in the title.
- Ends with: `See primary comment: https://github.com/{owner}/{repo}/pull/{pr}#discussion_r{id}`
  (real URL from the primary's `html_url`).

The only exception is `[TEST GAP]` companions, which by convention use their
own `**[TEST GAP] ...**` marker (a different severity category). They still
end with a `See primary comment:` link.

The primary is the comment on the file/line where the defect is most
concentrated; companions cover other affected files and can also be used to
"anchor" the follow-up ticket at the driver-side / consumer-side landing zone
even when no in-PR code change happens there.

**Worked example - companion comment where the in-PR fix IS a suggestion.** The
title below is the primary's title, reused verbatim. The companion's specific
angle ("startup must fail-fast until override substrate lands") is expressed
in the Section 1 intro, not in the title.

````
**[MEDIUM-1] Follower loop bypasses the required proxy and system-address execution contexts**

<Section 1 - plain English: 2-5 sentences framing THIS FILE'S angle on the
finding. E.g. "This is the in-PR landing zone: the startup branch must
fail-fast until the override substrate lands, otherwise operators enabling
the flag get a driver that reverts at the first nested-callback inbound.">


---

**Recommendation summary**

- **In this PR:** replace the planner-construction branch with an `IllegalStateException` so `--plugin-xcall-eez-fixpoint-loop-enabled=true` no longer starts:

```suggestion
      cliOptions.validateEezFixpointLoopOptions();
      throw new IllegalStateException(
          "EEZ fixpoint loop cannot be enabled: ...");
```

- **Follow-up ticket:** described in the primary comment - widen the planner seam, thread `StateOverrideMap`, and delegate to `EezSimulator`. Remove this guard when that lands.

---

**Problem detail**

<Section 3 - precise technical description, file:line citations, ASCII diagram, failure scenario, exploitability bound.>

---

**Recommendation detail**

Notes on the suggestion above:
- Remove this guard as part of the follow-up ticket, at the same commit that lands the state-override wiring.
- <Any narrower alternatives, testing notes, etc.>

See primary comment: https://github.com/{owner}/{repo}/pull/{pr}#discussion_r{id}
````

**Worked example - companion comment where NO in-PR code change is needed on
this file (follow-up anchor only).** The title matches the primary verbatim
again. The companion's specific angle ("this is the driver-side half of the
gap - `Optional.empty()` here defeats even a corrected planner") lives in
Section 1.

````
**[MEDIUM-1] Follower loop bypasses the required proxy and system-address execution contexts**

<Section 1 - plain English framing THIS SITE's role in the finding.
E.g. "This is the driver-side half of the gap. Even if the planner returned a
CallParameter with SYSTEM_ADDRESS as sender, `Optional.empty()` here defeats
strict balance validation because no overrides map funds the sender. Anchoring
here so the follow-up ticket has a clear driver-side landing point.">


---

**Recommendation summary**

- **In this PR:** no code change at this line - the in-PR fix is the startup guard in `XCallPlugin.java` (see companion). This L579 site is annotated only.
- **Follow-up ticket:** thread a `StateOverrideMap` through both this call and the L534 first-pass call, sourced from the planner's return value (planner seam must widen).

---

**Problem detail**

<Section 3 - why Optional.empty() defeats even a corrected planner, cross-reference to the mirror site.>

---

**Recommendation detail**

Follow-up work required at this seam:

<fenced code block or ASCII diagram of the data-flow that must be threaded through>

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
   - Format B (multi-file / split-scope): defect spans multiple files OR the recommendation naturally splits into "in this PR" (small, contained) plus "follow-up ticket" (architectural). Use Format B whenever you'd otherwise need to explain "this fix is only partial" - the 4-section skeleton makes the split explicit.
   - Format C: test coverage gap.
3. **Locate the exact file + line** in the PR diff where the comment anchors
   - Use `gh api repos/{owner}/{repo}/pulls/{pr}/files` to get the diff
   - Use `gh api repos/{owner}/{repo}/contents/{path}?ref={sha}` if needed
4. **Decide the split** (Format B only): before drafting, name the in-PR change (concrete, small, landable now) and the follow-up ticket scope (architectural, out-of-scope for this PR). If you cannot cleanly name both, either widen Section 4's "In this PR" bullet or step down to Format A.
5. **STOP - Show the user the draft** comment(s) and target file/line for approval before posting. Display:
   - Target: `{path}:{line}`
   - Format: A, B, or C
   - Full comment body (rendered, including all four sections for Format B)
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
- **Every word earns its place in Section 1 and Section 2 (Format B).** Section 1 (plain-English intro) and Section 2 (Recommendation summary) are the ONLY parts a 0-context reader is guaranteed to read - the title tells them a defect exists, then they scan these two sections to decide whether to act. Section 3 (Problem detail) is where technical depth belongs. Apply this discipline hard:
  - **No "In plain terms:", "Basically,", "Essentially," preambles.** The section is plain English by convention. Just state the defect.
  - **No adjectives that repeat the setup.** "Silent narrowing" when the whole point is that it's silent → drop "silent". "Weak size-only assertions" when the whole comment argues weakness → drop "Weak".
  - **Positive framing over negative.** "so X can find them" beats "otherwise X cannot find them". "no `SimulateResponse` sent" beats "without sending any `SimulateResponse`".
  - **Merge adjacent clauses when they share a subject.** "It ONLY asks for direct children and it emits ..." → "It only asks for its direct children and emits ...".
  - **Parallel structure** for three-item lists. "no source-proxy derivation, no dispatcher-code install, no static-call enforcement" reads faster than "it skips X, Y, and Z".
  - **Numeric ranges: use power notation.** `[2^31, 2^32-1]` beats `[2,147,483,648, 4,294,967,295]` - readers scan the exponent instantly.
  - **Drop qualifiers that are obvious from the frame.** "one small change" as a hint that the in-PR fix is small is unnecessary if the suggestion block is already visible. "the review's clause" > "This is the ... clause of the review".
  - **Cut over "however", "as-is", "specifically", "actually".** These usually add length without content. If the contrast is real, the reader picks it up from the substance.
  - **Read Section 1 out loud once.** If you stumble on a clause, rewrite it. If you re-read a sentence to parse it, split it.
- **No filler**: cut "it would be preferable to" - just state the fix
- **Bound risk**: always state why severity is what it is (not higher)
- **Diagrams over prose**: for anything involving data flow, control flow, or timing - draw it
- **Suggestion blocks must compile**: test mentally that the suggestion is syntactically valid
- **One finding = one comment thread**: don't combine findings
- **Split scope explicitly**: for any non-trivial finding, name what lands in THIS PR vs what splits to a follow-up ticket. Reviewers should never have to guess whether a recommendation is blocking merge.
- **Section order is fixed for Format B**: title+human summary → recommendation summary → problem detail → recommendation detail. Do not reorder. Section 1 is plain English; save citations, diagrams, and failure scenarios for Section 3.
- **Suggestion block placement (Format B)**: if the in-PR fix is a small self-contained code change on the file this comment anchors, put the ```suggestion``` block INSIDE the "In this PR" bullet of Section 2, not in Section 4. Section 4 then just references it.
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
- [ ] For Format B: all four sections present in the fixed order (title+summary → recommendation summary → problem detail → recommendation detail), separated by `---` rules
- [ ] For Format B: Recommendation summary explicitly names both "In this PR (#TICKET)" and "Follow-up ticket" bullets
- [ ] For Format B: if there is a code suggestion, it lives inside the "In this PR" bullet of Section 2 (not in Section 4), and has no "Suggested code:" preamble
- [ ] For Format B: all companion comments use the same 4-section skeleton and link back to primary's real `html_url`
- [ ] For Format B: EVERY companion's `**[SEVERITY-N] ...**` title is IDENTICAL to the primary's title (verbatim - no sub-title, no rewording, no companion-specific angle in the title). The companion's angle goes in the Section 1 plain-English intro instead. Only `[TEST GAP]` companions may use a different marker.
- [ ] Any recommendation to "add an inline comment / TODO / marker / Javadoc line / placeholder test" is expressed as a ```suggestion``` block containing the exact edited code, NOT as prose describing the comment.
- [ ] Read Section 1 and Section 2 out loud. If any clause makes you stumble, or if any word could be cut without loss of meaning, rewrite before posting. These sections are what a 0-context reader uses to decide whether to act - they must not carry filler ("In plain terms:", redundant adjectives, negative framing when positive would read faster, or qualifiers that just restate the setup).
