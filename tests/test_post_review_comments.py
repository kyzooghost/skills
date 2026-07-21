from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "pr-review-comments" / "scripts"
SCRIPT = SCRIPTS_DIR / "post_review_comments.py"
sys.path.insert(0, str(SCRIPTS_DIR))

from post_review_comments import (  # noqa: E402
    PostReviewCommentsError,
    post_review_comments,
    run_gh_api,
)


class FakeGhRunner:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> dict[str, object]:
        self.calls.append(args)
        return self.responses.pop(0)


def valid_spec(primary_body: str, companion_body: str) -> dict[str, object]:
    return {
        "repo": "owner/repo",
        "pr": 29,
        "commit": "a" * 40,
        "primary": {
            "path": "src/Primary.kt",
            "line": 43,
            "body": primary_body,
        },
        "companions": [
            {
                "path": "src/Companion.kt",
                "line": 27,
                "body": companion_body,
            }
        ],
    }


class PostReviewCommentsTest(unittest.TestCase):
    def test_posts_companion_with_real_primary_url_and_preserves_markdown(self) -> None:
        # Arrange
        primary_body = "**[LOW-1] Finding**\n\n`primary code`"
        companion_template = (
            "**[LOW-1] Finding**\n\n`companion code`\n\n"
            "See primary comment: {primary_url}"
        )
        primary_response = {
            "id": 100,
            "html_url": "https://github.com/owner/repo/pull/29#discussion_r100",
            "body": primary_body,
            "path": "src/Primary.kt",
            "line": 43,
        }
        companion_response = {
            "id": 101,
            "html_url": "https://github.com/owner/repo/pull/29#discussion_r101",
            "body": companion_template.format(primary_url=primary_response["html_url"]),
            "path": "src/Companion.kt",
            "line": 27,
        }
        spec = {
            "repo": "owner/repo",
            "pr": 29,
            "commit": "a" * 40,
            "primary": {
                "path": "src/Primary.kt",
                "line": 43,
                "body": primary_body,
            },
            "companions": [
                {
                    "path": "src/Companion.kt",
                    "line": 27,
                    "body": companion_template,
                }
            ],
        }
        runner = FakeGhRunner([primary_response, companion_response])

        # Act
        result = post_review_comments(spec, runner=runner)

        # Assert
        self.assertEqual(result, [primary_response, companion_response])
        companion_body_arg = runner.calls[1][runner.calls[1].index("-f") + 1]
        self.assertIn("`companion code`", companion_body_arg)
        self.assertIn("discussion_r100", companion_body_arg)

    def test_rejects_primary_url_token_before_mutation(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        runner = FakeGhRunner([])

        # Act and Assert
        with self.assertRaisesRegex(PostReviewCommentsError, "primary"):
            post_review_comments(spec, runner=runner)
        self.assertEqual(runner.calls, [])

    def test_rejects_repo_without_owner_and_repository_before_mutation(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        spec["repo"] = "owner/"
        runner = FakeGhRunner([])

        # Act and Assert
        with self.assertRaisesRegex(PostReviewCommentsError, "owner/repository"):
            post_review_comments(spec, runner=runner)
        self.assertEqual(runner.calls, [])

    def test_dry_run_validates_targets_without_invoking_runner(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        runner = FakeGhRunner([])

        # Act
        result = post_review_comments(spec, runner=runner, dry_run=True)

        # Assert
        self.assertEqual(
            result,
            [
                {"path": "src/Primary.kt", "line": 43, "body": "**[LOW-1] Finding**"},
                {
                    "path": "src/Companion.kt",
                    "line": 27,
                    "body": "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
                },
            ],
        )
        self.assertEqual(runner.calls, [])

    def test_mismatched_primary_response_stops_before_companion(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        runner = FakeGhRunner(
            [
                {
                    "id": 100,
                    "html_url": "https://github.com/owner/repo/pull/29#discussion_r100",
                    "body": "unexpected body",
                    "path": "src/Primary.kt",
                    "line": 43,
                }
            ]
        )

        # Act and Assert
        with self.assertRaisesRegex(PostReviewCommentsError, "primary response body"):
            post_review_comments(spec, runner=runner)
        self.assertEqual(len(runner.calls), 1)

    def test_mismatched_companion_response_stops_before_later_companion(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        spec["companions"].append(  # type: ignore[union-attr]
            {
                "path": "src/Later.kt",
                "line": 12,
                "body": "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
            }
        )
        primary_url = "https://github.com/owner/repo/pull/29#discussion_r100"
        runner = FakeGhRunner(
            [
                {
                    "id": 100,
                    "html_url": primary_url,
                    "body": "**[LOW-1] Finding**",
                    "path": "src/Primary.kt",
                    "line": 43,
                },
                {
                    "id": 101,
                    "html_url": "https://github.com/owner/repo/pull/29#discussion_r101",
                    "body": "unexpected body",
                    "path": "src/Companion.kt",
                    "line": 27,
                },
                {
                    "id": 102,
                    "html_url": "https://github.com/owner/repo/pull/29#discussion_r102",
                    "body": "unused",
                    "path": "src/Later.kt",
                    "line": 12,
                },
            ]
        )

        # Act and Assert
        with self.assertRaisesRegex(PostReviewCommentsError, "companion 0 response body") as error:
            post_review_comments(copy.deepcopy(spec), runner=runner)
        self.assertEqual(len(runner.calls), 2)
        self.assertIn(primary_url, str(error.exception))

    def test_cli_dry_run_reports_validated_targets(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = Path(temp_dir) / "comments.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            # Act
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--spec", str(spec_path), "--dry-run"],
                check=False,
                capture_output=True,
                text=True,
            )

        # Assert
        self.assertEqual(result.returncode, 0)
        self.assertIn("validated src/Primary.kt:43", result.stdout)
        self.assertIn("validated src/Companion.kt:27", result.stdout)

    def test_cli_rejects_unresolved_placeholder(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = Path(temp_dir) / "comments.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            # Act
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--spec", str(spec_path)],
                check=False,
                capture_output=True,
                text=True,
            )

        # Assert
        self.assertEqual(result.returncode, 1)
        self.assertIn("spec.primary.body contains unresolved marker", result.stderr)

    @patch("post_review_comments.subprocess.run")
    def test_gh_runner_uses_argument_list_without_shell(self, run_mock) -> None:
        # Arrange
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = '{"id": 100}'
        run_mock.return_value.stderr = ""
        args = ["gh", "api", "repos/owner/repo/pulls/29/comments"]

        # Act
        response = run_gh_api(args)

        # Assert
        self.assertEqual(response, {"id": 100})
        run_mock.assert_called_once_with(
            args,
            check=False,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    unittest.main()
