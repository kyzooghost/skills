#!/usr/bin/env python3
"""Sync a repo command into local command roots and Codex skills."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


COMMANDS_DIR = "commands"
SKILLS_DIR = "skills"
SKILL_MD = "SKILL.md"
AGENTS_METADATA_DIR = "agents"
OPENAI_YAML = "openai.yaml"
REFERENCES_DIR = "references"
COMMAND_REFERENCE_MD = "command.md"
CLAUDE_DIR = ".claude"
AGENTS_DIR = ".agents"
CODEX_DIR = ".codex"
HOME_COMMAND_ROOTS = {
    "claude": Path.home() / CLAUDE_DIR / COMMANDS_DIR,
    "agents": Path.home() / AGENTS_DIR / COMMANDS_DIR,
}
HOME_SKILL_ROOTS = {
    "codex": Path.home() / CODEX_DIR / SKILLS_DIR,
}
CODEX_SKILL_LABEL = "codex-skill"
REPO_SKILL_LABEL = "repo-skill"
COMMAND_REFERENCE_LABEL = "command-reference"
DRY_RUN_VERBS = {
    "created": "create",
    "updated": "update",
}


@dataclass(frozen=True)
class LinkPlan:
    label: str
    link_path: Path
    target_path: Path
    target_is_directory: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync a repo command as local Claude/Agents commands and a Codex skill.",
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
        "--codex-skills-dir",
        type=Path,
        default=HOME_SKILL_ROOTS["codex"],
        help="Codex skills directory.",
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


def ensure_symlink(link_path: Path, target_path: Path, dry_run: bool, target_is_directory: bool = False) -> str:
    link_path = link_path.expanduser()
    target_path = target_path.expanduser()

    if link_path.is_symlink():
        existing_target = link_path.readlink()
        if existing_target == target_path:
            return "unchanged"
        if not dry_run:
            link_path.unlink()
            link_path.symlink_to(target_path, target_is_directory=target_is_directory)
        return "updated"

    if path_lexists(link_path):
        if not dry_run:
            if link_path.is_dir():
                shutil.rmtree(link_path)
            else:
                link_path.unlink()
            link_path.symlink_to(target_path, target_is_directory=target_is_directory)
        return "updated"

    if not dry_run:
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(target_path, target_is_directory=target_is_directory)
    return "created"


def command_skill_name(source: Path) -> str:
    return source.stem


def command_display_name(skill_name: str) -> str:
    return skill_name.replace("-", " ").replace("_", " ").title()


def command_skill_dir(repo_root: Path, source: Path) -> Path:
    return repo_root / SKILLS_DIR / command_skill_name(source)


def command_reference_target(reference_dir: Path, source: Path) -> Path:
    return Path(os.path.relpath(source, reference_dir))


def generated_skill_md(skill_name: str) -> str:
    return (
        "---\n"
        f"name: {skill_name}\n"
        f"description: Use when the user asks for /{skill_name} behavior or the equivalent command workflow.\n"
        "---\n"
        "\n"
        f"# {command_display_name(skill_name)}\n"
        "\n"
        f"Read and follow `references/{COMMAND_REFERENCE_MD}`.\n"
    )


def generated_openai_yaml(skill_name: str) -> str:
    return (
        "interface:\n"
        f"  display_name: \"{command_display_name(skill_name)}\"\n"
        "  short_description: \"Run a repo command as a Codex skill\"\n"
        f"  default_prompt: \"Use ${skill_name} for this workflow.\"\n"
    )


def ensure_repo_command_skill(repo_root: Path, source: Path, dry_run: bool) -> tuple[Path, list[tuple[str, str, Path]]]:
    skill_name = command_skill_name(source)
    skill_dir = command_skill_dir(repo_root, source)
    skill_md = skill_dir / SKILL_MD
    reference_dir = skill_dir / REFERENCES_DIR
    command_reference = reference_dir / COMMAND_REFERENCE_MD
    openai_yaml = skill_dir / AGENTS_METADATA_DIR / OPENAI_YAML
    statuses: list[tuple[str, str, Path]] = []

    if skill_md.is_file():
        statuses.append((REPO_SKILL_LABEL, "unchanged", skill_md))
    else:
        statuses.append((REPO_SKILL_LABEL, "created", skill_md))
        if not dry_run:
            skill_md.parent.mkdir(parents=True, exist_ok=True)
            skill_md.write_text(generated_skill_md(skill_name), encoding="utf-8")
            openai_yaml.parent.mkdir(parents=True, exist_ok=True)
            openai_yaml.write_text(generated_openai_yaml(skill_name), encoding="utf-8")

    reference_status = ensure_symlink(
        command_reference,
        command_reference_target(reference_dir, source),
        dry_run,
    )
    statuses.append((COMMAND_REFERENCE_LABEL, reference_status, command_reference))
    return skill_dir, statuses


def build_command_link_plan(args: argparse.Namespace, source: Path) -> list[LinkPlan]:
    command_name = source.name
    claude_link = args.claude_commands_dir.expanduser() / command_name
    return [
        LinkPlan("claude", claude_link, source),
        LinkPlan("agents", args.agents_commands_dir.expanduser() / command_name, claude_link),
    ]


def build_codex_skill_plan(args: argparse.Namespace, skill_dir: Path) -> list[LinkPlan]:
    return [
        LinkPlan(
            CODEX_SKILL_LABEL,
            args.codex_skills_dir.expanduser() / skill_dir.name,
            skill_dir,
            target_is_directory=True,
        ),
    ]


def main() -> int:
    args = parse_args()
    source = resolve_command_source(args.repo_root.expanduser().resolve(strict=False), args.command)
    require_command_source(source)
    repo_root = args.repo_root.expanduser().resolve(strict=False)

    skill_dir, repo_skill_statuses = ensure_repo_command_skill(repo_root, source, args.dry_run)
    for label, status, path in repo_skill_statuses:
        display_status = DRY_RUN_VERBS.get(status, status) if args.dry_run else status
        prefix = "would " if args.dry_run and status != "unchanged" else ""
        print(f"{label}: {prefix}{display_status} {path}")

    plan = build_command_link_plan(args, source) + build_codex_skill_plan(args, skill_dir)
    for item in plan:
        status = ensure_symlink(item.link_path, item.target_path, args.dry_run, item.target_is_directory)
        display_status = DRY_RUN_VERBS.get(status, status) if args.dry_run else status
        prefix = "would " if args.dry_run and status != "unchanged" else ""
        print(f"{item.label}: {prefix}{display_status} {item.link_path} -> {item.target_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
