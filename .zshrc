approve() {
    gh pr review $1 --approve
}

git config --global push.autoSetupRemote true

alias k=kubectl
alias v=vim
alias c="claude --dangerously-skip-permissions"
alias co="codex -a never -s workspace-write"

rep() {
  cd ~/Desktop/repos
}

set-claude() {
    code ~/.claude
}

set-zshrc() {
    code ~/.zshrc
}

grid4() {
  local name="${1:-grid}"

  tmux new-session -d -s "$name" \; \
    split-window -h \; \
    select-pane -t 0 \; split-window -v \; \
    select-pane -t 1 \; split-window -v \; \
    select-layout tiled \; \
    attach

gpp() {
    git pull --prune
}

gclean() {
    git reset --hard && git clean -fd
}

gs() {
    git status
}

gb() {
    git branch
}

gp() {
    git push
}

gnew() {
    git checkout -b "$1"
}

# Create new worktree with a fresh branch
gwa() {
  if [ -z "$1" ]; then
    echo "Usage: gwa <branch-name>"
    return 1
  fi

  local branch="$1"
  local repo
  repo="$(basename "$PWD")"
  local wt_path="../${repo}--${branch}"

  echo "Creating worktree at: $wt_path"
  git worktree add -b "$branch" "$wt_path" || return 1
  cd "$wt_path"
}

# Create new worktree based on a remote branch
gwar() {
  if [ -z "$1" ]; then
    echo "Usage: gwar <remote-branch>"
    return 1
  fi

  local branch="$1"
  local repo
  repo="$(basename "$PWD")"

  local n=1
  local wt_path

  while true; do
    wt_path="../${repo}-pr${n}"
    if [ ! -e "$wt_path" ]; then
      break
    fi
    n=$((n + 1))
  done

  echo "Creating worktree at: $wt_path"
  git worktree add -b "$branch" "$wt_path" "origin/$branch" || return 1
  cd "$wt_path"
}

# Delete git worktree
gwipe() {
  local wt_path="$1"

  if [[ -z "$wt_path" ]]; then
    echo "Usage: gwipe <worktree-path>"
    return 1
  fi

  if [[ ! -d "$wt_path" ]]; then
    echo "Error: '$wt_path' is not a directory"
    return 1
  fi

  # Get branch associated with worktree
  local branch
  branch=$(git -C "$wt_path" symbolic-ref --short HEAD 2>/dev/null)

  if [[ -z "$branch" ]]; then
    echo "Warning: could not determine branch for worktree at $wt_path"
  fi

  echo "Removing worktree: $wt_path"
  git worktree remove "$wt_path" --force || return 1

  echo "Deleting folder: $wt_path"
  rm -rf "$wt_path"

  if [[ -n "$branch" ]]; then
    echo "Deleting branch: $branch"
    git branch -D "$branch"
  fi

  echo "✅ Done"
}

# Delete current worktree and cd back to main repo
gwipehere() {
  local wt_path
  wt_path="$(pwd)"

  local main_path
  main_path=$(git worktree list --porcelain | head -1 | sed 's/^worktree //')

  if [[ "$wt_path" == "$main_path" ]]; then
    echo "Error: already in the main worktree"
    return 1
  fi

  local branch
  branch=$(git symbolic-ref --short HEAD 2>/dev/null)

  cd "$main_path" || return 1

  echo "Removing worktree: $wt_path"
  git worktree remove "$wt_path" --force || return 1

  if [[ -d "$wt_path" ]]; then
    echo "Deleting folder: $wt_path"
    command rm -rf "$wt_path"
  fi

  if [[ -n "$branch" ]]; then
    echo "Deleting branch: $branch"
    git branch -D "$branch"
  fi

  echo "Done. Back in: $(pwd)"
}

incognito() {
    HISTFILE=/dev/null
    unset HISTFILE
    HISTSIZE=0
    HISTFILESIZE=0
}

# Custom bash function to switch to 'main' branch in git, and delete the branch we just switched from.
function delswitch() {
    # Get current branch name
    local current_branch=$(git symbolic-ref --short HEAD)

    # If we're already on main, inform the user and exit
    if [ "$current_branch" = "main" ]; then
        echo "Already on main branch."
        return 0
    fi

    git checkout main
    git branch -D "$current_branch"
    git pull --prune
}
