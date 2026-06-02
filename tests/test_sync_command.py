from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "sync-command" / "scripts" / "sync_command.py"


class SyncCommandTest(unittest.TestCase):
    def test_sync_command_installs_codex_skill_for_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_root = (root / "repo").resolve()
            commands_dir = repo_root / "commands"
            claude_commands = root / "claude" / "commands"
            agents_commands = root / "agents" / "commands"
            codex_skills = root / "codex" / "skills"
            commands_dir.mkdir(parents=True)
            command_file = commands_dir / "demo-command.md"
            command_file.write_text("Run the demo command.\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "demo-command",
                    "--repo-root",
                    str(repo_root),
                    "--claude-commands-dir",
                    str(claude_commands),
                    "--agents-commands-dir",
                    str(agents_commands),
                    "--codex-skills-dir",
                    str(codex_skills),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            skill_dir = repo_root / "skills" / "demo-command"
            skill_md = skill_dir / "SKILL.md"
            command_reference = skill_dir / "references" / "command.md"

            self.assertEqual((claude_commands / "demo-command.md").readlink(), command_file.resolve())
            self.assertEqual(
                (agents_commands / "demo-command.md").readlink(),
                claude_commands / "demo-command.md",
            )
            self.assertEqual((codex_skills / "demo-command").readlink(), skill_dir)
            self.assertIn("codex-skill: created", result.stdout)
            self.assertIn("name: demo-command", skill_md.read_text(encoding="utf-8"))
            self.assertEqual(command_reference.readlink(), Path("../../../commands/demo-command.md"))
            self.assertEqual(command_reference.resolve().read_text(encoding="utf-8"), "Run the demo command.\n")

    def test_sync_command_preserves_existing_repo_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_root = (root / "repo").resolve()
            commands_dir = repo_root / "commands"
            skill_dir = repo_root / "skills" / "demo-command"
            codex_skills = root / "codex" / "skills"
            commands_dir.mkdir(parents=True)
            skill_dir.mkdir(parents=True)
            (commands_dir / "demo-command.md").write_text("Run the demo command.\n", encoding="utf-8")
            skill_md = skill_dir / "SKILL.md"
            original_skill = (
                "---\n"
                "name: demo-command\n"
                "description: Use when the existing skill should be preserved.\n"
                "---\n"
                "\n"
                "# Demo Command\n"
                "\n"
                "Keep this custom body.\n"
            )
            skill_md.write_text(original_skill, encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "demo-command",
                    "--repo-root",
                    str(repo_root),
                    "--codex-skills-dir",
                    str(codex_skills),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual((codex_skills / "demo-command").readlink(), skill_dir)
            self.assertEqual(skill_md.read_text(encoding="utf-8"), original_skill)


if __name__ == "__main__":
    unittest.main()
