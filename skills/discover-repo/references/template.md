# CLAUDE.md Output Template

Use this structure as a guide. Skip sections that don't apply. Scale each section's depth to the complexity of the topic.

```markdown
# {Project Name} - Index & Architecture Summary

{One paragraph: what this repo does and why it exists. Include protocol/domain context if applicable.}

---

## 1. Purpose

{2-3 paragraphs: project purpose, key capabilities, and broader context. What problem does it solve? Who uses it? How does it fit into a larger system (if applicable)?}

Key capabilities:
- {capability 1}
- {capability 2}
- ...

---

## 2. Architecture

### 2.1 Directory Tree

{Annotated tree showing key files with one-line descriptions. Example:}

project/
  src/
    main.rs                    # Entrypoint: parses config, launches server
    server.rs                  # HTTP server: routes, middleware, graceful shutdown
    handlers/
      auth.rs                  # Login, logout, token refresh
      users.rs                 # CRUD operations for user accounts
    db/
      mod.rs                   # Connection pool, migrations
      queries.rs               # SQL query builders
  tests/
    integration/               # API integration tests
  Cargo.toml                   # Workspace config, dependency versions
  Dockerfile                   # Multi-stage build


### 2.2 Key System Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **ComponentName** | `path/to/file.rs` | What it does. Specific methods: `method_a`, `method_b`. Key behaviors. |
| ... | ... | ... |

### 2.3 Data Flow

{ASCII diagram showing how data moves through the system. Example:}

User Request
     |
     v
HTTP Server (server.rs)
     |
     v
Router -> Handler (handlers/)
     |
     v
Service Layer (services/)
     |
     v
Database (db/)


### 2.4 Execution Flow / Lifecycle

{Step-by-step description of the main happy path. Number each step.}

1. **Step name** - What happens, which functions are called
2. **Step name** - Next step in the flow
3. ...

---

## 3. Noteworthy Implementation Choices

{Each choice as a subsection. Explain the WHAT and the WHY.}

### Choice Name
What: {description of the implementation choice}
Why: {reasoning - tradeoffs, constraints, design philosophy}

### Another Choice
...

---

## 4. Key Data Types (if applicable)

{Tables of core types/interfaces. Skip this section for simple projects.}

| Type | File | Description |
|------|------|-------------|
| `TypeName` | `path/to/file` | What it represents, key fields |
| ... | ... | ... |

---

## 5. Test Infrastructure

### Test counts by file

| File/Directory | Tests | Coverage |
|----------------|-------|----------|
| `tests/unit/` | ~50 | Core logic |
| `tests/integration/` | ~20 | API endpoints |
| ... | ... | ... |

### Testing approach

{Frameworks, patterns, test utilities, how to run tests}

---

## 6. Build/Dev Workflow

### Prerequisites

- {tool 1} (version)
- {tool 2} (version)

### Core commands

{Actual commands from the repo's tooling:}

command1   # description
command2   # description


### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV_VAR` | `value` | What it configures |

### CI

{Brief description of CI pipeline}

---

## 7+ Additional Sections (as warranted)

{Include any of these if relevant:}

- **Deployment Targets** - table of environments
- **Branch Strategy** - active branches and their purpose
- **Dependency Highlights** - key deps with version and purpose
- **Key Terminology** - domain-specific glossary
- **Cross-Repo Dependencies** - how this repo relates to others
- **Key Ports/URLs** - service endpoints for development
```

## Quality Standards

1. **Accuracy** - Every file path must exist. Every described behavior must be verifiable in code.
2. **Depth** - Component descriptions include specific method names and behavioral details, not vague summaries.
3. **Structure** - Tables for structured data. ASCII diagrams for flows. Annotated trees for directories.
4. **Completeness** - All major components covered. No significant files omitted.
5. **Honesty** - Uncertain claims flagged with [NEEDS VERIFICATION].
6. **Conciseness** - Every sentence earns its place. No filler prose.
