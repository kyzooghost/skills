# Claude Command: Doc Update

This command detects documentation drift caused by code changes in a PR or branch, auto-fixes all drift, and presents changes for user review before committing.

## Usage

```
/doc-update            # Scan all *.md files in repo
/doc-update docs/ README.md  # Scan only specified paths
```

Arguments come via `$ARGUMENTS`. If empty, default to all `*.md` in the repo excluding `.git`, `node_modules`, `dist`, `build`, `.next`, `out`.

## What This Command Does

1. Gets the diff between the current branch and its base (PR base or main/master)
2. Extracts a semantic change manifest from the diff (identifiers, behaviors, structure)
3. Searches target documentation files for references to changed items
4. Reads and analyzes relevant doc sections for drift against the diff
5. Classifies drift by severity: CONTRADICTION (HIGH), MISSING UPDATE (MEDIUM), STALENESS (LOW)
6. Auto-fixes all detected drift in the documentation
7. Presents changes for user review and optionally commits

---

## Phase 1 - Triage

### Step 1: Get the Diff

Determine the base branch and compute the diff:

1. Try `gh pr view --json number,title,body,baseRefName` to check for a PR on current branch
2. If PR exists: use `git diff <baseRefName>...HEAD` and capture the PR title/body for context
3. If no PR (gh fails or no PR found): silently fall back to `git diff main...HEAD`
4. If `main` doesn't exist: try `git diff master...HEAD`
5. If diff is empty: stop with "No changes detected between current branch and base branch."

Note: `gh` is optional. If it is not installed or fails, fall back to git diff silently without warning.

### Step 2: Extract Semantic Change Manifest

Analyze the diff and build a list of:

- **Added/removed/renamed identifiers**: functions, classes, env vars, CLI flags, API endpoints, config keys
- **Behavioral changes**: altered logic, changed defaults, new error states, modified return values
- **Structural changes**: moved files, renamed modules, new dependencies

This manifest drives the doc search in Step 3.

### Step 3: Search Docs for References

Determine target doc files:
- If `$ARGUMENTS` is non-empty: use those paths. Expand directories to find `*.md` files within them.
- If `$ARGUMENTS` is empty: Use the Glob tool with pattern `**/*.md`, then filter out paths containing `.git/`, `node_modules/`, `dist/`, `build/`, `.next/`, or `out/` directory segments.

If no `*.md` files are found: stop with "No documentation files found in the specified paths."

For each item in the change manifest, use Grep to search the target doc files for mentions. Track which doc files and which sections (by heading) reference each changed item. Also flag doc sections that describe areas semantically related to the changes.

Output: a targeted list of `(doc_file, section, changed_item, relevance)` tuples to analyze in Phase 2.

---

## Phase 2 - Analyze & Fix

### Step 4: Read and Analyze Relevant Doc Sections

For each `(doc_file, section)` from Step 3:
1. Read the doc section with surrounding context using the Read tool
   Read from the matched heading to the next heading of equal or higher level. Include a few lines above the heading for context.
2. Compare against the diff changes
3. Classify drift type:
   - **CONTRADICTION** (HIGH): Doc states X, code now does Y
   - **MISSING UPDATE** (MEDIUM): Code added/removed/changed a feature, doc doesn't reflect it
   - **STALENESS** (LOW): Doc section references code areas significantly modified in the PR

If no drift is found across all sections: stop with "All documentation is up to date with current changes."

### Step 5: Print Drift Summary

Print each drift instance inline:

```
## Drift Found: {N} issues

1. CONTRADICTION - {file}:{line}
   Doc says: "{quoted doc text}"
   Code now: {description of code change}
   Severity: HIGH

2. MISSING UPDATE - {file}:{line}
   Code change: {description}
   Doc missing: {what needs to be added/updated}
   Severity: MEDIUM

3. STALENESS - {file}:{line_range}
   Section "{heading}" references {N} items modified in this PR
   Severity: LOW
```

### Step 6: Auto-Fix All Drift

For each drift instance, apply the appropriate fix using the Edit tool:

- **CONTRADICTION**: Edit the doc to match current code behavior
- **MISSING UPDATE**: Add or update documentation for the changed items
- **STALENESS**: Rewrite the stale section to reflect the current code state

After all fixes, print a summary:

```
## Fixes Applied

Modified {N} file(s):
- path/to/doc1.md ({X} changes)
- path/to/doc2.md ({Y} changes)
```

### Step 7: Present for Review

Run `git diff` on the modified doc files to show the user exactly what changed:

```bash
git diff -- {modified_files}
```

Then ask: "Would you like to commit these documentation updates?"

**If user approves:**
1. Stage the modified doc files: `git add {files}`
2. Commit with message: `docs: fix {N} doc drift issues ({list of drift types found})`
   For example: `docs: fix 3 doc drift issues (1 contradiction, 1 missing update, 1 staleness)`
3. Do NOT auto-push

**If user declines:**
1. Leave files modified but unstaged
2. Print: "Changes left in working tree for your review."

## Error Handling

| Condition | Message |
|-----------|---------|
| No diff found (on base branch) | "No changes detected between current branch and base branch." |
| No `*.md` files in scan paths | "No documentation files found in the specified paths." |
| No drift detected | "All documentation is up to date with current changes." |
| `gh` CLI not available | Fall back to `git diff` silently. `gh` is optional. |
| `git diff` fails | "Error: could not compute diff. Ensure you are on a feature branch." |
| `$ARGUMENTS` path does not exist | "Error: path '{path}' does not exist." |

## Ground Rules

- Never commit without explicit user approval
- Never modify non-markdown files
- Never delete doc content without showing what's being removed
- When rewriting sections, preserve the original markdown structure (headings, lists, code blocks)
- Match the existing documentation style and tone in each file
- For ambiguous drift, prefer flagging over aggressive rewriting
