# Design: Commit Lint Step

## Problem

The `/commit` command does not check linting before committing. We want linting to run as part of the command flow (not as a git hook) so the command stays portable across Claude Code and Cursor.

## Design

Add a new step 6 to `commands/commit.md` "What This Command Does" (current step 6 becomes step 7).

### New Step 6: Lint before committing

For each distinct logical change identified in step 4:

1. **Find project root** - walk up from changed files to find the nearest `package.json` (TS/JS) or `build.gradle`/`build.gradle.kts` (Gradle). Deduplicate so each project is linted once.
2. **TS/JS** - read the nearest `package.json` scripts. Run `lint:fix` if it exists, otherwise `lint`. Skip if neither exists.
3. **Gradle** - check `build.gradle`/`build.gradle.kts` for lint-related tasks. Run the matching task via `./gradlew <task>`.
4. **Re-stage** - if linting auto-fixes files, re-stage them with `git add`.
5. **No lint command found** - skip silently.

### Decisions

- **Auto-fix on failure**: run the fix variant, re-stage, continue.
- **Project scoping**: walk up directories to find nearest project file (handles monorepos).
- **Script discovery**: look for `lint:fix` first, fall back to `lint` in package.json scripts.
- **No hooks**: all logic lives in the command definition for Cursor portability.
