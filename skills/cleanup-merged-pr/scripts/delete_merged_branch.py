#!/usr/bin/env python3
"""Delete a merged branch and its worktree after confirming no work can be lost.

Safety Net blocks direct git deletion commands. This script runs
`git worktree remove --force` and `git branch -D` only after every check passes.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


EXIT_FAILED = 1
BRANCH_REF_PREFIX = "refs/heads/"
# Matches the sensitive-path list in commands/create-pr.md.
SENSITIVE_NAME_PATTERNS = (".env*", "*.pem", "*.key", "*.p12", "id_rsa*")
SENSITIVE_NAME_WORDS = ("credential", "secret")
ENV_TEMPLATE_NAMES = frozenset({".env.example", ".env.sample", ".env.template"})
# Package-manager output is regenerable, and its file names often look sensitive.
PACKAGE_DIRECTORY_NAMES = ("node_modules", "site-packages")
GITLINK_MODE = "160000"
MAX_LISTED_PATHS = 10


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
    ignored_paths: tuple[str, ...]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete a merged branch and its worktree after confirming no work can be lost.",
    )
    parser.add_argument("--branch", help="Branch to delete. Defaults to the current branch at --repo.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Any path inside the repository. Defaults to the current directory.",
    )
    return parser.parse_args(argv)


def current_directory() -> Path:
    try:
        return Path.cwd()
    except FileNotFoundError as error:
        # Likely right after this script removed the worktree the shell was in.
        raise CommandFailed("current directory no longer exists; pass --repo") from error


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


def gh_json(cwd: Path, *args: str) -> Any:
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


def check_clean(worktree: Path) -> None:
    status = git(worktree, "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none")
    if status.strip():
        raise Refused(f"worktree {worktree} has uncommitted changes:\n{status.rstrip()}")


def modules_git_dirs(worktree: Path) -> dict[Path, str]:
    """Map git directories under the worktree's modules directory, nested and deinitialized ones included, to names."""
    root = Path(git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "modules").strip())
    if not root.is_dir():
        return {}
    git_dirs: dict[Path, str] = {}
    for directory, subdirectories, files in os.walk(root):
        if "HEAD" in files and "objects" in subdirectories:
            name = Path(directory).relative_to(root).as_posix().replace("/modules/", "/")
            git_dirs[Path(directory).resolve()] = name
            # Nested submodules live in <git dir>/modules. Skip the rest of the git dir.
            subdirectories[:] = [child for child in subdirectories if child == "modules"]
    return git_dirs


def checked_out_git_dirs(worktree: Path) -> dict[Path, str]:
    """Map git directories of checked-out submodules to names. Includes embedded `.git` directories."""
    listing = git(
        worktree, "submodule", "foreach", "--quiet", "--recursive",
        'printf "%s\\0%s\\0" "$displaypath" "$(git rev-parse --absolute-git-dir)"',
    )
    fields = listing.split("\0")
    return {Path(git_dir).resolve(): name for name, git_dir in zip(fields[0::2], fields[1::2])}


def submodule_git_dirs(worktree: Path, checked_out: dict[Path, str]) -> dict[Path, str]:
    git_dirs = dict(checked_out)
    for git_dir, name in modules_git_dirs(worktree).items():
        git_dirs.setdefault(git_dir, name)
    return git_dirs


def check_git_dir_pushed(git_dir: Path, label: str, cwd: Path) -> None:
    """Refuse if the git directory has a stash or commits that are on no remote."""
    # Removal deletes the git directory. `--all` minus tags covers every local branch, the stash,
    # and the HEAD of every worktree of that git directory. Tags count as safe, both as tips and as
    # places a commit can be reached from, because fetched release tags often point at commits that
    # no remote branch contains. A local-only tag is an accepted gap.
    git_dir_option = f"--git-dir={git_dir}"
    stash = run_unchecked(["git", git_dir_option, "rev-parse", "--verify", "--quiet", "refs/stash"], cwd)
    if stash.returncode == 0:
        raise Refused(f"{label} has a stash")
    unpushed = run(["git", git_dir_option, "rev-list", "--exclude=refs/tags/*", "--all", "--not", "--remotes", "--tags"], cwd)
    if unpushed.strip():
        raise Refused(f"{label} has commits that are on no remote")


def gitlink_paths(worktree: Path) -> list[str]:
    records = git(worktree, "ls-files", "--stage", "-z").split("\0")
    return [record.split("\t", 1)[1] for record in records if record.startswith(f"{GITLINK_MODE} ")]


def check_uninitialized_submodule_paths(directory: Path, prefix: str) -> None:
    # Status and `submodule foreach` ignore a submodule path without a checkout, yet removal deletes its files.
    for path in gitlink_paths(directory):
        submodule = directory / path
        if submodule.is_dir() and not (submodule / ".git").exists() and any(submodule.iterdir()):
            raise Refused(f"submodule path {prefix}{path} is not initialized but contains files")


def check_submodules(directory: Path, prefix: str, checked_out: dict[Path, str]) -> None:
    check_uninitialized_submodule_paths(directory, prefix)
    # Removal also deletes the git directories of deinitialized submodules.
    for git_dir, name in submodule_git_dirs(directory, checked_out).items():
        check_git_dir_pushed(git_dir, f"submodule {prefix}{name}", directory)


