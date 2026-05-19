# Analysis Prompts Reference

These prompts are used sequentially against the aggregated session data to generate the insights report. Run them in parallel where possible, then combine results.

## Facet Extraction (Per-Session)

Run this against individual session transcripts (user/assistant messages) to extract structured facets. Skip sessions with fewer than 2 user messages or under 1 minute duration.

```
Analyze this coding assistant session and extract structured facets.

RESPOND WITH ONLY A VALID JSON OBJECT matching this schema:
{
  "underlying_goal": "What the user fundamentally wanted to achieve",
  "goal_categories": {"category_name": count, ...},
  "outcome": "fully_achieved|mostly_achieved|partially_achieved|not_achieved|unclear_from_transcript",
  "user_satisfaction_counts": {"level": count, ...},
  "claude_helpfulness": "unhelpful|slightly_helpful|moderately_helpful|very_helpful|essential",
  "session_type": "single_task|multi_task|iterative_refinement|exploration|quick_question",
  "friction_counts": {"friction_type": count, ...},
  "friction_detail": "One sentence describing friction or empty",
  "primary_success": "none|fast_accurate_search|correct_code_edits|good_explanations|proactive_help|multi_file_changes|good_debugging",
  "brief_summary": "One sentence: what user wanted and whether they got it"
}
```

Valid goal categories: `debug_investigate`, `implement_feature`, `fix_bug`, `write_script_tool`, `refactor_code`, `configure_system`, `create_pr_commit`, `analyze_data`, `understand_codebase`, `write_tests`, `write_docs`, `deploy_infra`, `warmup_minimal`

Valid satisfaction levels: `frustrated`, `dissatisfied`, `likely_satisfied`, `satisfied`, `happy`, `unsure`

Valid friction types: `misunderstood_request`, `wrong_approach`, `buggy_code`, `user_rejected_action`, `claude_got_blocked`, `user_stopped_early`, `wrong_file_or_location`, `excessive_changes`, `slow_or_verbose`, `tool_failed`, `user_unclear`, `external_issue`

## Insight Generation Prompts

All prompts below receive the aggregated session data as `DATA:` appended after the prompt text.

### 1. Project Areas

```
Analyze this coding assistant usage data and identify project areas.

RESPOND WITH ONLY A VALID JSON OBJECT:
{
  "areas": [
    {"name": "Area name", "session_count": N, "description": "2-3 sentences about what was worked on and how the assistant was used."}
  ]
}

Include 4-5 areas. Skip internal operations (cache warmups, etc).
```

### 2. Interaction Style

```
Analyze this coding assistant usage data and describe the user's interaction style.

RESPOND WITH ONLY A VALID JSON OBJECT:
{
  "narrative": "2-3 paragraphs analyzing HOW the user interacts with the coding assistant. Use second person 'you'. Describe patterns: iterate quickly vs detailed upfront specs? Interrupt often or let the assistant run? Include specific examples. Use **bold** for key insights.",
  "key_pattern": "One sentence summary of most distinctive interaction style"
}
```

### 3. What Works

```
Analyze this coding assistant usage data and identify what's working well for this user. Use second person ("you").

RESPOND WITH ONLY A VALID JSON OBJECT:
{
  "intro": "1 sentence of context",
  "impressive_workflows": [
    {"title": "Short title (3-6 words)", "description": "2-3 sentences describing the impressive workflow or approach. Use 'you' not 'the user'."}
  ]
}

Include 3 impressive workflows.
```

### 4. Friction Analysis

```
Analyze this coding assistant usage data and identify friction points for this user. Use second person ("you").

RESPOND WITH ONLY A VALID JSON OBJECT:
{
  "intro": "1 sentence summarizing friction patterns",
  "categories": [
    {"category": "Concrete category name", "description": "1-2 sentences explaining this category and what could be done differently. Use 'you' not 'the user'.", "examples": ["Specific example with consequence", "Another example"]}
  ]
}

Include 3 friction categories with 2 examples each.
```

### 5. Suggestions

