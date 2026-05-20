#!/usr/bin/env python3
"""Install a repo skill into local Claude, Agents, and Codex skill roots."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path


SKILL_MD = "SKILL.md"
SKILLS_DIR = "skills"
CLAUDE_DIR = ".claude"
AGENTS_DIR = ".agents"
CODEX_DIR = ".codex"
HOME_SKILL_ROOTS = {
    "claude": Path.home() / CLAUDE_DIR / SKILLS_DIR,
    "agents": Path.home() / AGENTS_DIR / SKILLS_DIR,
    "codex": Path.home() / CODEX_DIR / SKILLS_DIR,
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
        description="Install or refresh a repo skill as local Claude, Agents, and Codex symlinks.",
    )
    parser.add_argument(
        "skill",
        help="Skill name under <repo>/skills or path to a skill directory.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(),
        help="Repository root used when skill is a name.",
    )
    parser.add_argument(
        "--claude-skills-dir",
        type=Path,
        default=HOME_SKILL_ROOTS["claude"],
        help="Claude skills directory.",
    )
    parser.add_argument(
        "--agents-skills-dir",
        type=Path,
        default=HOME_SKILL_ROOTS["agents"],
        help="Agents skills directory.",
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


def resolve_skill_source(repo_root: Path, skill: str) -> Path:
    candidate = Path(skill).expanduser()
    if candidate.is_absolute():
        source = candidate
    elif candidate.parts[0] in (".", ".."):
        source = Path.cwd() / candidate
    elif len(candidate.parts) > 1:
        source = repo_root / candidate
    else:
        source = repo_root / SKILLS_DIR / skill
    return source.resolve(strict=False)


def require_skill_source(source: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"Error: skill directory not found: {source}")
    skill_md = source / SKILL_MD
    if not skill_md.is_file():
        raise SystemExit(f"Error: {SKILL_MD} not found in skill directory: {source}")


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
            link_path.symlink_to(target_path, target_is_directory=True)
        return "updated"

    if path_lexists(link_path):
        raise SystemExit(
            f"Error: refusing to replace non-symlink path: {link_path}. "
            "Inspect it and get explicit approval before changing it."
        )

    if not dry_run:
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(target_path, target_is_directory=True)
    return "created"


def build_plan(args: argparse.Namespace, source: Path) -> list[LinkPlan]:
    skill_name = source.name
    claude_link = args.claude_skills_dir.expanduser() / skill_name
    return [
        LinkPlan("claude", claude_link, source),
        LinkPlan("agents", args.agents_skills_dir.expanduser() / skill_name, claude_link),
        LinkPlan("codex", args.codex_skills_dir.expanduser() / skill_name, claude_link),
    ]


def main() -> int:
    args = parse_args()
    source = resolve_skill_source(args.repo_root.expanduser().resolve(strict=False), args.skill)
    require_skill_source(source)

    plan = build_plan(args, source)
    for item in plan:
        status = ensure_symlink(item.link_path, item.target_path, args.dry_run)
        display_status = DRY_RUN_VERBS.get(status, status) if args.dry_run else status
        prefix = "would " if args.dry_run and status != "unchanged" else ""
        print(f"{item.label}: {prefix}{display_status} {item.link_path} -> {item.target_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
