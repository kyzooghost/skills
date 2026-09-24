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

    def test_publish_command_documents_skip_prep(self) -> None:
        # Arrange
        required_fragments = (
            "--skip-prep",
            "/create-pr [--base <branch>] [--draft]",
            "/create-pr --update [--base <branch>]",
            'gh pr create --base "$BASE_BRANCH" --draft',
        )

        # Act
        command = COMMAND.read_text(encoding="utf-8")

        # Assert
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, command)

    def test_skill_routes_one_prep_path_before_publish(self) -> None:
        # Arrange
        skill = REPO_ROOT / "skills" / "create-pr" / "SKILL.md"
        required_fragments = (
            "Skip prep",
            "--skip-prep",
            "references/stacked-prep.md",
            "references/normal-prep.md",
            "references/command.md",
            "does not follow",
        )

        # Act
        text = skill.read_text(encoding="utf-8")

        # Assert
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_normal_prep_transplants_without_publishing(self) -> None:
        # Arrange
        path = REPO_ROOT / "skills" / "create-pr" / "references" / "normal-prep.md"
        required_fragments = (
            "origin/BASE",
            "--base",
            "cherry-pick",
            "git ls-files --others --exclude-standard",
            "Do not stash",
            "git push --set-upstream origin",
            "nothing to publish",
        )
        self.assertTrue(path.is_file())

        # Act
        text = path.read_text(encoding="utf-8")

        # Assert
        self.assertNotIn("gh pr create", text)
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_stacked_prep_updates_the_remote_pr_before_the_child_branch(self) -> None:
        # Arrange
        path = REPO_ROOT / "skills" / "create-pr" / "references" / "stacked-prep.md"
        required_fragments = (
            "origin/$PR_BRANCH",
            "Do not force-push",
            "already up to date",
            "statusCheckRollup",
            "mergeStateStatus",
            "failing or pending checks",
            "merge conflict",
            "git push --set-upstream origin",
            '--base "$PR_BRANCH"',
            "state",
            "later poll",
        )
        self.assertTrue(path.is_file())

        # Act
        text = path.read_text(encoding="utf-8")

        # Assert
        self.assertNotIn("gh pr create", text)
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_ship_from_plan_skips_create_pr_prep(self) -> None:
        # Arrange
        skill = REPO_ROOT / "skills" / "ship-from-plan" / "SKILL.md"

        # Act
        text = skill.read_text(encoding="utf-8")

        # Assert
        self.assertIn("/create-pr --skip-prep", text)
        self.assertIn('Add `--base "$BASE_BRANCH"` only when the user supplied `BASE_BRANCH`', text)
        self.assertNotIn("/create-pr --draft", text)


if __name__ == "__main__":
    unittest.main()
