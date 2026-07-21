# pr-review-comments Scope Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Format B keep complete fixes and regression coverage in the current PR by default, while allowing evidence-backed scope splits with separate approval before issue creation.

**Architecture:** Separate comment-shape classification from delivery-scope routing inside `skills/pr-review-comments/SKILL.md`. Format B gains `B-current` and `B-split` modes, then the procedure, writing rules, checklist, and worked examples are aligned with those modes so no unconditional follow-up-ticket rule remains.

**Tech Stack:** Markdown, GitHub CLI documentation, `rg`, Git

**Design:** `docs/superpowers/specs/2026-07-21-pr-review-comments-scope-routing-design.md`

Angle-bracketed metavariables inside replacement snippets are literal content for the skill's output templates, not unfinished plan steps.

---

### Task 1: Implement the Format B scope-routing contract

**Files:**
- Modify: `skills/pr-review-comments/SKILL.md:1-339`
- Reference: `docs/superpowers/specs/2026-07-21-pr-review-comments-scope-routing-design.md`

- [ ] **Step 1: Capture the current contradictory rules**

Run:

```bash
rg -n 'Format B \(multi-file / split-scope\)|with both "In this PR|Follow-up ticket linking|Problem detail and follow-up scope|create it after the user approves the draft' skills/pr-review-comments/SKILL.md
```

Expected: matches show that multi-file findings select Format B, every Format B primary requires both bullets, the details label assumes follow-up scope, and issue creation follows review-comment approval without a separate approval gate.

- [ ] **Step 2: Update the frontmatter description**

Replace the current `description:` line with:

```yaml
description: Transform security review findings into targeted GitHub PR review comments. Takes a single finding from a differential review report and produces actionable, file-targeted PR review comments using the GitHub API (gh). Use when the user says "/pr-review-comments", "post review comments", "turn findings into PR comments", "post this finding", or asks to convert a security/code review finding into inline PR comments. Three formats - Format A (single code suggestion + concise explanation), Format B (concise multi-file or structural thread with B-current default and evidence-backed B-split scope), and Format C (standalone test coverage gaps).
```

- [ ] **Step 3: Replace the Format B introduction and primary templates**

Replace the content from `### Format B:` through the closing fence immediately before `**Where the suggestion block lives.**` with the following literal Markdown. Keep the nested fence lengths exactly as shown.

`````markdown
### Format B: Multi-file or structural finding

Use Format B when the finding spans multiple files, needs non-contiguous edits, requires structural explanation, or has any evidence-backed split recommendation. The multi-file and structural paths describe comment shape; an evidence-backed split also requires Format B's two-scope structure even when its current-PR mitigation has one target.

**Choose one delivery mode before drafting:**

- **B-current (default):** the complete production fix and regression coverage land in this PR. Multi-file scope, structural work, lack of a suggestion block, additional tests, and LOW severity do not justify a follow-up ticket by themselves.
- **B-split (exception):** part of the fix cannot reasonably land in this PR because the user, maintainer, or governing ticket excludes it; an unmet prerequisite blocks it; it belongs to another repository, owner, release, or deployment boundary; or required test infrastructure does not exist and cannot be added within the current ticket. Cite the qualifying evidence in the draft. "Too large," "architectural," and "better as follow-up" do not qualify without a concrete blocker.

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
`````

- [ ] **Step 4: Make the details and issue rules conditional**

Replace the existing `<details>` conventions and follow-up-ticket-linking paragraphs with:

```markdown
**`<details>` conventions.**
- Summary line is always `<b>Problem detail and implementation scope</b>` - bold via `<b>` tags, since markdown `**` does not render inside `<summary>`.
- A `---` rule sits above the `<details>` block, separating it from the Recommended fix section.
- Leave a blank line after `<summary>...</summary>` and before `</details>` so GitHub renders the markdown inside.
- Diagrams live only inside `<details>`.

**Regression coverage.** Tests that prove a production finding stays fixed are part of the current PR by default. Defer them only in B-split when the required harness or prerequisite does not exist and cannot be added within the current ticket; cite that blocker. Use Format C when the finding itself is solely a test gap.

**Follow-up ticket linking (B-split only).** Link the specific GitHub issue that tracks the evidence-backed deferred work. `#N` auto-links within the same repo; use the full issue URL for a cross-repo ticket. If no issue exists, first obtain approval for the review-comment draft, then show the proposed issue title and body and request separate approval to create it. Approval of the review-comment draft does not authorize issue creation. If creation is approved, create the issue, capture its real number and URL, replace the pending marker in the approved B-split body, and then post. If creation is declined, do not create the issue or post the split comment; revise to B-current or use an existing issue supplied by the user, then return to the review-comment draft gate for fresh approval of the complete rendered body. If creation fails, report the error and stop without posting a comment that references the missing issue.
```

- [ ] **Step 5: Replace the Procedure section**

Replace the complete numbered list under `## Procedure` with:

