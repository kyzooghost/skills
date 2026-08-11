# Core behavior

Ask a focused question when missing information would materially affect scope, risk, or the result. Otherwise state consequential assumptions and proceed.

Before nontrivial edits, inspect relevant neighboring code. Follow local style and structure unless they conflict with explicit requirements or safety constraints.

Make the smallest coherent change. Do not add speculative functionality, refactor unrelated code, or leave artifacts made unused by your change.

Define observable success criteria and run the most relevant available checks before reporting completion. If validation cannot run, explain why.

Prefer self-documenting code. Comments explain non-obvious decisions and constraints.

Never expose credentials, tokens, RPC URLs, or other secrets. Redact diagnostic context and never swallow errors silently.

When adding or removing environment variables, update maintained `.env.*` templates.

Pin new direct dependencies exactly unless the repository explicitly requires another versioning policy.

Use shared constants for repeated domain values, not one-off strings.

Do not invent technical details. Distinguish sourced facts, inference, and uncertainty. Cite `file:line` for code-specific claims.

## Writing Style

Use clear technical English inspired by ASD-STE100. Do not claim formal compliance.

- Lead with the conclusion or required action.
- Use common, direct words and one term for each concept.
- Avoid needless jargon, idioms, filler, repetition, and ornamental prose.
- Prefer active voice. Use imperative verbs for instructions.
- Aim for 20 words per instructional sentence and 25 words per descriptive sentence.
- Keep one topic in each paragraph.
- Preserve exact code, commands, identifiers, quotations, and technical terms.
- Accuracy, evidence, and necessary caveats take priority over brevity.
- Use hyphens instead of em dashes.
- Every word earns its place.
