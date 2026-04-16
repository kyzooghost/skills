---
name: discover-repo
description: Generate a comprehensive CLAUDE.md index for a repository. Dispatches parallel subagents to study directory structure, core code, docs, tests, and config, then synthesizes findings into a structured guide for future Claude sessions. Triggers on "/discover-repo", "discover this repo", "generate a CLAUDE.md", "index this codebase", or "study this repo". Use when onboarding to a new codebase or creating documentation for AI-assisted development.
---

# Discover Repo

Generate a high-quality CLAUDE.md that serves as an index and architecture guide for the current repository.

## Output

- `CLAUDE.md` at the current directory root
- `CLAUDE.discovery.md` if `CLAUDE.md` already exists (never overwrite)

## Process

### Phase 1 - Parallel Discovery

Dispatch 5 Agent subagents simultaneously using `subagent_type: "Explore"`. All 5 MUST be dispatched in a single message for parallel execution.

Replace `{cwd}` with the actual current working directory in each prompt.

**Structure Agent:**
```
Explore the repository at {cwd}. Map the directory structure.

Report in clean markdown:

1. DIRECTORY TREE - Annotated tree of the repo showing key files/directories with one-line descriptions.
   - 3 levels deep for all directories, up to 5 levels for src/, lib/, core/, and other source directories
   - Annotate each significant file with a one-line description
   - Skip node_modules/, target/, build/, dist/, .git/, __pycache__/, vendor/

2. LANGUAGES & BUILD SYSTEM - Languages used, build tool (Cargo, npm, Make, etc.), key config files

3. FILE COUNTS - Approximate source file count by language/extension

Cite exact file paths. Be thorough but concise.
Flag anything uncertain with [NEEDS VERIFICATION].
```

**Core Code Agent:**
```
Explore the repository at {cwd}. Understand the core code architecture.

Report in clean markdown:

1. ENTRYPOINTS - Main/entrypoint files (main.rs, main.go, index.ts, etc.). What each does.

2. KEY COMPONENTS TABLE - For each major module/component/service:
   | Component | File(s) | Responsibility |
   Include specific method/function names that define the component's behavior.

3. DATA FLOW - How data moves through the system. Trace the main happy path from input to output.

4. EXECUTION FLOW - Step-by-step: what happens when the main operation runs.

5. KEY ABSTRACTIONS - Core types, traits/interfaces, data structures. Name, file, one-line description.

6. IF APPLICABLE (include only if found):
   - API routes/endpoints table (HTTP, RPC, WebSocket) with method, path, handler, description
   - Wire protocol or message types table (tags, payload types, directions)

Cite exact file paths and line numbers. Focus on architecture, not implementation details.
Flag anything uncertain with [NEEDS VERIFICATION].
```

**Docs Agent:**
```
Explore the repository at {cwd}. Extract the project's purpose and existing documentation.

Report in clean markdown:

1. PURPOSE - What does this project do? Why does it exist? Synthesize from README, doc comments, and code.

2. KEY CAPABILITIES - Bullet list of what the system can do.

3. EXISTING DOCS - List all documentation files with a one-line summary of each.

4. PROTOCOL/DOMAIN CONTEXT - If domain-specific: terminology, external system interactions.

5. NOTEWORTHY COMMENTS - Significant code comments explaining architectural decisions (grep for TODO, HACK, NOTE, IMPORTANT, SAFETY, INVARIANT).

6. CROSS-REPO CONTEXT (if applicable) - How this repo relates to sibling repos, external services, or a broader system. Import/dependency relationships with other repos.

7. HARD-WON RULES (if applicable) - Look for lessons-learned files, "do not" comments, removed-code notes, or operational rules embedded in docs/comments. These encode negative knowledge (what NOT to do).

Cite exact file paths. Prefer direct quotes over paraphrasing.
Flag anything uncertain with [NEEDS VERIFICATION].
```

**Tests Agent:**
```
Explore the repository at {cwd}. Understand the test infrastructure.

Report in clean markdown:

1. TEST FILES TABLE:
   | File/Directory | Tests (approx) | What it tests |

2. TESTING APPROACH - Unit? Integration? E2E? Frameworks? Test utilities/helpers?

3. CI CONFIGURATION - Read CI configs (.github/workflows/, etc.). What runs, what gates merges.

4. TEST COMMANDS - How to run tests.

Cite exact file paths. Count test functions where possible.
Flag anything uncertain with [NEEDS VERIFICATION].
```

**Config Agent:**
```
Explore the repository at {cwd}. Understand configuration, dependencies, and deployment.

Report in clean markdown:

1. BUILD COMMANDS - How to build, test, lint, format. Check Makefile, justfile, package.json scripts, etc.

2. CONFIGURATION - Config files, environment variables, .env templates.

3. DEPENDENCIES - Top 10-15 most important dependencies and their purpose.

4. DEPLOYMENT - Dockerfile, docker-compose, K8s manifests. Deployment targets.
   - If multiple deployment targets exist, list them in a table: environment name, config location, notes.
   - If Docker services have dependencies or startup order, note them.

5. PREREQUISITES - What needs to be installed to develop on this project?

6. IF APPLICABLE (include only if found):
   - Deployed addresses or network registries (blockchain projects)

Cite exact file paths. Include actual command examples from the repo's tooling.
Flag anything uncertain with [NEEDS VERIFICATION].
```

### Phase 2 - Synthesis

After all 5 agents complete, synthesize their reports into a single CLAUDE.md.

Read [references/template.md](references/template.md) for the output structure.
Read [references/example-publisher-claude-md.md](references/example-publisher-claude-md.md) as a quality benchmark.

Synthesis rules:
- Deduplicate and cross-reference findings across all 5 agent reports
- Build accurate data/execution flow descriptions from agent findings
- Tables over prose for structured data
- ASCII diagrams for architecture and data flow
- Every file path must come from agent reports - never fabricate
- Scale section depth to complexity
- Skip template sections that don't apply
- Flag uncertain claims with [NEEDS VERIFICATION]
- For "Noteworthy Implementation Choices": explain WHY, not just WHAT

### Phase 3 - Write

1. Check if `CLAUDE.md` exists in the current directory
2. If exists: write to `CLAUDE.discovery.md`
3. If not: write to `CLAUDE.md`
4. Report what was written and where