```markdown
1. **Identify the finding** from the review report.
2. **Classify the comment shape**:
   - Format A: one self-contained, complete recommendation at one target with a valid suggestion block and no deferred scope.
   - Format B: a multi-file, non-contiguous, or structurally complex finding, or any evidence-backed split recommendation.
   - Format C: a standalone test-gap finding.
3. **Select the Format B delivery mode**:
   - Default to B-current with the complete production fix and regression coverage in this PR.
   - Use B-split only with concrete evidence from user direction, ticket scope, dependency state, ownership, or release boundaries, or when required test infrastructure does not exist and cannot be added within the current ticket.
   - Cite the qualifying evidence. Complexity, file count, severity, and test effort are not split evidence.
   - If a complete fix depends on unresolved product or architecture decisions, ask the user for direction rather than inventing a B-current recommendation or scope boundary.
4. **Locate the exact file and line** in the PR diff where each comment anchors:
   - Use `gh api repos/{owner}/{repo}/pulls/{pr}/files` to get the diff.
   - Use `gh api repos/{owner}/{repo}/contents/{path}?ref={sha}` if needed.
5. **STOP - Show the user the review-comment draft** before any GitHub mutation. Display:
   - Target: `{path}:{line}`.
   - Format A, B-current, B-split, or C.
   - Full rendered comment body, including the `<details>` content for Format B.
   - Every companion target for Format B.
   - For B-split, the exact qualifying evidence and the existing issue link or a clearly marked pending issue.
   - Wait for explicit approval of the review-comment draft.
6. **STOP again before creating an issue** when an approved B-split draft has no existing issue:
   - Search the repository's open and closed issues for an existing ticket that already owns the deferred work.
   - If the search finds an existing ticket, replace the pending marker with its real number or URL, then return to step 5 for fresh approval of the complete rendered body.
   - Otherwise, show the proposed issue title and complete body.
   - Request explicit issue-creation approval separate from review-comment approval.
   - If approved, create the GitHub issue, capture its real number and URL, replace the pending marker in the approved B-split body, and then proceed to posting.
   - If declined, do not create the issue or post the split comment; revise to B-current or use an existing issue supplied by the user, then return to step 5 for fresh approval of the complete rendered body.
   - If issue creation fails, report the GitHub error and stop before posting any comment that references the missing issue.
7. **Post via GitHub API** only after the required approvals and, for B-split, a real issue link:
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pr}/comments \
     -f body="<comment>" \
     -f path="<file>" \
     -F line=<line> \
     -f side="RIGHT" \
     -f commit_id="<sha>"
   ```
8. **Post Format B companions** after the primary, substituting the primary's real `html_url` into every `See primary comment:` footer.
```

- [ ] **Step 6: Replace the unconditional scope-writing rules**

In `## Writing Rules`, replace the bullets beginning `**Split scope explicitly**`, `**Structure is fixed for Format B**`, and `**No duplication across the fold` with:

```markdown
- **Current-PR scope is the default**: for B-current, name the complete production fix and regression coverage under **In this PR**. Do not add follow-up language merely because the work is multi-file, structural, lacks a suggestion block, adds tests, or is LOW severity.
- **Split scope requires evidence**: for B-split, state the concrete blocker and keep the in-PR change safe and independently complete. Never infer a split from size or complexity alone.
- **Structure is fixed for Format B**: title + what's-wrong intro -> **Recommended fix** -> `---` + `<details>`. B-current has one **In this PR** bullet; B-split adds one **Follow-up ticket** bullet. Save citations, diagrams, failure scenarios, and task breakdowns for the `<details>` block.
- **No duplication across the fold (Format B)**: each point appears exactly once above or below the fold. The `<details>` block adds evidence and implementation task breakdown; it never restates the Recommended fix bullets.
```

