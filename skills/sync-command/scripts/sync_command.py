#!/usr/bin/env python3
"""Sync a repo command into local Claude, Agents, and Codex command roots."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


COMMANDS_DIR = "commands"
CLAUDE_DIR = ".claude"
AGENTS_DIR = ".agents"
CODEX_DIR = ".codex"
HOME_COMMAND_ROOTS = {
    "claude": Path.home() / CLAUDE_DIR / COMMANDS_DIR,
    "agents": Path.home() / AGENTS_DIR / COMMANDS_DIR,
    "codex": Path.home() / CODEX_DIR / COMMANDS_DIR,
}
DRY_RUN_VERBS = {
    "created": "create",
    "updated": "update",
}


@dataclass(frozen=True)
class LinkPlan:
    label: str
    link_path: Path
    target_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync a repo command as local Claude, Agents, and Codex symlinks.",
    )
    parser.add_argument(
        "command",
        help="Command name (without .md) under <repo>/commands or path to a command file.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(),
        help="Repository root used when command is a name.",
    )
    parser.add_argument(
        "--claude-commands-dir",
        type=Path,
        default=HOME_COMMAND_ROOTS["claude"],
        help="Claude commands directory.",
    )
    parser.add_argument(
        "--agents-commands-dir",
        type=Path,
        default=HOME_COMMAND_ROOTS["agents"],
        help="Agents commands directory.",
    )
    parser.add_argument(
        "--codex-commands-dir",
        type=Path,
        default=HOME_COMMAND_ROOTS["codex"],
        help="Codex commands directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without touching the filesystem.",
    )
    return parser.parse_args()


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_command_source(repo_root: Path, command: str) -> Path:
    candidate = Path(command).expanduser()
    if candidate.is_absolute():
        source = candidate
    elif candidate.parts[0] in (".", ".."):
        source = Path.cwd() / candidate
    elif len(candidate.parts) > 1:
        source = repo_root / candidate
    else:
        # Bare name - look in commands/ dir, append .md if needed
        name = command if command.endswith(".md") else f"{command}.md"
        source = repo_root / COMMANDS_DIR / name
    return source.resolve(strict=False)


def require_command_source(source: Path) -> None:
    if not source.is_file():
        raise SystemExit(f"Error: command file not found: {source}")


def path_lexists(path: Path) -> bool:
    return os.path.lexists(path)


def ensure_symlink(link_path: Path, target_path: Path, dry_run: bool) -> str:
    link_path = link_path.expanduser()
    target_path = target_path.expanduser()

    if link_path.is_symlink():
        existing_target = link_path.readlink()
        if existing_target == target_path:
            return "unchanged"
        if not dry_run:
            link_path.unlink()
            link_path.symlink_to(target_path)
        return "updated"

    if path_lexists(link_path):
        if not dry_run:
            if link_path.is_dir():
                shutil.rmtree(link_path)
            else:
                link_path.unlink()
            link_path.symlink_to(target_path)
        return "updated"

    if not dry_run:
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(target_path)
    return "created"


def build_plan(args: argparse.Namespace, source: Path) -> list[LinkPlan]:
    command_name = source.name
    claude_link = args.claude_commands_dir.expanduser() / command_name
    return [
        LinkPlan("claude", claude_link, source),
        LinkPlan("agents", args.agents_commands_dir.expanduser() / command_name, claude_link),
        LinkPlan("codex", args.codex_commands_dir.expanduser() / command_name, claude_link),
    ]


def main() -> int:
    args = parse_args()
    source = resolve_command_source(args.repo_root.expanduser().resolve(strict=False), args.command)
    require_command_source(source)

    plan = build_plan(args, source)
    for item in plan:
        status = ensure_symlink(item.link_path, item.target_path, args.dry_run)
        display_status = DRY_RUN_VERBS.get(status, status) if args.dry_run else status
        prefix = "would " if args.dry_run and status != "unchanged" else ""
        print(f"{item.label}: {prefix}{display_status} {item.link_path} -> {item.target_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
