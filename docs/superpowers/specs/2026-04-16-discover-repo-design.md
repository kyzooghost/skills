# /discover-repo Skill Design

## Summary

A skill that automates generating high-quality CLAUDE.md files for repositories. Dispatches 5 parallel Explore subagents to study different aspects of the codebase, then synthesizes findings into a structured CLAUDE.md following a proven template.

## Trigger

- `/discover-repo`
- "discover this repo", "generate a CLAUDE.md", "index this codebase"

## Invocation

- Runs against the current working directory (must be a repo root or significant subdirectory)
- No path arguments

## Output

- `CLAUDE.md` at the current directory root
- `CLAUDE.discovery.md` if `CLAUDE.md` already exists (never overwrites)

## Skill File Structure

```
skills/discover-repo/
  SKILL.md                          # Main skill definition
  references/
    template.md                     # Output template structure guide
    example-publisher-claude-md.md  # Full publisher/CLAUDE.md as quality reference
```

## Process

### Phase 1 - Parallel Discovery

Dispatch 5 Explore subagents simultaneously. Each gets a focused prompt and returns structured findings.

| Agent | Focus | Explores | Reports |
|-------|-------|----------|---------|
| **structure** | Directory tree, languages, build system | `ls`, file patterns (`**/*.rs`, `**/*.ts`, etc.), Makefile/Cargo.toml/package.json | Annotated directory tree with file purposes, language breakdown |
| **core-code** | Entrypoints, modules, key abstractions | Main/entrypoint files, module declarations, core types, public APIs | Component table (name, file, responsibility), data/execution flow |
| **docs** | README, specs, comments, purpose | README.md, docs/, existing CLAUDE.md (if regenerating), inline doc comments | Project purpose, protocol description, existing docs summary |
| **tests** | Test files, patterns, CI | Test directories, test files, .github/workflows, CI configs | Test count table, testing approach, CI description |
| **config** | Config, env vars, deployment, deps | Config files, .env templates, Dockerfile, docker-compose, dependency manifests | Build commands, config reference, deployment targets, dependency highlights |

Each agent prompt includes:
- What to look for (specific file patterns and keywords)
- What format to report in (structured sections matching template needs)
- Instruction to cite exact file paths and line numbers
- Instruction to flag uncertainty with [NEEDS VERIFICATION]

### Phase 2 - Synthesis

Main agent reads all 5 subagent reports and composes the CLAUDE.md:
1. Deduplicate and cross-reference findings
2. Identify the most noteworthy implementation choices (non-obvious decisions)
3. Build accurate data/execution flow descriptions
4. Use the template structure to organize all sections
5. Use the publisher example as a quality benchmark
6. Flag anything uncertain with [NEEDS VERIFICATION]

Key synthesis rules:
- Tables over prose
- ASCII diagrams for architecture/data flow
- Exact file paths with one-line descriptions
- "Why" not just "what" for implementation choices
- Never invent details not found by subagents
- Scale section depth to complexity (a few lines for simple things, paragraphs for complex ones)

### Phase 3 - Write

1. Check if `CLAUDE.md` exists in the current directory
2. If yes: write to `CLAUDE.discovery.md`
3. If no: write to `CLAUDE.md`
4. Report what was written and where

## Output Template Structure

```markdown
# {Project Name} - Index & Architecture Summary

{One paragraph: what this repo does and why it exists}

---

## 1. Purpose

{2-3 paragraphs explaining the project's purpose, key capabilities, and context}

---

## 2. Architecture

### 2.1 Directory Tree

{Annotated directory tree showing key files with one-line descriptions}

### 2.2 Key System Components

{Table: Component | Location | Responsibility}

### 2.3 Data Flow

{ASCII diagram showing how data moves through the system}

### 2.4 Execution Flow / Lifecycle

{Step-by-step description of the main happy path(s)}

---

## 3. Noteworthy Implementation Choices

{Each choice as a ### subsection: what the choice is, then why}

---

## 4. Key Data Types (if applicable)

{Tables of core types/interfaces and their purpose}

---

## 5. Test Infrastructure

{Test count table by file/directory, testing approach description}

---

## 6. Build/Dev Workflow

{Prerequisites, build/test/lint commands, configuration, CI}

---

## 7+ Additional Sections (as warranted)

{Deployment targets, branch strategy, dependency highlights, key terminology, etc.}
```

## Quality Standards

The output should match the quality of the publisher/CLAUDE.md and specs/CLAUDE.md examples:

1. **Accuracy**: Every file path must exist. Every described behavior must be verifiable in code.
2. **Depth**: Component descriptions include specific method names and behavioral details, not just vague summaries.
3. **Structure**: Tables for structured data. ASCII diagrams for flows. Annotated trees for directories.
4. **Completeness**: All major components covered. No significant files omitted from the tree.
5. **Honesty**: Uncertain claims flagged with [NEEDS VERIFICATION].

## Constraints

- The skill must work for any language/framework - not hardcoded to Rust/Solidity/etc.
- Subagent prompts must be generic enough to handle diverse codebases
- The template sections are guidelines, not rigid requirements - skip sections that don't apply (e.g., "Key Data Types" for a simple CLI tool)
- Never fabricate file paths or code patterns not found by subagents
