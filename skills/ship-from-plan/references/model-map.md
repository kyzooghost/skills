# Model Map

Resolve the user's required friendly model inputs against the active agent environment. The map controls dispatch configuration only; it never chooses a default model.

## Resolution rules

1. Detect the active environment from runtime tools and agent capabilities. Do not infer it only from home directories because Cursor, Claude, and Codex configuration can coexist.
2. Match the complete friendly name, including its reasoning level.
3. Confirm the resolved model is available to the active subagent dispatch tool before Stage 1.
4. If the friendly name is unmapped or unavailable, show the active environment and its available model identifiers, then ask the user to select another model.
5. Never downgrade, upgrade, or silently substitute a selected model.
6. Cursor uses one slug field. Codex uses separate `model` and `reasoning_effort` fields.

## Cursor mappings

- `Grok 4.7` -> slug `cursor-grok-4.7-high`

## Codex mappings

- `Luna xHigh` -> model `gpt-6-luna`, reasoning effort `xhigh`

## Dispatch contract

- Every implementer dispatch uses the resolved `IMPLEMENTOR_MODEL` configuration.
- Every task reviewer, final reviewer, and differential-review subagent uses the resolved `REVIEWER_MODEL` configuration.
- More context, task decomposition, and same-model redispatch are allowed.
- Any model change requires new human input.