Leave the existing suggestion-block placement and all sentence-level conciseness rules unchanged.

- [ ] **Step 7: Replace the Format B checklist items**

Replace the checklist items from `For Format B primaries: above the fold` through the existing Format B companion item with:

```markdown
- [ ] Every Format B draft identifies B-current or B-split before posting.
- [ ] B-current contains one **In this PR** bullet covering the complete production fix and regression coverage, with no follow-up placeholder, ticket search, or issue creation.
- [ ] B-split cites qualifying evidence, keeps the in-PR change safe and independently complete, and includes both **In this PR** and **Follow-up ticket** bullets.
- [ ] A posted B-split comment links a real GitHub issue; after separately approved creation, its real number and URL replaced the pending marker before posting.
- [ ] Every materially revised comment body received fresh review-comment approval before posting.
- [ ] Any Format B code suggestion lives inside the **In this PR** bullet of **Recommended fix**, never inside `<details>`, with no suggestion preamble.
- [ ] Every Format B `<details>` block has a `---` rule above it, summary line `<b>Problem detail and implementation scope</b>`, blank lines after `</summary>` and before `</details>`, and no content duplicated from above the fold.
- [ ] Every Format B companion is a stub with the primary title verbatim, a 1-2 sentence file-specific angle, an optional suggestion, and a `See primary comment:` link using the primary's real `html_url`. It has no Recommended fix section or `<details>` block. Only `[TEST GAP]` companions may use a different marker.
```

- [ ] **Step 8: Verify the core contract**

Run:

```bash
rg -n 'B-current|B-split|Problem detail and implementation scope|separate explicit approval|separate approval' skills/pr-review-comments/SKILL.md
```

Expected: matches appear in the Format B definition, procedure, writing rules, and checklist.

Run:

```bash
rg -n 'with both "In this PR|Problem detail and follow-up scope|create it after the user approves the draft' skills/pr-review-comments/SKILL.md
```

Expected: no output.

- [ ] **Step 9: Commit the runtime-rule change**

```bash
git add skills/pr-review-comments/SKILL.md
git diff --cached --check
git commit -m "refactor(pr-review-comments): default fixes to current PR"
```

Expected: one commit modifying only `skills/pr-review-comments/SKILL.md`.

### Task 2: Add worked examples for both Format B modes

**Files:**
- Modify: `skills/pr-review-comments/SKILL.md` in the Format B worked-example section

- [ ] **Step 1: Add a B-current multi-file example**

Insert this example after the companion-comment rules and before the existing split-scope example:

`````markdown
**Worked example - B-current primary:**

````
**[LOW-1] Kotlin internal widens session state to public JVM API**

The migrated state holders and coordinator helpers are marked `internal`, but Kotlin emits them as public JVM classes, fields, and methods. Trusted Java code can mutate session phase or invoke timeout hooks outside the coordinator's intended boundary, causing abort or liveness failures. No remote path reaches these members, so severity is LOW.

**Recommended fix**

- **In this PR:** restore the baseline package-private JVM boundary for the session holder, abort helper, mutable fields, and coordinator hooks, then add compiled-bytecode visibility assertions for every affected member.

---

<details>
<summary><b>Problem detail and implementation scope</b></summary>

The Java baseline emits package-private classes, fields, and methods. Kotlin `internal` is module-level source visibility, so the migrated class files expose public JVM symbols.

```
trusted extension -> session(id).phase = COMMITTING
                  -> timeout and abort guards return
```

**In-PR task list:**
1. Restore package-private bytecode visibility for the state holder, abort helper, session accessor, timeout hook, and mutable state.
2. Assert the compiled modifiers for every migrated symbol.
3. Keep package-level coordinator tests proving intended internal access still works.

</details>
````

This remains B-current even though the production fix and regression coverage span multiple files. No external blocker exists, so the skill must not create a follow-up issue.
`````

- [ ] **Step 2: Mark the existing follower-loop example as B-split and add evidence**

Rename its heading to:

```markdown
**Worked example - B-split primary:**
```

Change its details summary to:

```html
<summary><b>Problem detail and implementation scope</b></summary>
```

Insert this paragraph immediately after that summary and its blank line:

