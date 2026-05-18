---
name: handover
description: Prepare a structured handover document from the current session for a fresh Claude session to continue the work. Use when the user says "/handover", "prepare a handover", "write a handover", "session summary for next time", or when wrapping up a complex debugging/implementation session that will be continued later. Captures problem context, locked decisions, dead ends, running state, key files/commands, artifacts, open questions, and next steps so zero context is lost between sessions.
---

# Session Handover

Produce a structured handover that gives the next fresh Claude session everything it needs to continue without re-discovery.

## Process

1. **Scan the conversation** for: problem statement, investigation steps, decisions made, files touched, commands run, current state, failed approaches, and unresolved questions.
2. **Active state capture** - Run relevant diagnostic commands (git status, kubectl, build state, etc.) to capture live state. If commands fail or aren't available, fall back to what's known from the conversation.
3. **Write the handover** to `tmp-docs/handover-YYYY-MM-DD-<topic>.md` (use kebab-case topic slug). If user specifies a different path, use that instead.

## Output Structure

Every section is **mandatory**. Write "None" if a section is genuinely empty.

```markdown
## Session Handover ({date}, session `{first_8_chars_of_session_id}`)

### Problem Statement
# 1-3 sentences. What is being solved and why. Include the user-facing symptom.

### Key Decisions Locked
# Bulleted list of decisions that are FINAL and should NOT be revisited.
# Include rationale in parentheses so the next session understands WHY.

### Dead Ends
# Approaches tried that failed. Format:
# - **What was tried** - why it didn't work
# Prevents the next session from repeating failed approaches.

### Running State
# Table or bullets showing current state of relevant systems/components.
# Note the timestamp/conditions under which state was observed.
# e.g., pod status, deploy state, test results, feature flag state.

### Key Files & Commands
# Table: File | Repo/Location | Why it matters
# Then a fenced code block of the most useful diagnostic/operational commands.
# Include ACTUAL paths, ACTUAL command strings - not placeholders.

### Artifacts
# Table: Link | Type | Status | What it does
# PRs, commits, Jira tickets, Confluence pages created or referenced.

### Open Questions
# Things not yet answered that the next session may need to investigate.
# Include enough context for the question to be actionable standalone.

### Next Steps
# Numbered, ordered list of what to do next.
# Each step must be specific and actionable.
# Include verification criteria: how to confirm the step succeeded.
```

## Guidelines

- **Be concrete, not abstract.** Include actual file paths, actual command strings, actual error messages. "Check the logs" is useless; `kubectl logs -n cbp-web -l app=commbiz-web --since=5m | grep -i "statusCode"` is useful.
- **Capture the "why" behind decisions.** The next session has no conversation context - it needs to know WHY an approach was chosen or rejected.
- **Running state is a snapshot.** Note when it was captured so the next session knows if it might be stale.
- **Keep it scannable.** Tables for structured data. Bullets for lists. No paragraphs where a table row suffices.
- **Commands must be copy-pasteable.** No pseudocode or partial commands in the Key Commands section.
- **Dead ends save time.** Even a one-liner like "Tried X, failed because Y" prevents hours of repeated investigation.
