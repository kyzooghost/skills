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

- `Grok 4.5 High` -> slug `cursor-grok-4.5-high`
- `GLM 5.2` -> slug `glm-5.2-high`
- `Claude Sonnet 5` -> slug `claude-sonnet-5-thinking-high`
- `Claude Opus 4.8` -> slug `claude-opus-4-8-thinking-high`
- `Composer 2.5 Fast` -> slug `composer-2.5-fast`
- `GPT 5.4 Medium` -> slug `gpt-5.4-medium`
- `GPT 5.6 SOL High` -> slug `gpt-5.6-sol-high`
- `GPT 5.6 Terra Medium` -> slug `gpt-5.6-terra-medium`

## Codex mappings

- `GPT 5.6 SOL High` -> model `gpt-5.6-sol`, reasoning effort `high`
- `GPT 5.6 Terra Medium` -> model `gpt-5.6-terra`, reasoning effort `medium`

## Dispatch contract

- Every implementer dispatch uses the resolved `IMPLEMENTOR_MODEL` configuration.
- Every task reviewer, final reviewer, and differential-review subagent uses the resolved `REVIEWER_MODEL` configuration.
- More context, task decomposition, and same-model redispatch are allowed.
- Any model change requires new human input.