def is_package_path(path: str) -> bool:
    return any(part in PACKAGE_DIRECTORY_NAMES for part in PurePosixPath(path).parts)


def is_sensitive(path: str) -> bool:
    if is_package_path(path):
        return False
    name = PurePosixPath(path).name.lower()
    if name in ENV_TEMPLATE_NAMES:
        return False
    if any(word in name for word in SENSITIVE_NAME_WORDS):
        return True
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in SENSITIVE_NAME_PATTERNS)


def list_ignored(directory: Path) -> list[str]:
    # No --directory: a sensitive file inside an ignored directory must still be listed.
    # A nested repository is the exception: git lists it as one entry that ends in "/".
    output = git(directory, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")
    return [path for path in output.split("\0") if path]


def git_common_dir(directory: Path) -> Path:
    return Path(git(directory, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).resolve()


def check_nested_repository(directory: Path, display_path: str, superproject_common_dir: Path) -> None:
    """Refuse if removal would lose work in a repository that sits inside an ignored directory."""
    probe = run_unchecked(["git", "-C", str(directory), "rev-parse", "--absolute-git-dir"], directory)
    if probe.returncode != 0:
        raise Refused(f"cannot inspect ignored directory {display_path}")
    # Deleting a worktree of this repository leaves its metadata prunable and its branch checked out.
    # `rev-list --all` over the shared refs would also report a misleading "commits on no remote".
    if git_common_dir(directory) == superproject_common_dir:
        raise Refused(
            f"nested worktree {display_path} belongs to this repository; remove it first with git worktree remove"
        )
    check_clean(directory)
    check_git_dir_pushed(Path(probe.stdout.strip()), f"nested repository {display_path}", directory)


def inspect_ignored(directory: Path, prefix: str, superproject_common_dir: Path) -> list[str]:
    """List ignored paths under `directory`. A nested repository is one entry that ends in "/"."""
    paths: list[str] = []
    for entry in list_ignored(directory):
        paths.append(prefix + entry)
        if entry.endswith("/"):
            nested = directory / entry
            check_nested_repository(nested, prefix + entry.rstrip("/"), superproject_common_dir)
            paths.extend(inspect_tree(nested, prefix + entry, superproject_common_dir))
    return paths


def inspect_tree(directory: Path, prefix: str, superproject_common_dir: Path) -> list[str]:
    """Check submodules and nested repositories under `directory`. Return its ignored paths, prefixed."""
    checked_out = checked_out_git_dirs(directory)
    check_submodules(directory, prefix, checked_out)
    paths = inspect_ignored(directory, prefix, superproject_common_dir)
    # `ls-files` does not descend into submodules, but removal deletes their files too.
    for name in checked_out.values():
        submodule = directory / name
        submodule_prefix = f"{prefix}{name}/"
        check_uninitialized_submodule_paths(submodule, submodule_prefix)
        paths.extend(inspect_ignored(submodule, submodule_prefix, superproject_common_dir))
    return paths


def top_level_path(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] + "/" if len(parts) > 1 or path.endswith("/") else parts[0]


def format_paths(paths: list[str]) -> str:
    shown = ", ".join(paths[:MAX_LISTED_PATHS])
    hidden = len(paths) - MAX_LISTED_PATHS
    return f"{shown} and {hidden} more" if hidden > 0 else shown


def inspect_worktree(worktree: Path) -> tuple[str, ...]:
    """Refuse if removing the linked worktree would lose work or secrets. Return the regenerable ignored paths.

    Checks submodule stashes and unpushed commits, uninitialized submodule paths, nested
    repositories (including worktrees of this repository), and sensitive ignored files.
    The returned ignored paths are collapsed to top level.
    """
    paths = inspect_tree(worktree, "", git_common_dir(worktree))
    sensitive = sorted(path for path in paths if not path.endswith("/") and is_sensitive(path))
    if sensitive:
        raise Refused(f"worktree {worktree} has ignored files that may hold secrets: {format_paths(sensitive)}")
    return tuple(sorted({top_level_path(path) for path in paths}))


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
    branch_worktree = checkouts[0] if checkouts else None
    ignored_paths: tuple[str, ...] = ()
    if branch_worktree is not None:
        check_clean(branch_worktree.path)
        # `git switch` in the main checkout keeps its submodule git directories and ignored files.
        # Removal of a linked worktree deletes them, so inspect_worktree must pass first.
        if branch_worktree.path != main_worktree:
            ignored_paths = inspect_worktree(branch_worktree.path)
    check_merged(main_worktree, branch, default, tip)
    return Plan(branch, tip, default, main_worktree, branch_worktree, ignored_paths)


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
    try:
        git(plan.main_worktree, "branch", "-D", plan.branch)
    except CommandFailed as error:
        if removed is None:
            raise
        raise CommandFailed(f"{error} (worktree {removed} was already removed)") from error
    return removed


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        plan = build_plan((args.repo or current_directory()).resolve(), args.branch)
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
    print(f"deleted ignored paths: {', '.join(plan.ignored_paths) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