```markdown
**Split evidence.** The user explicitly confirmed that the governing ticket limits the current PR to refusing unsafe feature activation. The execution-context wiring is owned by the linked follow-up ticket and depends on prerequisite state-override work, so it cannot land safely in this PR.
```

Keep the existing **In this PR** and **Follow-up ticket** bullets, failure diagram, task list, and companion example. Rename the companion heading to:

```markdown
**Worked example - B-split companion carrying the in-PR fix:**
```

- [ ] **Step 3: Verify both examples exercise different scope modes**

Run:

```bash
rg -n 'Worked example - B-current|Worked example - B-split|In-PR task list|Split evidence' skills/pr-review-comments/SKILL.md
```

Expected: the B-current example has an In-PR task list and no follow-up bullet; the B-split example has explicit split evidence and retains its linked follow-up bullet.

- [ ] **Step 4: Commit the examples**

```bash
git add skills/pr-review-comments/SKILL.md
git diff --cached --check
git commit -m "docs(pr-review-comments): demonstrate scope routing modes"
```

Expected: one commit adding the B-current example and qualifying the B-split example.

### Task 3: Run final scenario and consistency verification

**Files:**
- Verify: `skills/pr-review-comments/SKILL.md`
- Verify: `docs/superpowers/specs/2026-07-21-pr-review-comments-scope-routing-design.md`

- [ ] **Step 1: Verify no unconditional ticket rule remains**

Run:

```bash
rg -n 'with both "In this PR|Problem detail and follow-up scope|create it after the user approves the draft|every Format B.*Follow-up' skills/pr-review-comments/SKILL.md
```

Expected: no output.

- [ ] **Step 2: Verify all required routing concepts are present**

Run:

```bash
rg -n 'B-current|B-split|concrete blocker|Regression coverage|separate approval|Problem detail and implementation scope' skills/pr-review-comments/SKILL.md
rg -n 'capture its real number and URL|fresh (review-comment )?approval|required test infrastructure does not exist and cannot be added|unresolved product or architecture|any evidence-backed split' skills/pr-review-comments/SKILL.md docs/superpowers/specs/2026-07-21-pr-review-comments-scope-routing-design.md docs/superpowers/plans/2026-07-21-pr-review-comments-scope-routing.md
```

Expected: matches cover classification, templates, approval flow, positive issue creation, fresh approval after revisions, the full infrastructure condition, unresolved-decision escalation, writing rules, checklist, and examples.

- [ ] **Step 3: Read the scenario paths in order**

Run:

```bash
sed -n '/### Format A:/,/## GitHub API Details/p' skills/pr-review-comments/SKILL.md
```

Confirm these exact outcomes:

1. One complete, self-contained target with a valid suggestion and no deferred scope routes to Format A.
2. Multi-file work without a blocker routes to B-current and performs no issue mutation.
3. An evidence-backed split routes to B-split even if the current-PR mitigation has one target; with an existing issue, it links that issue.
4. Evidence-backed deferral without an issue pauses for separate issue-title-and-body approval.
5. Approved creation creates the missing issue, captures its real number and URL, and substitutes the pending marker before posting.
6. Declined issue creation produces no issue and no placeholder comment; a revised body returns for fresh review-comment approval before posting.
7. Production regression coverage stays in B-current; the infrastructure exception applies only when required test infrastructure does not exist and cannot be added within the current ticket.
8. A complete fix that depends on unresolved product or architecture decisions pauses for user direction instead of inventing a recommendation or scope boundary.
9. A standalone test gap routes to Format C.

- [ ] **Step 4: Run final Markdown and repository checks**

Run:

```bash
git diff --check origin/main...HEAD
git diff --name-only origin/main...HEAD
rg -n $'\u2014' skills/pr-review-comments/SKILL.md docs/superpowers/specs/2026-07-21-pr-review-comments-scope-routing-design.md docs/superpowers/plans/2026-07-21-pr-review-comments-scope-routing.md
git status --short --branch
```

Expected:

- `git diff --check` exits successfully with no output.
- The em-dash search returns no output.
- The branch is clean and the PR range changes only `docs/superpowers/specs/2026-07-21-pr-review-comments-scope-routing-design.md`, `docs/superpowers/plans/2026-07-21-pr-review-comments-scope-routing.md`, and `skills/pr-review-comments/SKILL.md`.
