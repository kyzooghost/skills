#!/bin/bash
set -euo pipefail
# PreToolUse hook — blocks grep in Bash commands, use rg (ripgrep) instead.
CMD=$(jq -r '.tool_input.command // empty')
[[ -z "$CMD" ]] && exit 0

if echo "$CMD" | grep -qE '(^|[|;&])[[:space:]]*grep([[:space:]]|$)'; then
  echo "BLOCKED: Use rg (ripgrep) instead of grep" >&2
  exit 2
fi
exit 0
