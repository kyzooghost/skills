# Claude Command: Md

This command writes the last agent response to a local Markdown file.

## Usage

```
/md                  # Auto-generate filename from response summary
/md my-file.md       # Write to tmp-docs/my-file.md
```

## What This Command Does

1. Identifies the last assistant response from the conversation
2. Generates a short summary filename (if not provided)
3. Writes the content to `tmp-docs/<filename>.md`
4. Confirms the file was written with the path and size

## Behavior

- **Directory**: Always write to `tmp-docs/` in the current working directory. Create the directory if it does not exist.
- **Filename**: If no argument provided, generate a kebab-case filename from a 2-4 word summary of the response content (e.g., `api-error-handling.md`, `user-auth-flow.md`). If argument provided, use it as the filename.
- **Overwrite**: Always overwrite if file exists - do not append.
- **Content**: Write the raw text content of the last assistant response before this command was invoked. Do not include tool calls or system messages - only the text shown to the user.
- **Format preservation**: Preserve all formatting - code blocks, headers, lists, etc.

## Output

After writing, display:
```
Wrote {n} bytes to {filepath}
```

## Error Handling

- If no previous assistant response exists: "Error: no previous response to save."
- If path is invalid or unwritable: show the filesystem error message.
