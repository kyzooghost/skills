#!/bin/bash
set -euo pipefail
# PreToolUse hook - blocks pip/pip3 in favor of uv.
CMD=$(jq -r '.tool_input.command // empty')
[[ -z "$CMD" ]] && exit 0

if echo "$CMD" | grep -qE '^(pip|pip3)\s'; then
  echo "BLOCKED: use uv instead" >&2
  exit 2
fi
exit 0