```
Analyze this coding assistant usage data and suggest improvements.

## FEATURES REFERENCE (pick from these for features_to_try):
1. **MCP Servers**: Connect to external tools, databases, and APIs via Model Context Protocol.
   - How to use: Configure MCP servers in your assistant's settings
   - Good for: database queries, Slack integration, GitHub issue lookup, connecting to internal APIs

2. **Custom Skills/Commands**: Reusable prompts defined as markdown files that run with a single command.
   - How to use: Create skill/command markdown files in your project config
   - Good for: repetitive workflows - commit, review, test, deploy, or complex multi-step workflows

3. **Hooks/Automation**: Shell commands that auto-run at specific lifecycle events.
   - How to use: Configure in your assistant's settings file
   - Good for: auto-formatting code, running type checks, enforcing conventions

4. **Non-Interactive/Headless Mode**: Run the assistant non-interactively from scripts and CI/CD.
   - How to use: Use CLI flags for non-interactive mode with allowed tools
   - Good for: CI/CD integration, batch code fixes, automated reviews

5. **Sub-Agents**: Spawn focused sub-agents for complex exploration or parallel work.
   - How to use: Ask the assistant to "use an agent to explore X" or let it auto-invoke
   - Good for: codebase exploration, understanding complex systems

RESPOND WITH ONLY A VALID JSON OBJECT:
{
  "config_additions": [
    {"addition": "A specific line or instruction to add to your assistant config (e.g. CLAUDE.md, AGENTS.md, .cursorrules) based on workflow patterns.", "why": "1 sentence explaining why this would help based on actual sessions", "prompt_scaffold": "Instructions for where to add this"}
  ],
  "features_to_try": [
    {"feature": "Feature name from FEATURES REFERENCE above", "one_liner": "What it does", "why_for_you": "Why this would help YOU based on your sessions", "example_config": "Actual command or config to copy"}
  ],
  "usage_patterns": [
    {"title": "Short title", "suggestion": "1-2 sentence summary", "detail": "3-4 sentences explaining how this applies to YOUR work", "copyable_prompt": "A specific prompt to copy and try"}
  ]
}

IMPORTANT for config_additions: PRIORITIZE instructions that appear MULTIPLE TIMES in the user data. If user told the assistant the same thing in 2+ sessions, that's a PRIME candidate.

IMPORTANT for features_to_try: Pick 2-3 from the FEATURES REFERENCE above. Include 2-3 items for each category.
```

### 6. On the Horizon

```
Analyze this coding assistant usage data and identify future opportunities.

RESPOND WITH ONLY A VALID JSON OBJECT:
{
  "intro": "1 sentence about evolving AI-assisted development",
  "opportunities": [
    {"title": "Short title (4-8 words)", "whats_possible": "2-3 ambitious sentences about autonomous workflows", "how_to_try": "1-2 sentences mentioning relevant tooling", "copyable_prompt": "Detailed prompt to try"}
  ]
}

Include 3 opportunities. Think BIG - autonomous workflows, parallel agents, iterating against tests.
```

### 7. Fun Ending

```
Analyze this coding assistant usage data and find a memorable moment.

RESPOND WITH ONLY A VALID JSON OBJECT:
{
  "headline": "A memorable QUALITATIVE moment from the transcripts - not a statistic. Something human, funny, or surprising.",
  "detail": "Brief context about when/where this happened"
}

Find something genuinely interesting or amusing from the session summaries.
```

## At a Glance (Final Summary)

Run this AFTER all other insights are generated, feeding it the combined results.

```
You're writing an "At a Glance" summary for a coding assistant usage insights report. The goal is to help the user understand their usage and improve how they use AI coding assistants.

Use this 4-part structure:

1. **What's working** - What is the user's unique style of interacting with the assistant and what are some impactful things they've done? Keep it high level. Don't be fluffy or overly complimentary. Don't focus on tool calls.

2. **What's hindering you** - Split into (a) Assistant's fault (misunderstandings, wrong approaches, bugs) and (b) user-side friction (not providing enough context, environment issues). Be honest but constructive.

3. **Quick wins to try** - Specific features they could try, or a workflow technique if compelling. (Avoid generic advice like "provide more context up front" which is less actionable.)

4. **Ambitious workflows for better models** - As models improve over the next 3-6 months, what should they prepare for? What workflows that seem impossible now will become possible?

Keep each section to 2-3 not-too-long sentences. Don't overwhelm the user. Don't mention specific numerical stats or underlined_categories from the session data. Use a coaching tone.

RESPOND WITH ONLY A VALID JSON OBJECT:
{
  "whats_working": "(refer to instructions above)",
  "whats_hindering": "(refer to instructions above)",
  "quick_wins": "(refer to instructions above)",
  "ambitious_workflows": "(refer to instructions above)"
}
```
