---
name: usage-insights
description: Generate a usage insights report analyzing coding assistant session history. Parses session JSONL logs, extracts metadata (tools used, languages, git activity, friction points), and produces a structured markdown analysis with actionable suggestions. Works with any assistant that stores sessions as JSONL. Use when the user says "/usage-insights", "analyze my sessions", "usage report", "how am I using this", "session insights", or asks to review their coding assistant usage patterns.
---

# Usage Insights

Generate a comprehensive usage report by analyzing coding assistant session logs.

## Workflow

### Step 1: Locate Session Logs

Ask the user where their session logs live if not obvious. Common locations:
- Claude Code: `~/.claude/projects/` (JSONL files, one per session)
- Custom: user-specified directory

### Step 2: Parse Sessions

Run the session parser to extract and aggregate metadata:

```bash
python3 <this-skill-dir>/scripts/parse_sessions.py --sessions-dir <PATH> --output /tmp/usage-insights-data.json --max-sessions 200
```

If `--sessions-dir` is omitted, it auto-detects `~/.claude/projects/` or `$CLAUDE_CONFIG_DIR/projects/`.

### Step 3: Generate Insights

Read `/tmp/usage-insights-data.json` and the prompts from `references/analysis-prompts.md`.

Using the aggregated JSON as context appended after each prompt's `DATA:` marker, run these analyses (in parallel where independent):

1. **Project Areas** - What the user works on
2. **Interaction Style** - How the user interacts
3. **What Works** - Impressive workflows and wins
4. **Friction Analysis** - Where things go wrong
5. **Suggestions** - Concrete improvements (config additions, features to try, usage patterns)
6. **On the Horizon** - Future workflow opportunities
7. **Fun Ending** - A memorable moment

### Step 4: At a Glance Summary

After all insights are collected, run the "At a Glance" prompt (from the references file) with the combined data plus insight results to produce a 4-part executive summary.

### Step 5: Write Report

Write the final report to `tmp-docs/insights-report-YYYY-MM-DD.md` (relative to the working directory), creating the directory if needed. Use today's date.

Format:

```markdown
# Usage Insights

[sessions] sessions - [messages] messages - [hours]h - [commits] commits
[date_range_start] to [date_range_end]

## At a Glance

**What's working:** [whats_working]

**What's hindering you:** [whats_hindering]

**Quick wins to try:** [quick_wins]

**Ambitious workflows:** [ambitious_workflows]

## Project Areas
[areas list with descriptions]

## Impressive Things You Did
[impressive_workflows with titles and descriptions]

## Where Things Go Wrong
[friction categories with examples]

## Suggestions

### Config Additions
[config_additions with why and where to add]

### Features to Try
[features_to_try with example configs]

### Usage Patterns to Adopt
[usage_patterns with copyable prompts]

## On the Horizon
[opportunities with copyable prompts]

---
*[fun_ending headline and detail]*
```

## Notes

- Sessions with fewer than 2 user messages or under 1 minute duration are excluded
- The parser handles malformed JSONL gracefully (skips bad lines)
- For very large session directories, limit to the 200 most recent sessions
- The session log format expected: JSONL where each line has `type` (user/assistant), `message` (with `content` and optionally `usage`), and `timestamp` fields
- Report output path is always `tmp-docs/insights-report-YYYY-MM-DD.md` relative to cwd
