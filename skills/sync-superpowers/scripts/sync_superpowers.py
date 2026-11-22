#!/usr/bin/env python3
"""Install or update obra/superpowers for Claude Code, Codex, and Cursor.

All three tools read one git checkout pinned to a release tag. Claude Code
loads the checkout as a local-path plugin marketplace. Codex and Cursor load
~/.agents/skills symlinks into the checkout.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


REPO_SLUG = "obra/superpowers"
REPO_URL = f"https://github.com/{REPO_SLUG}.git"
SKILLS_DIR = "skills"
SKILL_MD = "SKILL.md"
DEFAULT_CHECKOUT_DIR = Path.home() / ".local" / "share" / "superpowers"
DEFAULT_AGENTS_SKILLS_DIR = Path.home() / ".agents" / SKILLS_DIR
REQUIRED_TOOLS = ("git", "claude", "codex")


class SyncError(Exception):
    """A failure that stops the run with a message for the user."""


@dataclass
class Report:
    dry_run: bool
    warnings: list[str] = field(default_factory=list)

    def action(self, message: str) -> None:
        print(f"would {message}" if self.dry_run else message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


@dataclass(frozen=True)
class Release:
    tag: str
    skills: tuple[str, ...]


@dataclass
class LinkChanges:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    pruned: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install or update obra/superpowers for Claude Code, Codex, and Cursor.",
    )
    parser.add_argument("--version", help="Release tag to install, for example v7.0.2. Default: latest release.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing anything.")
    parser.add_argument("--checkout-dir", type=Path, default=DEFAULT_CHECKOUT_DIR, help="Managed checkout location.")
    parser.add_argument(
        "--agents-skills-dir",
        type=Path,
        default=DEFAULT_AGENTS_SKILLS_DIR,
        help="Skill links for Codex and Cursor.",
    )
    parser.add_argument("--repo-url", default=REPO_URL, help="Clone source.")
    return parser.parse_args()


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SyncError(f"command failed: {shlex.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout


def git(repo: Path, *args: str) -> str:
    return run(["git", "-C", str(repo), *args])


def require_tools(need_gh: bool) -> None:
    tools = REQUIRED_TOOLS + (("gh",) if need_gh else ())
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        raise SyncError(f"missing required tools on PATH: {', '.join(missing)}")


def resolve_tag(version: str | None) -> str:
    if version:
        return version
    tag = run(["gh", "release", "view", "-R", REPO_SLUG, "--json", "tagName", "--jq", ".tagName"]).strip()
    if not tag:
        raise SyncError(f"gh returned no latest release for {REPO_SLUG}")
    return tag


def prepare_repo(checkout_dir: Path, repo_url: str) -> Path:
    if not os.path.lexists(checkout_dir):
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", "--", repo_url, str(checkout_dir)])
    git(checkout_dir, "fetch", "--quiet", "--tags", "--force", "origin")
    return checkout_dir


def list_tag_skills(repo_dir: Path, tag: str) -> tuple[str, ...]:
    listing = git(repo_dir, "ls-tree", "-r", "-z", "--name-only", f"refs/tags/{tag}", "--", SKILLS_DIR)
    paths = listing.split("\0")
    names = sorted(
        parts[1]
        for parts in (path.split("/") for path in paths)
        if len(parts) == 3 and parts[2] == SKILL_MD
    )
    if not names:
        raise SyncError(f"tag {tag} has no {SKILLS_DIR}/<name>/{SKILL_MD}")
    return tuple(names)


def preflight(version: str | None, repo_url: str, checkout_dir: Path) -> Release:
    require_tools(need_gh=version is None)
    tag = resolve_tag(version)
    repo_dir = prepare_repo(checkout_dir, repo_url)
    try:
        git(repo_dir, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
    except SyncError:
        raise SyncError(f"tag {tag} not found in {repo_url}") from None
    return Release(tag=tag, skills=list_tag_skills(repo_dir, tag))


def checkout_tag(checkout_dir: Path, tag: str, report: Report) -> None:
    report.action(f"check out {tag} in {checkout_dir}")
    if not report.dry_run:
        git(checkout_dir, "checkout", "--quiet", "--detach", f"refs/tags/{tag}")


def sync_links(agents_dir: Path, checkout_dir: Path, skills: tuple[str, ...], report: Report) -> LinkChanges:
    skills_root = checkout_dir / SKILLS_DIR
    changes = LinkChanges()
    for name in skills:
        link = agents_dir / name
        target = skills_root / name
        if link.is_symlink():
            if Path(os.readlink(link)) == target:
                continue
            report.action(f"update link {link} -> {target}")
            changes.updated.append(name)
            if not report.dry_run:
                link.unlink()
                link.symlink_to(target, target_is_directory=True)
        else:
            report.action(f"create link {link} -> {target}")
            changes.created.append(name)
            if not report.dry_run:
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target, target_is_directory=True)
    return changes


def print_summary(release: Release, links: LinkChanges, report: Report) -> None:
    print()
    suffix = " (dry run: nothing changed)" if report.dry_run else ""
    print(f"superpowers {release.tag}{suffix}")
    print(
        f"links: {len(links.created)} created, {len(links.updated)} updated, "
        f"{len(links.pruned)} removed, {len(release.skills)} total"
    )
    for warning in report.warnings:
        print(f"warning: {warning}")
    if not report.dry_run:
        print("Restart Claude Code, Codex, and Cursor to load the change.")


def main() -> int:
    args = parse_args()
    checkout_dir = args.checkout_dir.expanduser().resolve()
    agents_dir = args.agents_skills_dir.expanduser()
    report = Report(dry_run=args.dry_run)
    completed = None
    try:
        release = preflight(args.version, args.repo_url, checkout_dir)
        completed = "preflight"
        checkout_tag(checkout_dir, release.tag, report)
        completed = "checkout"
        links = sync_links(agents_dir, checkout_dir, release.skills, report)
        completed = "links"
    except (SyncError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        if completed:
            print(f"last completed phase: {completed}; run again to finish", file=sys.stderr)
        return 1
    print_summary(release, links, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
