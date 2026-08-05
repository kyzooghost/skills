# create-scoped-tickets - usability improvements

Audit of `skills/create-scoped-tickets/SKILL.md` from the perspective of a first-time user with no prior context on the ticket workflow. Findings ranked by impact.

## High-impact (real blockers for a stranger)

- [ ] **1. Make the ecosystem visible.** Nothing tells the reader that this skill's output feeds `scoped-planning`, `scoped-differential-review`, and `ship-from-plan`, or that the ticket template's headings (`The owner may`, etc.) are load-bearing structure those downstream skills parse. A stranger would see "Agent Work Ticket" as arbitrary formalism and might discard it. Add a short "Fits into" paragraph up top linking the four skills.

- [ ] **2. Add a Requirements / preflight section.** Silently assumes: GitHub (not GitLab/Jira), `gh` CLI installed + authenticated, issues enabled on the repo, write access, ability to create labels. First failure point tells the user, badly. Add a 5-line "Requirements" section.

- [ ] **3. Fix the invocation gap.** `/create-scoped-tickets <SPEC> --repo ...` implies a slash command, but this lives under `skills/` and there's no matching `commands/create-scoped-tickets.md`. Sibling skills do the same thing. A stranger will type the command and nothing happens. Either add the command file, or say "invoke via the Skill tool with these arguments".

- [ ] **4. Add a worked example.** Phase 4 says "emit the full drafted set as text in this order" but shows no sample output. Users don't know what a draft, amendment proposal, or coverage map actually looks like end-to-end. One neutral example (not blockchain-specific) would carry more weight than the 10 scenario exercises combined.

- [ ] **5. Surface the private ticket schema.** Almost no existing GitHub issue in the wild uses `The owner may` / `The owner must not`. The fallback ("ask user for owned/excluded scope in one line each") is workable, but nothing warns upfront that this skill is designed against tickets **you already wrote in this format**. State the assumption; link to the template so users can retrofit or generate first-time via seed mode.

- [ ] **6. Relocate the Verification section.** Ripgrep checks against `SKILL.md` itself are meta-tests for the skill authoring, not verification a user runs against their tickets. This confuses the intended audience. Move to a separate `AUTHORING.md` or a `## For contributors` section at the bottom, clearly labeled.

## Medium impact

- [ ] **7. Rewrite the description as triggering conditions only.** Per the `writing-skills` guidance, descriptions that summarize workflow let Claude shortcut the body. Change to something like: "Use when the user asks to seed or extend a GitHub label-scoped ticket set from a spec."

- [ ] **8. Add a 3-line glossary.** "Agent Work Ticket", "label universe", "scope map", "amendment proposal", "built-in defaults" all appear before their meaning is set.

- [ ] **9. Move the 10 scenario exercises out of SKILL.md.** They're valuable but buried in a 270-line file. Move to `references/scenarios.md`; SKILL.md should stay scannable.

- [ ] **10. Call out the silent formalism adoption.** Running this skill against a repo permanently commits the team to Agent Work Ticket structure (since Append mode requires it). Say so out loud.

## Low impact

- [ ] **11.** Multi-label rationale not explained - why would I ever pass two labels?
- [ ] **12.** `SCOPE_HINT` under-documented - one-line description, no "when to use" guidance.
- [ ] **13.** Example title flavor (`Besu Sidecar - Builder 2PC`) is niche; a neutral placeholder reads more universally.
- [ ] **14.** Amendments are text-only with no `gh issue edit` helper - efficiency loss.
- [ ] **15.** No forward pointer at the end ("Now run `scoped-planning` against these tickets").
- [ ] **16.** No `dry-run` keyword for discovery (Phase 4 is effectively a dry-run but the word isn't used).

## Recommended rollout

Biggest wins for other users are items 1-5, roughly one afternoon of edits, mostly additions rather than restructuring. Items 6, 7, 9 are cleanups that also serve the primary author (tighter skill for own use).

Options:
- **A.** Draft edits for the top block (1-5).
- **B.** Full high+medium set (1-10).
- **C.** Restructure into a proper multi-file skill (`SKILL.md` + `references/scenarios.md` + `AUTHORING.md`).
