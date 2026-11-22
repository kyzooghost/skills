#!/usr/bin/env python3
"""Install or update obra/superpowers for Claude Code, Codex, and Cursor.

All three tools read one git checkout pinned to a release tag. Claude Code
loads the checkout as a local-path plugin marketplace. Codex and Cursor load
~/.agents/skills symlinks into the checkout.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


REPO_SLUG = "obra/superpowers"
REPO_URL = f"https://github.com/{REPO_SLUG}.git"
MARKETPLACE = "superpowers-dev"
PLUGIN = "superpowers"
PLUGIN_ID = f"{PLUGIN}@{MARKETPLACE}"
USER_SCOPE = "user"
DIRECTORY_SOURCE = "directory"
SKILLS_DIR = "skills"
SKILL_MD = "SKILL.md"
DEFAULT_CHECKOUT_DIR = Path.home() / ".local" / "share" / "superpowers"
DEFAULT_AGENTS_SKILLS_DIR = Path.home() / ".agents" / SKILLS_DIR
REQUIRED_TOOLS = ("git", "claude", "codex")

# Cursor reads all of these roots, and Codex reads ~/.codex/skills, so a
# superpowers skill in one of them appears twice.
DUPLICATE_SKILL_ROOTS = (".claude", ".codex", ".cursor")


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


def require_clean_checkout(checkout_dir: Path, repo_url: str) -> None:
    if not (checkout_dir / ".git").exists():
        raise SyncError(f"{checkout_dir} exists but is not a git checkout; move it or pass another --checkout-dir")
    # Read the stored URL. `git remote get-url` applies url.<base>.insteadOf
    # rewrites, so a user's HTTPS-to-SSH rewrite would look like a wrong origin.
    try:
        origin = git(checkout_dir, "config", "--get", "remote.origin.url").strip()
    except SyncError:
        raise SyncError(f"{checkout_dir} has no origin remote; move it or pass another --checkout-dir") from None
    if origin != repo_url:
        raise SyncError(
            f"{checkout_dir} origin is {origin}, expected {repo_url}; "
            "pass the same --repo-url as the first run, or another --checkout-dir"
        )
    if git(checkout_dir, "status", "--porcelain", "--untracked-files=all").strip():
        raise SyncError(f"{checkout_dir} has local changes; commit, move, or discard them first")


def require_link_slots(agents_dir: Path, skills: tuple[str, ...]) -> None:
    for name in skills:
        path = agents_dir / name
        if os.path.lexists(path) and not path.is_symlink():
            raise SyncError(f"{path} is a real file or directory; move it, then run again")


def prepare_repo(checkout_dir: Path, repo_url: str, dry_run: bool, temp_dirs: list[Path]) -> Path:
    """Return a repository with fresh tags: the checkout, or a temporary clone in a dry run."""
    if os.path.lexists(checkout_dir):
        require_clean_checkout(checkout_dir, repo_url)
        repo_dir = checkout_dir
    else:
        if dry_run:
            temp_dir = Path(tempfile.mkdtemp(prefix="sync-superpowers-"))
            temp_dirs.append(temp_dir)
            repo_dir = temp_dir / "checkout"
        else:
            checkout_dir.parent.mkdir(parents=True, exist_ok=True)
            repo_dir = checkout_dir
        # The temporary clone is read only with ls-tree, so it skips the working tree.
        # The real checkout gets one, so a failed run leaves it clean for the next run.
        clone_mode = ["--no-checkout"] if dry_run else []
        run(["git", "clone", "--quiet", *clone_mode, "--", repo_url, str(repo_dir)])
    git(repo_dir, "fetch", "--quiet", "--tags", "--force", "origin")
    return repo_dir


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


def preflight(
    version: str | None,
    repo_url: str,
    checkout_dir: Path,
    agents_dir: Path,
    dry_run: bool,
    temp_dirs: list[Path],
) -> Release:
    require_tools(need_gh=version is None)
    tag = resolve_tag(version)
    repo_dir = prepare_repo(checkout_dir, repo_url, dry_run, temp_dirs)
    try:
        git(repo_dir, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
    except SyncError:
        raise SyncError(f"tag {tag} not found in {repo_url}") from None
    skills = list_tag_skills(repo_dir, tag)
    require_link_slots(agents_dir, skills)
    return Release(tag=tag, skills=skills)


def checkout_tag(checkout_dir: Path, tag: str, report: Report) -> None:
    report.action(f"check out {tag} in {checkout_dir}")
    if not report.dry_run:
        git(checkout_dir, "checkout", "--quiet", "--detach", f"refs/tags/{tag}")


def run_write(cmd: list[str], report: Report) -> None:
    report.action(f"run: {shlex.join(cmd)}")
    if not report.dry_run:
        run(cmd)


def read_json_list(cmd: list[str], key: str | None = None) -> list[dict]:
    """Run a CLI listing and return its list of objects, or the list under `key`."""
    output = run(cmd)
    try:
        value = json.loads(output)
    except json.JSONDecodeError as error:
        raise SyncError(f"invalid JSON from {shlex.join(cmd)}: {error}") from None
    if key is not None:
        value = value.get(key, []) if isinstance(value, dict) else None
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        field_note = f" field {key!r}" if key else ""
        raise SyncError(f"unexpected JSON from {shlex.join(cmd)}{field_note}: expected a list of objects")
    return value


def points_at(marketplace: dict, checkout_dir: Path) -> bool:
    path = marketplace.get("path")
    return (
        marketplace.get("source") == DIRECTORY_SOURCE
        and path is not None
        and Path(path).resolve() == checkout_dir
    )


def verify_claude(tag: str) -> dict:
    expected = tag.removeprefix("v")
    for plugin in read_json_list(["claude", "plugin", "list", "--json"]):
        if plugin.get("id") == PLUGIN_ID and plugin.get("scope") == USER_SCOPE:
            if not plugin.get("enabled"):
                raise SyncError(f"Claude reports {PLUGIN_ID} disabled; run: claude plugin enable {PLUGIN_ID}")
            if plugin.get("version") != expected:
                raise SyncError(
                    f"Claude reports {PLUGIN_ID} version {plugin.get('version')}; expected {expected}"
                )
            return plugin
    raise SyncError(f"Claude does not list {PLUGIN_ID} at user scope after install")


def sync_claude(checkout_dir: Path, tag: str, report: Report) -> dict | None:
    marketplaces = read_json_list(["claude", "plugin", "marketplace", "list", "--json"])
    current = next((m for m in marketplaces if m.get("name") == MARKETPLACE), None)
    add = ["claude", "plugin", "marketplace", "add", str(checkout_dir)]
    replaced = False
    if current is None:
        run_write(add, report)
    elif not points_at(current, checkout_dir):
        # Removing the marketplace also uninstalls its plugins, so the plugin
        # must be installed again. Track it here so a dry run reports the same.
        run_write(["claude", "plugin", "marketplace", "remove", MARKETPLACE], report)
        run_write(add, report)
        replaced = True
    else:
        run_write(["claude", "plugin", "marketplace", "update", MARKETPLACE], report)

    plugins = read_json_list(["claude", "plugin", "list", "--json"])
    installed = not replaced and any(
        p.get("id") == PLUGIN_ID and p.get("scope") == USER_SCOPE for p in plugins
    )
    run_write(["claude", "plugin", "update" if installed else "install", PLUGIN_ID], report)

    uninstalled: set[str] = set()
    for plugin in plugins:
        plugin_id = plugin.get("id") or ""
        if plugin_id == PLUGIN_ID or plugin_id.split("@")[0] != PLUGIN:
            continue
        scope = plugin.get("scope")
        if scope == USER_SCOPE:
            if plugin_id not in uninstalled:
                run_write(["claude", "plugin", "uninstall", plugin_id], report)
                uninstalled.add(plugin_id)
        else:
            project = plugin.get("projectPath") or "an unknown project"
            report.warn(f"Claude plugin {plugin_id} is installed at {scope} scope for {project}; left unchanged")

    if report.dry_run:
        return None
    return verify_claude(tag)


def installed_codex_superpowers() -> list[str]:
    installed = read_json_list(["codex", "plugin", "list", "--json"], key="installed")
    plugin_ids = []
    for plugin in installed:
        if plugin.get("name") != PLUGIN or not plugin.get("installed"):
            continue
        plugin_id = plugin.get("pluginId")
        if not plugin_id:
            raise SyncError(f"Codex lists an installed {PLUGIN} plugin without a pluginId")
        plugin_ids.append(plugin_id)
    return plugin_ids


def sync_codex(report: Report) -> None:
    # Codex reads ~/.agents/skills, so any superpowers plugin would duplicate the links.
    for plugin_id in installed_codex_superpowers():
        run_write(["codex", "plugin", "remove", plugin_id], report)

    marketplaces = read_json_list(["codex", "plugin", "marketplace", "list", "--json"], key="marketplaces")
    if any(m.get("name") == MARKETPLACE for m in marketplaces):
        run_write(["codex", "plugin", "marketplace", "remove", MARKETPLACE], report)

    if not report.dry_run:
        remaining = installed_codex_superpowers()
        if remaining:
            raise SyncError(f"Codex still lists installed superpowers plugins: {', '.join(remaining)}")


def link_target(link: Path) -> Path:
    """Return the absolute target of a symlink, without following the final component."""
    target = Path(os.readlink(link))
    if not target.is_absolute():
        target = link.parent / target
    # The OS resolves ".." through the real parent directory, so resolve the
    # parent through the file system, not as text. The skill directory itself
    # may already be gone after a tag change, so do not resolve the last part.
    return Path(os.path.realpath(target.parent)) / target.name


def sync_links(agents_dir: Path, checkout_dir: Path, skills: tuple[str, ...], report: Report) -> LinkChanges:
    skills_root = checkout_dir / SKILLS_DIR
    changes = LinkChanges()
    for name in skills:
        link = agents_dir / name
        target = skills_root / name
        if link.is_symlink():
            if link_target(link) == target:
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

    # Only links into our checkout are ours to prune. Leave every other entry alone.
    existing = sorted(agents_dir.iterdir()) if agents_dir.is_dir() else []
    for link in existing:
        if link.name in skills or not link.is_symlink():
            continue
        if link_target(link).parent == skills_root:
            report.action(f"remove link {link}")
            changes.pruned.append(link.name)
            if not report.dry_run:
                link.unlink()
    return changes


def warn_duplicates(skills: tuple[str, ...], report: Report) -> None:
    for root in DUPLICATE_SKILL_ROOTS:
        skills_dir = Path.home() / root / SKILLS_DIR
        for name in skills:
            path = skills_dir / name
            if os.path.lexists(path):
                report.warn(
                    f"{path} duplicates superpowers skill {name}; remove it so each tool lists the skill once"
                )


def print_summary(release: Release, claude_plugin: dict | None, links: LinkChanges, report: Report) -> None:
    print()
    suffix = " (dry run: nothing changed)" if report.dry_run else ""
    print(f"superpowers {release.tag}{suffix}")
    if claude_plugin:
        print(
            f"claude: {claude_plugin['id']} scope={claude_plugin['scope']} "
            f"version={claude_plugin['version']}"
        )
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
    temp_dirs: list[Path] = []
    completed = None
    try:
        release = preflight(args.version, args.repo_url, checkout_dir, agents_dir, args.dry_run, temp_dirs)
        completed = "preflight"
        if report.dry_run and not os.path.lexists(checkout_dir):
            report.action(f"clone {args.repo_url} into {checkout_dir}")
        checkout_tag(checkout_dir, release.tag, report)
        completed = "checkout"
        claude_plugin = sync_claude(checkout_dir, release.tag, report)
        completed = "claude"
        sync_codex(report)
        completed = "codex"
        links = sync_links(agents_dir, checkout_dir, release.skills, report)
        warn_duplicates(release.skills, report)
        completed = "links"
    except (SyncError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        if completed:
            print(f"last completed phase: {completed}; run again to finish", file=sys.stderr)
        return 1
    finally:
        for temp_dir in temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except OSError as error:
                # Do not let a cleanup failure hide the run's real result.
                print(f"warning: could not remove {temp_dir}: {error}", file=sys.stderr)
    print_summary(release, claude_plugin, links, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
