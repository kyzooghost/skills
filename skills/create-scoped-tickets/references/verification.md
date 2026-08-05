# Verification

Maintainer-facing checks for the create-scoped-tickets skill. Run the static checks from the repository root after editing SKILL.md; use the scenario exercises to test behavior end to end.

## Contents

- Static checks (bash script asserting SKILL.md structure and required commands)
- Scenario exercises (10 behavioral scenarios)

## Static checks

```bash
set -euo pipefail

skill_md=skills/create-scoped-tickets/SKILL.md

# SKILL.md body stays under the 500-line budget
line_count="$(wc -l < "$skill_md" | tr -d ' ')"
if [ "$line_count" -ge 500 ]; then
  printf 'SKILL.md is %s lines; must be under 500.\n' "$line_count"
  exit 1
fi
echo "SKILL.md is $line_count lines."

# No em-dash (per workspace rule) in the skill or its reference files
if rg -n $'\xE2\x80\x94' "$skill_md" skills/create-scoped-tickets/references/; then
  exit 1
else
  echo 'No em-dash found.'
fi
# Expected: no rg matches

# No lingering references to the removed workflows
if rg -n 'Workflow B|Workflow C|sync_pr_status_comments|PR review scoped|status comments' "$skill_md"; then
  exit 1
fi
# Expected: no output

# gh commands used in their respective workflow phases
phase_0_text="$(awk '/^### Phase 0 - Universe inventory$/{found=1} found && /^### Phase 1 - Spec decomposition$/{exit} found {print}' "$skill_md")"
if ! printf '%s\n' "$phase_0_text" | rg -F -x '     gh issue list -R <REPO> --label "$label" --state open --limit 200 --json number,title,body,labels' >/dev/null; then
  echo 'Missing the exact gh issue list command in Phase 0.'
  exit 1
fi
phase_5_text="$(awk '/^### Phase 5 - File approved NEW drafts$/{found=1} found && /^## Author checklist/{exit} found {print}' "$skill_md")"
expected_phase_5_command="$(printf '%s\n' \
  "gh issue create \\" \
  "  -R <REPO> \\" \
  "  --title \"<Title>\" \\" \
  "  --body \"<full Agent Work Ticket body>\" \\" \
  "  --label \"<label1>\" --label \"<label2>\" ...")"
actual_phase_5_command="$(printf '%s\n' "$phase_5_text" | awk '/^gh issue create \\$/{capture=1} capture {print} /^  --label .*\.\.\.$/{exit}')"
if [ "$actual_phase_5_command" != "$expected_phase_5_command" ]; then
  echo 'Missing the exact gh issue create command in Phase 5.'
  exit 1
fi
echo 'Phase 0 and Phase 5 contain their required GitHub commands.'

# Onboarding sections, reference links, and Skill-tool invocation are present
required_onboarding_patterns=(
  '^## Fits into the workflow$'
  '^## Requirements$'
  '^## Glossary$'
  'repository-local schema'
  '\$create-scoped-tickets'
  'references/worked-example\.md'
  'references/verification\.md'
)
for pattern in "${required_onboarding_patterns[@]}"; do
  if ! rg -n "$pattern" "$skill_md" >/dev/null; then
    printf 'Missing onboarding content: %s\n' "$pattern"
    exit 1
  fi
done
echo 'All onboarding content is present.'

# Reference files exist one level deep with their expected headings
if ! rg -q -F -x '# Worked example - Seed mode' skills/create-scoped-tickets/references/worked-example.md; then
  echo 'references/worked-example.md is missing or lacks its heading.'
  exit 1
fi
echo 'Reference files are in place.'

# The old slash-command form is absent; the regex is intentionally non-literal
if rg -n '^[[:space:]]*/create-[[:lower:]-]+' "$skill_md"; then
  exit 1
else
  echo 'No slash-command invocation remains.'
fi
# Expected: no rg matches

# Every core heading appears exactly once
required_headings=(
  '## Inputs'
  '## Built-in defaults (never restated by the user)'
  '## Workflow'
  '### Phase 0 - Universe inventory'
  '### Phase 1 - Spec decomposition'
  '### Phase 2 - Overlap classification (Append mode only)'
  '### Phase 3 - Draft tickets'
  '### Phase 4 - Present drafts for batch approval'
  '### Phase 5 - File approved NEW drafts'
  '## Author checklist (per drafted ticket, before Phase 4)'
  '## Error handling and edge cases'
  '## Invocation'
  '## Verification'
)
for heading in "${required_headings[@]}"; do
  match_count="$(rg -F -x "$heading" "$skill_md" | wc -l | tr -d ' ' || true)"
  if [ "$match_count" -ne 1 ]; then
    printf 'Expected exactly one heading: %s (found %s)\n' "$heading" "$match_count"
    exit 1
  fi
done
echo 'All core sections appear exactly once.'
```

## Scenario exercises

1. **Seed, empty universe** - `LABELS=topic1`, zero open tickets. Spec has 4 atomic units. Output: 4 NEW drafts in dependency order, batch approval, 4 `gh issue create` calls, receipt with 4 issue numbers.
2. **Append, all NEW** - `LABELS=topic1,topic2`, existing tickets under `topic1` cover an adjacent area not in the spec. All 3 spec candidates are NEW. Output: 3 NEW drafts with "The owner must not" citing existing ticket numbers.
3. **Append, all AMEND** - The spec's units all overlap existing tickets. Output: amendment proposals only; nothing to file in Phase 5; explicit "fully covered" message.
4. **Append, PARTIAL split** - One candidate overlaps existing ticket #N. Output: one AMEND proposal for #N plus one NEW draft whose "The owner must not" cites #N.
5. **Overlap between two NEW candidates** - Phase 3 detects two drafts touching the same area. Output: merged or resplit before Phase 4; no overlap survives to approval.
6. **Existing ticket with non-standard scope headings** - Ticket #M uses only "Description". Output: stop, ask user for #M's owned/excluded scope.
7. **User approves subset** - User approves drafts A, C; holds B. Output: file A and C; B held in receipt.
8. **Filing failure mid-batch** - `gh issue create` errors on draft B after A filed. Output: stop; report A filed, B failed, C not attempted.
9. **SCOPE_HINT narrows the run** - Hint restricts decomposition to §4. Output: only §4 units become candidates; §3 spec content appears under "Uncovered spec sections" for user confirmation.
10. **Two existing tickets appear to own the same area** - Phase 0 detects the conflict. Output: stop, ask user to resolve before decomposition.
