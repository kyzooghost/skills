# pr-review-comments Current-PR Scope Routing Design

## Summary

Amend `skills/pr-review-comments/SKILL.md` so comment complexity and delivery scope are separate decisions. A finding can require Format B because it spans multiple files without requiring a follow-up issue. Format B will support an all-in-current-PR mode and a justified split-scope mode, with the all-in-current-PR mode as the default.

The complete production fix and its regression coverage stay in the reviewed PR unless concrete evidence shows that part of the work cannot reasonably land there. Creating a new follow-up issue requires separate user approval after the review-comment draft is approved.

## Problem

The current skill conflates two independent properties:

1. **Comment complexity:** whether the finding needs a multi-file Format B thread.
2. **Delivery scope:** whether part of the fix must be deferred to another ticket.

`SKILL.md:49-51` selects Format B for either a multi-file finding or a split recommendation. The Format B template at `SKILL.md:61-68` then requires both an **In this PR** bullet and a **Follow-up ticket** bullet. The procedure at `SKILL.md:223-231` and checklist at `SKILL.md:333-336` reinforce that requirement and direct the agent to create an issue when none exists.

This makes an implementation detail of the comment format drive project scope. Multi-file production fixes and their regression tests can be incorrectly deferred even when they are directly required by the reviewed change and have no external dependency.

## Goals

- Keep the complete production fix and regression coverage in the current PR by default.
- Support multi-file Format B comments without requiring follow-up language or an issue.
- Permit split scope only when the skill can cite concrete evidence that part of the work cannot reasonably land in the current PR.
- Require separate user approval before creating a follow-up issue.
- Preserve Format B's concise primary comment, collapsed evidence, and stub companions.
- Make classification and checklist rules internally consistent so the unnecessary-ticket behavior does not recur.

## Non-goals

- Change Format A's single-target suggestion structure.
- Change Format C for standalone test-coverage findings.
- Change GitHub review-comment API mechanics or the existing approval gate before posting.
- Decide the implementation for a reviewed finding; the skill still recommends scope and waits for user approval.
- Prohibit follow-up tickets when a real scope boundary or dependency exists.

## Classification Model

Select the comment format from presentation complexity and the split-recommendation exception:

- **Format A:** one self-contained, complete recommendation at one target, with a valid suggestion block and no deferred scope.
- **Format B:** a multi-file, non-contiguous, or structurally complex finding, or any evidence-backed split recommendation even when the current-PR mitigation has one target.
- **Format C:** a standalone test-gap finding whose primary defect is missing coverage.

After selecting Format B, select one delivery mode independently.

### B-current: complete fix in the current PR

`B-current` is the default. It applies when the production fix and regression coverage can reasonably land in the reviewed PR, including when the work:

- spans multiple files;
- requires structural changes;
- does not fit in a suggestion block;
- adds or updates regression tests; or
- is LOW severity.

None of those properties justifies a follow-up ticket by itself.

### B-split: evidence-backed scope split

`B-split` applies only when at least one of these conditions is established from the user, governing ticket, repository, or dependency state:

- The user, maintainer, or governing ticket explicitly excludes the work from the current PR.
- An unmet prerequisite or dependency blocks implementation.
- The work belongs to another repository, owner, release, or deployment boundary.
- Required test infrastructure does not exist and cannot be added within the current ticket.

The skill must cite the qualifying evidence in the draft. Statements such as "too large," "architectural," or "better as follow-up" do not qualify without a concrete scope boundary or blocker.

If no qualifying evidence exists, select `B-current`.

## Format B Primary Templates

Both modes retain the fixed order: title, plain-English impact, **Recommended fix**, horizontal rule, and collapsed details.

Use one neutral details summary for both modes:

```html
<summary><b>Problem detail and implementation scope</b></summary>
```

### B-current template

````markdown
**[SEVERITY-N] Title that captures the defect**

<What's wrong: 2-4 sentences, including the bounded impact.>

**Recommended fix**

- **In this PR:** <the complete production fix and regression coverage>

---

<details>
<summary><b>Problem detail and implementation scope</b></summary>

<Evidence, failure scenario, exploitability bound, full fix description when
it does not fit above the fold, and a numbered In-PR task list.>

</details>
````

`B-current` contains no follow-up placeholder, ticket search, or issue-creation step.

### B-split template

````markdown
**[SEVERITY-N] Title that captures the defect**

<What's wrong: 2-4 sentences, including the bounded impact.>

**Recommended fix**

