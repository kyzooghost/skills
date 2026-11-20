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


def run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise CommandFailed(f"`{' '.join(command)}` failed: {result.stderr.strip()}")
    return result.stdout


def git(cwd: Path, *args: str) -> str:
    return run(["git", "-C", str(cwd), *args], cwd)


def git_succeeds(cwd: Path, *args: str) -> bool:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    return result.returncode == 0


def list_worktrees(repo: Path) -> list[Worktree]:
    worktrees: list[Worktree] = []
    path: Path | None = None
    branch: str | None = None
    for line in git(repo, "worktree", "list", "--porcelain").splitlines() + [""]:
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
    output = run(["gh", "repo", "view", "--json", "defaultBranchRef"], main_worktree)
    return json.loads(output)["defaultBranchRef"]["name"]


def ensure_commit(main_worktree: Path, oid: str, pr_number: int) -> bool:
    if git_succeeds(main_worktree, "cat-file", "-e", f"{oid}^{{commit}}"):
        return True
    # The PR head can hold commits this clone never fetched, such as review suggestions.
    git_succeeds(main_worktree, "fetch", "--quiet", "origin", f"refs/pull/{pr_number}/head")
    return git_succeeds(main_worktree, "cat-file", "-e", f"{oid}^{{commit}}")


def merged_pr_contains(main_worktree: Path, branch: str, tip: str) -> int | None:
    """Return the number of a merged PR whose head contains the local tip."""
    output = run(
        ["gh", "pr", "list", "--head", branch, "--state", "merged", "--json", "number,headRefOid"],
        main_worktree,
    )
    for pr in json.loads(output):
        head = pr["headRefOid"]
        if head == tip:
            return pr["number"]
        if ensure_commit(main_worktree, head, pr["number"]) and git_succeeds(
            main_worktree, "merge-base", "--is-ancestor", tip, head
        ):
            return pr["number"]
    return None


def check_merged(main_worktree: Path, branch: str, default: str, tip: str) -> None:
    # A squash merge leaves branch commits off the default branch, so a merged PR
    # counts only if its head contains the local tip.
    if merged_pr_contains(main_worktree, branch, tip) is not None:
        return
    ahead = int(git(main_worktree, "rev-list", "--count", f"refs/remotes/origin/{default}..{tip}").strip())
    if ahead:
        raise Refused(
            f"branch {branch} has {ahead} commit(s) not on origin/{default}, "
            f"and no merged PR head contains its tip {tip[:12]}"
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

    branch_worktree = next((worktree for worktree in worktrees if worktree.branch == branch), None)
    check_merged(main_worktree, branch, default, tip)
    return Plan(branch, default, main_worktree, branch_worktree)


def execute(plan: Plan) -> str | None:
    """Delete the branch. Return the removed worktree path, if any."""
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
    except CommandFailed as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_FAILED
    print(f"deleted branch: {plan.branch}")
    print(f"removed worktree: {removed or 'none'}")
    print(f"main worktree: {plan.main_worktree}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
