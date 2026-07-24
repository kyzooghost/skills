from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMAND = REPO_ROOT / "commands" / "create-pr.md"
REFERENCE = REPO_ROOT / "skills" / "create-pr" / "references" / "command.md"


class CreatePrCommandTest(unittest.TestCase):
    def test_packaged_skill_uses_the_canonical_command(self) -> None:
        # Arrange
        expected_target = Path("../../../commands/create-pr.md")

        # Act
        actual_target = REFERENCE.readlink()

        # Assert
        self.assertTrue(REFERENCE.is_symlink())
        self.assertEqual(actual_target, expected_target)
        self.assertEqual(REFERENCE.resolve(), COMMAND.resolve())

    def test_command_reuses_one_resolved_base_branch(self) -> None:
        # Arrange
        required_fragments = (
            "--base <branch>",
            "baseRefName",
            "defaultBranchRef",
            'git fetch origin "$BASE_BRANCH"',
            'git diff "origin/$BASE_BRANCH"...HEAD',
            'git log "origin/$BASE_BRANCH"..HEAD',
            'git diff "origin/$BASE_BRANCH"...HEAD --name-only',
            'gh pr create --base "$BASE_BRANCH"',
            'gh pr edit "$PR_NUMBER" --base "$BASE_BRANCH"',
        )

        # Act
        command = COMMAND.read_text(encoding="utf-8")

        # Assert
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, command)

    def test_command_supports_draft_creation_but_rejects_draft_updates(self) -> None:
        # Arrange
        required_fragments = (
            "/create-pr [--base <branch>] [--draft]",
            "/create-pr --update [--base <branch>]",
            'gh pr create --base "$BASE_BRANCH" --draft',
            "`--update --draft` is unsupported",
        )

        # Act
        command = COMMAND.read_text(encoding="utf-8")

        # Assert
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, command)


if __name__ == "__main__":
    unittest.main()
