# pr-review-comments Format B Conciseness Design

## Summary

Restructure Format B in `skills/pr-review-comments/SKILL.md` to roughly halve comment verbosity. The four-section skeleton (human summary, recommendation summary, problem detail, recommendation detail) duplicates every point twice: Section 4 is defined as an expanded version of Section 2, and Section 3 restates Section 1 with citations. Companion comments repeat the full skeleton per file. This design replaces the skeleton with a three-part shape (what's wrong, Fix, collapsed detail block), reduces companions to stubs, and moves diagrams, failure scenarios, and follow-up task lists behind a `<details>` fold.

Reference for the problem: the MEDIUM-1 comments on kyzooghost/lineth-xcall-besu-plugin PR 10, where the primary comment is roughly 1,000 words and each companion restates the primary.

## Goals

- Format B comments read in halved length: title, what's wrong, and Fix above the fold; evidence and follow-up scope behind one `<details>` block.
- Eliminate structural duplication: each point is written exactly once, either above or below the fold.
- Companion comments become stubs: title, 1-2 sentence angle, optional suggestion block, link to primary.
- Keep the in-PR vs follow-up-ticket split explicit above the fold.

## Non-goals

- No changes to Format A (single-target fix) or Format C (test gap).
- No hard word budgets; the existing "every word earns its place" writing rules carry sentence-level discipline.
- No changes to the posting procedure's API mechanics or the "STOP and show the user the draft" gate.
- No changes to the diagram drawing style itself, only to where diagrams live.

## Format B Primary Structure

Replace the four-section skeleton with:

````
**[SEVERITY-N] Title that captures the defect**

<What's wrong: 2-4 sentences, plain English. What breaks, when it breaks, why
it matters. No citations, no diagrams.>

**Fix**

- **In this PR (#TICKET):** <one-line change summary, then the
  ```suggestion``` block if the in-PR fix lands on this file>
- **Follow-up ticket:** <one line: what splits out and why it cannot land in
  this PR>

<details>
<summary>Problem detail and follow-up scope</summary>

<Citations (file:line), ASCII diagram, end-to-end failure scenario,
exploitability bound, and the numbered follow-up task list.>

</details>
````

Rules:

- Delete the "Section 4 is an expanded version of Section 2" instruction. Each Fix bullet is written once and is self-contained.
- The `<details>` block adds evidence and the follow-up task breakdown. It never restates the Fix bullets or the what's-wrong intro.
- The `---` horizontal-rule separators between sections are removed; the bold **Fix** header and the `<details>` fold provide the structure.
- If the in-PR fix does not land on this file, the "In this PR" bullet says so and points at the file where it lands (unchanged from current behavior).
- If the in-PR fix is too large for a suggestion block or spans non-contiguous edits, the "In this PR" bullet carries a one-line summary and the full description (fenced code block or diagram) goes inside `<details>`.

## Companion Structure

Companions become stubs:

````
**[SEVERITY-N] Exact same title as primary**

<1-2 sentences: this file's specific angle on the finding.>

<```suggestion``` block, only if this file carries an in-PR fix>

See primary comment: <primary html_url>
````

- No Fix section, no `<details>` block, no problem detail.
- Site-specific reasoning that needs depth goes into the primary's `<details>` block, not into the companion.
- Unchanged rules: title verbatim from the primary (no rewording, no sub-titles), angle expressed in the intro sentences, footer uses the primary's real `html_url`, `[TEST GAP]` companions keep their own marker.

## `<details>` Conventions

- Fixed summary line: `Problem detail and follow-up scope`.
- Blank line after `<summary>...</summary>` and before `</details>`, so GitHub renders the markdown inside the fold.
- Suggestion blocks never go inside `<details>`: GitHub's apply button and scanning reviewers must see them above the fold.
- Diagrams live only inside `<details>`.

## Ripple Edits to SKILL.md

- **Frontmatter description**: rewrite the Format B clause. "four-section skeleton with explicit ... split-scope" becomes "concise what's-wrong + Fix with collapsed detail block and stub companions, explicit in-PR vs follow-up-ticket split".
- **Worked examples**: replace the two long companion examples with one stub-companion example. Rewrite the primary example in the new shape, condensed from the real MEDIUM-1 comment on lineth-xcall-besu-plugin PR 10 at roughly half its posted length.
- **Writing rules**:
  - "Every word earns its place in Section 1 and Section 2" becomes "every word earns its place above the fold" (everything outside `<details>`).
  - Rewrite the fixed-section-order rule for the new shape: title + what's wrong, Fix, `<details>`. Order remains fixed.
  - Rewrite the suggestion-block-placement rule: the suggestion lives inside the "In this PR" bullet of Fix; never inside `<details>`.
  - Sentence-level rules survive unchanged: no preambles, positive framing, parallel structure, power notation for ranges, cut filler qualifiers, read-aloud test.
- **Checklist**: replace the four-section items with:
  - Above the fold contains only title, what's-wrong intro, and Fix.
  - `<details>` block present with the fixed summary line and blank-line spacing so it renders.
  - No content duplicated across the fold.
  - Companions are stubs: verbatim title, 1-2 sentence angle, optional suggestion, primary link. No Fix section or `<details>`.
- **Procedure**: step 4 (decide the in-PR vs follow-up split before drafting) is unchanged. Step 5's Format B display note changes from "including all four sections" to "including the `<details>` block content".

## Error Handling

Not applicable; this is a prose skill change with no executable code.

## Testing

Manual verification: draft the PR 10 MEDIUM-1 primary and its two companions in the new shape and confirm the primary reads at roughly half the posted length with no information lost (everything from the old Sections 3/4 is present inside `<details>`), and each companion fits on one screen.
