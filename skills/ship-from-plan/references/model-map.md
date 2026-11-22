# Model Map

Resolve the user's required friendly model inputs against the active agent environment. The map controls dispatch configuration only; it never chooses a default model.

## Resolution rules

1. Detect the active environment from runtime tools and agent capabilities. Do not infer it only from home directories because Cursor, Claude, and Codex configuration can coexist.
2. Match the complete friendly name, including its reasoning level.
3. Confirm the resolved model is available to the active subagent dispatch tool before Stage 1.
4. If the friendly name is unmapped or unavailable, show the active environment and its available model identifiers, then ask the user to select another model.
5. Never downgrade, upgrade, or silently substitute a selected model.
6. Cursor uses one slug field. Codex uses separate `model` and `reasoning_effort` fields.

## Claude Code mappings

Claude Code dispatches through the Agent tool: `model` takes an alias and `effort` takes a level. Alias versions are confirmed by the user, not detected. Do not dispatch with `subagent_type: "fork"`, because a fork ignores `model` and `effort` and runs on the parent's model.

- `Sonnet 5.5 medium` -> Agent `model` `sonnet`, `effort` `medium`
- `Sonnet 5.5 high` -> Agent `model` `sonnet`, `effort` `high`
- `Opus 5.5 high` -> Agent `model` `opus`, `effort` `high`
- `Fable 5.2 high` -> Agent `model` `fable`, `effort` `high`

## Cursor mappings

- `Grok 4.7` -> slug `cursor-grok-4.7-high`

## Codex mappings

- `Luna xHigh` -> model `gpt-6-luna`, reasoning effort `xhigh`

## Dispatch contract

- Every implementer dispatch uses the resolved `IMPLEMENTOR_MODEL` configuration.
- Every task reviewer, final whole-branch reviewer, and post-`/create-pr` reviewer uses the resolved `REVIEWER_MODEL` configuration.
- The differential-review subagent uses the resolved `DIFF_REVIEWER_MODEL` configuration.
- More context, task decomposition, and same-model redispatch are allowed.
- Any model change requires new human input.
