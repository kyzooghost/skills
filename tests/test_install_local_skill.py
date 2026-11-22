from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "sync-skill" / "scripts" / "install_local_skill.py"


class InstallLocalSkillTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name).resolve()
        self.repo_root = self.root / "repo"
        self.source = self.repo_root / "skills" / "demo-skill"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text("---\nname: demo-skill\ndescription: Demo.\n---\n", encoding="utf-8")
        self.claude_skills = self.root / "claude" / "skills"
        self.agents_skills = self.root / "agents" / "skills"
        self.codex_skills = self.root / "codex" / "skills"

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def run_install(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "demo-skill",
                "--repo-root", str(self.repo_root),
                "--claude-skills-dir", str(self.claude_skills),
                "--agents-skills-dir", str(self.agents_skills),
                "--codex-skills-dir", str(self.codex_skills),
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    def test_installs_claude_and_agents_links_only(self) -> None:
        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        claude_link = self.claude_skills / "demo-skill"
        self.assertEqual(claude_link.readlink(), self.source)
        self.assertEqual((self.agents_skills / "demo-skill").readlink(), claude_link)
        self.assertFalse((self.codex_skills / "demo-skill").exists())
        self.assertNotIn("codex:", result.stdout)

    def test_removes_legacy_codex_duplicate(self) -> None:
        self.codex_skills.mkdir(parents=True)
        legacy = self.codex_skills / "demo-skill"
        legacy.symlink_to(self.claude_skills / "demo-skill")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(legacy.is_symlink())
        self.assertIn(f"codex: removed duplicate {legacy}", result.stdout)

    def test_dry_run_reports_legacy_codex_duplicate_without_removing_it(self) -> None:
        self.codex_skills.mkdir(parents=True)
        legacy = self.codex_skills / "demo-skill"
        legacy.symlink_to(self.source)

        result = self.run_install("--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(legacy.is_symlink())
        self.assertIn(f"codex: would remove duplicate {legacy}", result.stdout)

    def test_keeps_unrelated_codex_entries(self) -> None:
        other_target = self.root / "other-skill"
        other_target.mkdir()
        self.codex_skills.mkdir(parents=True)
        (self.codex_skills / "demo-skill").symlink_to(other_target)

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.codex_skills / "demo-skill").readlink(), other_target)
        self.assertNotIn("codex:", result.stdout)


if __name__ == "__main__":
    unittest.main()
