---
name: md
description: Use when the user invokes /md or asks to save the previous assistant response to a Markdown file.
---

# Md

Save the previous assistant response as a local Markdown file.

## Invocation

```text
/md
/md my-file.md
```

## Behavior

1. Identify the last assistant response before the user's `/md` request.
2. Write only the text shown to the user. Do not include tool calls, hidden reasoning, system messages, or the `/md` request itself.
3. Preserve the response formatting exactly, including headings, lists, and code fences.
4. Write to `tmp-docs/<filename>` under the current working directory. Create `tmp-docs/` if needed.
5. If the user supplied a filename, use it as the filename. If it has no `.md` suffix, add `.md`.
6. If no filename was supplied, generate a 2-4 word kebab-case filename from the response content.
7. Overwrite any existing file with the same path.
8. After writing, report `Wrote {n} bytes to {filepath}`.
9. Open the file in Chrome:

```bash
open -a "Google Chrome" {filepath}
```

## Errors

- If there is no previous assistant response to save, say: `Error: no previous response to save.`
- If the path is invalid or unwritable, show the filesystem error message.
