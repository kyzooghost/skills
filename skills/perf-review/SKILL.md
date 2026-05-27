---
name: perf-review
description: Use when drafting a periodic performance review (annual review, mid-year, promo packet, peer feedback) from monthly win reports and supporting sources, where the goal is prose-form answers grounded in verifiable evidence.
---

# Drafting a Performance Review from Win Reports

## Overview

The user keeps monthly `wins-YYYY-MM.md` notes in this repo as raw source material. This skill turns those notes into prose review answers grounded in evidence verifiable via the available MCPs (typically GitHub, Slack, Notion). The output is a draft the user iterates on - not a finished form.

## When to Use

Use when the user asks for a draft of an annual review, mid-year review, promo packet narrative, peer feedback, or any periodic write-up that synthesises the last 3-12 months of work into prose answers.

Do NOT use for: writing the monthly win reports themselves (those are raw notes, different shape), real-time status updates, or public-facing material (private-info redaction here is calibrated for internal HR forms).

## Process

1. **Gather inputs.** The target form (the questions). Any sample or prior review the user provides - this is the strongest style anchor, copy its conventions. All monthly win reports in scope. The prior cycle review for cross-reference.
2. **Read everything before drafting.** The saga lives in cross-month references; skim-then-draft produces shallow answers.
3. **Map to themes.** Identify the 1-2 dominant sagas plus supporting evidence per question. Most reviews have a dominant deliverable that anchors several questions - lean on it.
4. **Verify quantitative claims via MCPs.** Numbers, dates, counts, severities - look them up, do not infer from memory. GitHub for PR/issue counts, audit-finding severities, exact merge dates. Slack for first-mention dates (when the user originally raised X vs when it became urgent). Notion for design doc context and decision threads. If something cannot be verified, flag it rather than guess.
5. **Draft prose.** Match the format of any provided sample (prose-only vs bulleted, links vs none, paragraph density, voice). Default budget: 1-2 paragraphs per question, with flexibility on the lead question. First-person, human voice.
6. **Self-review** against the principles below.
7. **Iterate.** Expect the feedback patterns in the table below; re-verify any factual claim you adjust.

## Writing Principles

- **First-person, human-sounding.** Not corporate.
- **Specific over generic.** Name the project, the decision, the outcome.
- **Each answer stands alone.** Don't depend on an appendix the form may not have.
- **No jargon without brief explanation.** Reader is the user's engineering manager, not a domain peer.
- **Supportive tone for strengths, hedged tone for unfinished growth areas.** No inflated claims; everything grounded in evidence.
- **Be concise - density over length.** If 2 paragraphs can carry the same content as 3, use 2. Every sentence earns its place.
- **Write for an engineering manager, not an engineer.** Describe impact and outcomes at a level a non-practitioner can follow. Avoid laundry lists of technologies - abstract them up to the capability they provide.

  Example: instead of *"Helm chart archetypes, Argo Rollouts, per-app vault isolation, Istio egress centralization"*, write *"deployment automation, secret management, networking, and safe rollout strategies."* If the form has an Evidence Appendix, technical specifics live there; if not, they stay collapsed in prose.

- **Use dot points when they improve scannability.** If an answer contains 3+ parallel items (tools, examples, challenges), present them as a bulleted list rather than embedding them in prose. Dot points are easier to scan for an EM reading multiple reviews.
- **Quantify business impact where defensible.** Don't leave impact as abstract ("a revenue stream") when a concrete order of magnitude is supportable ("a seven-figure annualised revenue stream"). Back-of-envelope math from verifiable inputs (TVL, staking APR, retention share) is fine - just don't fabricate precision.
- **Concrete stakes over generic pressure.** "Under audit pressure" is vague; "during the second-last working week of the year on an expensive audit engagement" is specific and lands harder. Name what made the situation high-stakes.
- **Don't hedge live results.** If something is deployed and running, state it as fact. "Potential" or "expected" undermines work that is already real.
- **Inline evidence near the claim.** Place evidence citations (links, dates) directly after the paragraph they support, not in a separate appendix the reader has to scroll to. The reader shouldn't have to leave the paragraph to verify it.
- **Problem then outcome for strategic contributions.** When describing a framework or direction-setting contribution, name the problem it solved ("a confusing landscape with no shared vocabulary") before the outcome ("put the team on a shared page with clear paths forward"). Problem-first framing makes the value self-evident.
- **Connect to prior review cycle.** Explicitly tie achievements back to growth areas called out in the prior review. This shows trajectory and self-awareness, which EMs value highly.

## Common Feedback Patterns to Anticipate

| Feedback | What to adjust |
|---|---|
| "Don't mention $X / customer name / unannounced product" | Strip private info: dollar figures, internal strategy, unreleased products |
| "Too implementation-level for executive reading" | Collapse engineering detail to outcome and decision; remove tech-stack names |
| "Use months / dates, not 'months'" | Verify specific dates via Slack MCP (first message timestamp) or GitHub (merge date) |
| "I didn't lead this" | Reattribute - "active participant in X led by Y" |
| "Cannot claim 'first' / 'team's first'" | Hedge to "one of the very first" or drop the claim |
| "What is X? I think you invented this" | Remove and ask the user to clarify the actual deliverable |
| "Paragraph too long" | Break at natural seams; target 4-6 lines per paragraph |
| Technology laundry list | Abstract up to capability ("deployment automation, secret management, ...") |
| "I didn't solely own this" / "someone else owned the risk" | Reattribute - "I owned the implementation; [name/role] owned the risk posture / consequences" |
| "Guardrails" described inaccurately | Describe the actual security risks the guardrails address (e.g., non-deterministic execution, exfiltration) rather than just the symptom they prevent |
| "This wasn't the only factor" | Soften exclusivity claims - "the main constraint" not "the only thing" - unless it is literally the sole factor |
| Impact left as abstract noun | Quantify - "a revenue stream" becomes "a seven-figure annualised revenue stream" when the math is defensible |

## Common Mistakes

- Drafting from conversational memory instead of re-reading the source files.
- Inferring quantitative claims instead of verifying in the actual report.
- Importing engineering-team framing into executive HR-form prose.
- Inflating contributions ("led" when the truth is "active participant").
- Claiming sole ownership ("I owned the full thing") when another person owned the risk or consequences - reattribute to implementation vs outcome ownership.
- Including private financial, customer, or unannounced-strategy details.
- Ignoring the format of the sample the user provided as the style anchor.
- Using Slack DM links as evidence - DMs are not accessible to other readers. Always prefer Slack channel links or GitHub PR/issue links that anyone in the org can open.
- Hedging results that are already live ("potential revenue" when deposits are actively flowing).
- Using generic pressure language ("under pressure", "tight timeline") instead of naming the specific stakes.

## Format Mirroring Rule

If the user provides a prior review as a sample, copy its format conventions exactly: prose-only vs bulleted, link-inclusive vs no links, first-person voice, paragraph density, presence or absence of an Evidence Appendix. The sample is the strongest signal of what the user actually wants to submit.
