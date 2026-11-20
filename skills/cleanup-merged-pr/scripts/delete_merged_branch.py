#!/usr/bin/env python3
"""Delete a merged branch and its worktree after confirming no work can be lost.

Safety Net blocks direct git deletion commands. This script runs
`git worktree remove --force` and `git branch -D` only after every check passes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


EXIT_FAILED = 1
BRANCH_REF_PREFIX = "refs/heads/"


class Refused(Exception):
    """A safety check failed. Nothing was changed."""


class CommandFailed(Exception):
    """A git or gh command exited non-zero."""


@dataclass(frozen=True)
class Worktree:
    path: Path
    branch: str | None


@dataclass(frozen=True)
class Plan:
    branch: str
    tip: str
    default_branch: str
    main_worktree: Path
    branch_worktree: Worktree | None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete a merged branch and its worktree after confirming no work can be lost.",
    )
    parser.add_argument("--branch", help="Branch to delete. Defaults to the current branch at --repo.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Any path inside the repository. Defaults to the current directory.",
    )
    return parser.parse_args(argv)


def run_unchecked(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a command and return its result. Raise CommandFailed only if it cannot start."""
    try:
        return subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    except OSError as error:
        raise CommandFailed(f"`{' '.join(command)}` could not run: {error}") from error


def run(command: list[str], cwd: Path) -> str:
    result = run_unchecked(command, cwd)
    if result.returncode != 0:
        raise CommandFailed(f"`{' '.join(command)}` failed: {result.stderr.strip()}")
    return result.stdout


def git(cwd: Path, *args: str) -> str:
    return run(["git", "-C", str(cwd), *args], cwd)


def git_succeeds(cwd: Path, *args: str) -> bool:
    return run_unchecked(["git", "-C", str(cwd), *args], cwd).returncode == 0


def gh_json(cwd: Path, *args: str):
    try:
        return json.loads(run(["gh", *args], cwd))
    except json.JSONDecodeError as error:
        raise CommandFailed(f"`gh {' '.join(args)}` returned invalid JSON: {error}") from error


def list_worktrees(repo: Path) -> list[Worktree]:
    worktrees: list[Worktree] = []
    path: Path | None = None
    branch: str | None = None
    for line in git(repo, "worktree", "list", "--porcelain", "-z").split("\0"):
        if line.startswith("worktree "):
            path = Path(line.removeprefix("worktree "))
        elif line.startswith("branch "):
            branch = line.removeprefix("branch ").removeprefix(BRANCH_REF_PREFIX)
        elif not line and path is not None:
            worktrees.append(Worktree(path=path, branch=branch))
            path, branch = None, None
    return worktrees


def current_branch(repo: Path) -> str:
    if not git_succeeds(repo, "symbolic-ref", "--quiet", "HEAD"):
        raise Refused(f"HEAD at {repo} is detached; pass --branch")
    return git(repo, "symbolic-ref", "--short", "HEAD").strip()


def default_branch(main_worktree: Path) -> str:
    return gh_json(main_worktree, "repo", "view", "--json", "defaultBranchRef")["defaultBranchRef"]["name"]


def ensure_commit(main_worktree: Path, oid: str, pr_number: int) -> str | None:
    """Return None if the commit is available locally, otherwise the reason it is not."""
    commit_ref = f"{oid}^{{commit}}"
    if git_succeeds(main_worktree, "cat-file", "-e", commit_ref):
        return None
    # The PR head can hold commits this clone never fetched, such as review suggestions.
    pull_ref = f"refs/pull/{pr_number}/head"
    fetch = run_unchecked(["git", "-C", str(main_worktree), "fetch", "--quiet", "origin", pull_ref], main_worktree)
    if git_succeeds(main_worktree, "cat-file", "-e", commit_ref):
        return None
    return f"could not fetch {pull_ref}: {fetch.stderr.strip() or 'commit not found'}"


def merged_pr_contains(main_worktree: Path, branch: str, tip: str) -> tuple[int | None, list[str]]:
    """Return a merged PR number whose head contains the local tip, plus fetch problems."""
    prs = gh_json(
        main_worktree,
        "pr", "list", "--head", branch, "--state", "merged", "--json", "number,headRefOid",
    )
    problems: list[str] = []
    for pr in prs:
        head = pr["headRefOid"]
        if head == tip:
            return pr["number"], problems
        problem = ensure_commit(main_worktree, head, pr["number"])
        if problem is not None:
            problems.append(problem)
        elif git_succeeds(main_worktree, "merge-base", "--is-ancestor", tip, head):
            return pr["number"], problems
    return None, problems


def check_merged(main_worktree: Path, branch: str, default: str, tip: str) -> None:
    # A squash merge leaves branch commits off the default branch, so a merged PR
    # counts only if its head contains the local tip.
    pr_number, problems = merged_pr_contains(main_worktree, branch, tip)
    if pr_number is not None:
        return
    ahead = int(git(main_worktree, "rev-list", "--count", f"refs/remotes/origin/{default}..{tip}").strip())
    if ahead:
        detail = f" ({'; '.join(problems)})" if problems else ""
        raise Refused(
            f"branch {branch} has {ahead} commit(s) not on origin/{default}, "
            f"and no merged PR head contains its tip {tip[:12]}{detail}"
        )


def build_plan(repo: Path, branch_arg: str | None) -> Plan:
    worktrees = list_worktrees(repo)
    main_worktree = worktrees[0].path
    branch = branch_arg or current_branch(repo)
    default = default_branch(main_worktree)
    if branch == default:
        raise Refused(f"{branch} is the default branch")
    if not git_succeeds(main_worktree, "rev-parse", "--verify", "--quiet", f"{BRANCH_REF_PREFIX}{branch}"):
        raise Refused(f"branch {branch} does not exist locally")
    tip = git(main_worktree, "rev-parse", f"{BRANCH_REF_PREFIX}{branch}").strip()

    checkouts = [worktree for worktree in worktrees if worktree.branch == branch]
    if len(checkouts) > 1:
        paths = ", ".join(str(worktree.path) for worktree in checkouts)
        raise Refused(f"branch {branch} is checked out in {len(checkouts)} worktrees: {paths}")
    check_merged(main_worktree, branch, default, tip)
    return Plan(branch, tip, default, main_worktree, checkouts[0] if checkouts else None)


def execute(plan: Plan) -> str | None:
    """Delete the branch. Return the removed worktree path, if any."""
    current_tip = git(plan.main_worktree, "rev-parse", f"{BRANCH_REF_PREFIX}{plan.branch}").strip()
    if current_tip != plan.tip:
        raise Refused(f"branch {plan.branch} moved from {plan.tip[:12]} to {current_tip[:12]} during the checks")
    removed: str | None = None
    if plan.branch_worktree is not None:
        if plan.branch_worktree.path == plan.main_worktree:
            git(plan.main_worktree, "switch", plan.default_branch)
        else:
            git(plan.main_worktree, "worktree", "remove", "--force", str(plan.branch_worktree.path))
            removed = str(plan.branch_worktree.path)
    git(plan.main_worktree, "branch", "-D", plan.branch)
    return removed


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        plan = build_plan(args.repo.resolve(), args.branch)
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_FAILED
    except CommandFailed as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_FAILED
    try:
        removed = execute(plan)
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_FAILED
    except CommandFailed as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_FAILED
    print(f"deleted branch: {plan.branch}")
    print(f"removed worktree: {removed or 'none'}")
    print(f"main worktree: {plan.main_worktree}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
