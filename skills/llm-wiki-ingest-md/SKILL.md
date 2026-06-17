---
name: llm-wiki-ingest-md
description: Combine /llm-wiki ingest and /md into one step. Ingests the last assistant response into the bank-repos-wiki AND writes it to tmp-docs/ as markdown, opened in Chrome. Use when the user says "/llm-wiki-ingest-md", "ingest and /md", "wiki ingest then md", or any combination requesting both wiki ingest and markdown file output in one action.
---

# LLM Wiki Ingest + MD

Perform both operations on the last assistant response in one step:

1. **Wiki ingest** - update `bank-repos-wiki/wiki/commbiz-integration-testing.md` (or appropriate wiki page) with key findings from the response, and append to `bank-repos-wiki/wiki/log.md`
2. **MD export** - write the full response text to `tmp-docs/<auto-named>.md` and open in Chrome

## Workflow

1. Identify the last assistant response (text only, not tool calls)
2. **Wiki ingest:**
   - Read `bank-repos-wiki/wiki/index.md` to find the relevant page
   - Surgically add key findings to the appropriate section (don't rewrite the whole page)
   - Append a log entry to `bank-repos-wiki/wiki/log.md` with format: `## [YYYY-MM-DD] ingest | <brief title>`
3. **MD export:**
   - Generate kebab-case filename from content (2-4 word summary)
   - Write to `tmp-docs/<filename>.md` preserving all formatting
   - Open in Chrome: `open -a "Google Chrome" <filepath>`
4. Report: `Wiki ingested + Wrote {n} bytes to {filepath}`

## Rules

- Wiki directory: `bank-repos-wiki/` in cwd (`/Users/tangj19/Desktop/repos/bank-repos-wiki/`)
- MD directory: `tmp-docs/` in cwd
- Wiki update: surgical addition, not full page rewrite
- Log format: `## [YYYY-MM-DD] ingest | <title>\n- Updated: [page](page.md)\n- Key finding: <one line>`
- Filename: auto-generate from content if no arg provided
- Overwrite: always overwrite md file, never append
- Content: raw text of last response only for md file
- Preserve: all formatting - code blocks, headers, lists, tables