- **In this PR:** <a safe and independently complete in-PR change>
- **Follow-up ticket (#ISSUE):** <deferred work and the concrete blocker>

---

<details>
<summary><b>Problem detail and implementation scope</b></summary>

<Evidence, failure scenario, exploitability bound, cited split evidence,
and separate numbered task lists for the current PR and follow-up ticket.>

</details>
````

The in-PR change must stand alone safely. A partial mitigation that leaves the reviewed feature in an invalid state does not qualify merely because the remainder is deferred.

When no issue exists yet, the user-visible draft marks the ticket as pending separate approval. That draft must not be posted until issue creation is approved and the real issue number replaces the marker.

## Regression Coverage Policy

Regression coverage for a production finding is part of that finding's current-PR fix by default. It appears in the `B-current` **In this PR** bullet and task list rather than becoming a separate follow-up issue.

Coverage may move to `B-split` only when the required harness or prerequisite does not exist and cannot be added within the current ticket. The draft must state that blocker. Format C remains available when the submitted finding is solely about missing tests rather than a production defect plus its regression coverage.

## Approval and Issue-Creation Flow

The procedure becomes:

1. Identify the finding.
2. Classify the comment as Format A, Format B, or Format C using the classification model, including the evidence-backed split exception.
3. For Format B, select `B-current` by default and evaluate the split-eligibility conditions.
4. Locate the exact diff anchors and companion targets.
5. Show the user the full comment draft, Format B mode, companion targets, and any split evidence.
6. Wait for explicit approval of the review-comment draft.
7. If an approved `B-split` draft has no existing issue, show the proposed issue title and body and request separate approval to create it.
8. If issue creation is approved, create the issue, capture its real number and URL, replace the pending marker in the approved `B-split` body, and post the comments.
9. If issue creation is declined, do not post a placeholder or unlinked split comment. Revise the finding to `B-current` or use an existing issue supplied by the user, then return to the review-comment draft gate for fresh approval of the complete rendered body. The same fresh approval is required when substituting a different existing issue.

Approval of a review-comment draft does not imply approval to create a GitHub issue.

## Companion Comments

Companion behavior remains unchanged for both Format B modes:

- Use the primary title verbatim.
- Add only the file-specific angle and an optional valid suggestion block.
- Link to the posted primary comment.
- Do not repeat the **Recommended fix** section or collapsed details.

The number of affected files influences companion selection, not delivery scope.

## Required SKILL.md Edits

Update these sections together so no stale rule recreates the mandatory-ticket behavior:

1. **Frontmatter description:** describe Format B as supporting current-PR and justified split-scope modes.
2. **Format B heading and introduction:** explain that multi-file shape does not imply deferred scope.
3. **Primary template:** make the follow-up bullet conditional and use the neutral details summary.
4. **Follow-up linking guidance:** apply it only to `B-split` and add the separate issue-creation approval.
5. **Worked examples:** add a multi-file `B-current` example where production changes and tests land together. Retain or replace the existing `B-split` example only if it states verified split evidence rather than size alone.
6. **Procedure:** separate format classification from the Format B scope-mode decision.
7. **Writing rules:** replace the unconditional split instruction with the current-PR default and evidence requirement.
8. **Checklist:** add conditional checks for `B-current` and `B-split`; remove the requirement that every Format B primary contain and link a follow-up ticket.

## Error Handling

- If split evidence is missing, vague, or inferred only from complexity, use `B-current`.
- If the user rejects the proposed split, revise the draft before any GitHub mutation.
- If a required issue already exists, link it rather than creating a duplicate.
- If issue creation fails, report the error and stop before posting comments that reference a nonexistent ticket.
- If the complete fix genuinely cannot be described without unresolved product or architecture decisions, ask the user for direction rather than inventing a boundary.

## Verification

Manually exercise the amended skill against these scenarios:

1. A complete, self-contained one-target recommendation with a valid suggestion and no deferred scope selects Format A.
2. A multi-file visibility fix plus bytecode assertions selects `B-current`, contains one **In this PR** bullet, and creates no issue.
3. An evidence-backed split selects `B-split` even when its current-PR mitigation has one target, and a cited existing dependency links the existing issue.
4. A justified split without an issue pauses after comment approval, displays the proposed issue title and body, and requests separate creation approval.
5. Approving issue creation creates the issue, captures its real number and URL, and substitutes the pending marker before posting.
6. Declining issue creation results in no issue and no placeholder split comment; any revised body returns for fresh review-comment approval before posting.
7. Regression tests remain in the current PR unless required test infrastructure does not exist and cannot be added within the current ticket.
8. A complete fix that depends on unresolved product or architecture decisions pauses for user direction instead of inventing a `B-current` recommendation or scope boundary.
9. A standalone missing-test finding still selects Format C.

Static verification should also confirm:

- No unconditional instruction says every Format B comment needs both bullets.
- No checklist item requires a follow-up issue for `B-current`.
- Every issue-creation instruction is conditional on `B-split` and separate approval.
- Approved issue creation captures the real issue number and URL and substitutes the pending marker before posting.
- Every materially revised review-comment body receives fresh approval before posting.
- The details summary is consistently `Problem detail and implementation scope`.
- The existing concise-above-the-fold and companion-stub rules remain intact.

## Success Criteria

The amendment is successful when a multi-file finding with no external blocker produces an approved Format B review thread that keeps the full fix and regression coverage in the current PR and performs no issue mutation. A follow-up issue is created only for an evidence-backed `B-split` finding after the user separately approves the issue draft.
