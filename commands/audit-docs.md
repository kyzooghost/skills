# Claude Command: Audit Docs

Static, read-only audit of all Markdown files in the repo for internal contradictions, conflicts, and semantic drift. No inputs - scans the entire repo as a snapshot.

## Usage

```
/audit-docs
```

No arguments. Scans all `*.md` files in the repo.

---

## Phase 1 - Collect

### Step 1: Discover Markdown Files

1. Use Glob with pattern `**/*.md` from the repo root.
2. Filter out paths containing any of: `.git/`, `node_modules/`, `dist/`, `build/`, `.next/`, `out/`, `.claude/worktrees/`.
3. If no files found: stop with "No Markdown files found in this repository."
4. Read ALL matched files using the Read tool. Do not skip any.
5. If more than 200 files: batch into groups of 50, maintain a running index of terms, claims, and cross-references across batches, and warn the user ("Large corpus ({N} files) - this may take a while.").

---

## Phase 2 - Analyze

### Step 2: Run All 7 Checks

For each check below, cross-reference ALL collected files against each other. Do not limit comparison to files in the same directory - a contradiction between `README.md` and `docs/advanced/deployment.md` is just as important as one between sibling files.

#### Check 1: Terminology conflicts (HIGH)

Find terms, acronyms, or concepts that are defined or used with different meanings across files. Look for:
- Explicit definitions that contradict ("X means Y" in one file, "X means Z" in another)
- Implicit usage where the same word clearly refers to different things
- Acronyms expanded differently

#### Check 2: Protocol contradictions (HIGH)

Find cases where one doc requires a behavior that another doc forbids or contradicts. Look for:
- Process instructions that conflict ("always do X" vs "never do X")
- Mutually exclusive recommendations
- Conditional rules whose conditions overlap but actions differ

#### Check 3: Lifecycle mismatches (HIGH)

Find processes, workflows, or sequences described differently across files. Look for:
- Different step counts for the same process
- Steps in different order
- Steps present in one description but missing from another
- Different entry/exit conditions for the same phase

#### Check 4: Permission inconsistencies (HIGH)

Find access rules, roles, or capabilities stated differently across files. Look for:
- Role X can do action Y in one file but cannot in another
- Different sets of roles listed for the same capability
- Privilege escalation paths that contradict security docs

#### Check 5: Completion criteria inconsistencies (MEDIUM)

Find success, done, ready, or acceptance conditions that differ across files. Look for:
- Different definitions of "done" or "ready" for the same deliverable
- Checklists that don't match for the same process
- Quality gates described with different thresholds

#### Check 6: Enumerated value mismatches (MEDIUM)

Find lists, enums, status sets, or option sets that don't match across files. Look for:
- A set of values listed in one file that has additions, removals, or renames compared to another file listing the same set
- Tables with different column sets for the same entity
- Configuration options documented inconsistently

#### Check 7: Stale cross-references (LOW)

Find internal links and references that are broken. Check:
- Markdown links to other repo files: `[text](path/to/file.md)` - verify the file exists using Glob
- Markdown links with anchors: `[text](path/to/file.md#heading)` - verify the file exists AND the heading exists in that file
- Relative path references in prose (e.g., "see `docs/deploy.md`") - verify the file exists
- Do NOT check external URLs (http/https links) - that is out of scope

---

## Phase 3 - Report to stdout

### Step 3: Print Results

Sort all findings by severity: HIGH first, then MEDIUM, then LOW. Within the same severity, group by category.

Use this format:

```
## Audit Results: {N} issues found across {M} files

### [HIGH] {Category}: {brief title}
- **Location A:** {file}:{line} - "{quoted text or description}"
- **Location B:** {file}:{line} - "{quoted text or description}"
- **Suggested fix:** {actionable recommendation}

### [MEDIUM] {Category}: {brief title}
- **Location A:** {file}:{line} - "{quoted text or description}"
- **Location B:** {file}:{line} - "{quoted text or description}"
- **Suggested fix:** {actionable recommendation}

### [LOW] Stale cross-reference: {brief title}
- **Location:** {file}:{line} - links to `{target}`
- **Problem:** {what's wrong - file missing, heading missing, closest match}
- **Suggested fix:** {specific fix}
```

After all findings, print an `[OK]` entry for each category that had zero findings:

```
### [OK] {Category}
- Checked {N} references across {M} files, all consistent.
```

If NO issues found across ALL categories: print "All documentation is consistent. No issues found across {N} files."

When uncertain whether something is a true conflict or just different phrasing, still include it but add: `[UNCERTAIN] May be stylistic rather than substantive.`

---

## Phase 4 - Offer Report

### Step 4: Offer Markdown Report

After printing results to stdout, ask: "Would you like me to save this as a Markdown report?"

**If user approves:**
1. Write the full stdout output to `docs/audit-report-YYYY-MM-DD.md` (use today's date)
2. Do NOT commit. Do NOT stage. Leave in working tree.
3. Print: "Report saved to docs/audit-report-YYYY-MM-DD.md"

**If user declines:**
1. Do nothing. The stdout output is sufficient.

---

## Ground Rules

- **Read-only.** Never modify any file during the audit. This command only reports.
- **Always include `file:line`.** No vague references like "somewhere in docs/api.md". Every finding must have a line number.
- **Report [OK] for clean categories.** The user should see that all 7 checks were performed, even if some found nothing.
- **No auto-fix.** Unlike /doc-update, contradictions between docs require human judgment about which doc is correct.
- **No external links.** Only check internal cross-references between repo Markdown files.
- **No linting.** Don't flag grammar, formatting, or Markdown syntax issues.

## Error Handling

| Condition | Message |
|-----------|---------|
| No `*.md` files found | "No Markdown files found in this repository." |
| No issues detected | "All documentation is consistent. No issues found across {N} files." |
| Corpus > 200 files | Warn user, then proceed with batched processing |
