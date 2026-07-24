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

    def test_posts_companion_with_terminal_newline_and_preserves_body(self) -> None:
        # Arrange
        primary_body = "**[LOW-1] Finding**"
        primary_url = "https://github.com/owner/repo/pull/29#discussion_r100"
        companion_template = (
            "**[LOW-1] Finding**\n\n"
            "See primary comment: {primary_url}\n"
        )
        companion_body = companion_template.format(primary_url=primary_url)
        primary_response = {
            "id": 100,
            "html_url": primary_url,
            "body": primary_body,
            "path": "src/Primary.kt",
            "line": 43,
        }
        companion_response = {
            "id": 101,
            "html_url": "https://github.com/owner/repo/pull/29#discussion_r101",
            "body": companion_body,
            "path": "src/Companion.kt",
            "line": 27,
        }
        spec = valid_spec(primary_body, companion_template)
        runner = FakeGhRunner([primary_response, companion_response])

        # Act
        result = post_review_comments(spec, runner=runner)

        # Assert
        self.assertEqual(result, [primary_response, companion_response])
        companion_body_arg = runner.calls[1][runner.calls[1].index("-f") + 1]
        self.assertEqual(companion_body_arg, f"body={companion_body}")

    def test_rejects_content_after_companion_footer_before_mutation(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**",
            (
                "**[LOW-1] Finding**\n\n"
                "See primary comment: {primary_url}\n"
                "unexpected trailing content"
            ),
        )
        runner = FakeGhRunner([])

        # Act and Assert
        with self.assertRaisesRegex(PostReviewCommentsError, "must end with"):
            post_review_comments(spec, runner=runner)
        self.assertEqual(runner.calls, [])

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

    def test_dry_run_reports_multiline_target_range_without_invoking_runner(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        spec["primary"]["start_line"] = 40  # type: ignore[index]
        spec["companions"] = []
        runner = FakeGhRunner([])

        # Act
        result = post_review_comments(spec, runner=runner, dry_run=True)

        # Assert
        self.assertEqual(
            result,
            [
                {
                    "path": "src/Primary.kt",
                    "start_line": 40,
                    "line": 43,
                    "body": "**[LOW-1] Finding**",
                }
            ],
        )
        self.assertEqual(runner.calls, [])

    def test_posts_multiline_primary_with_range_arguments(self) -> None:
        # Arrange
        primary_body = "**[LOW-1] Finding**"
        primary_response = {
            "id": 100,
            "html_url": "https://github.com/owner/repo/pull/29#discussion_r100",
            "body": primary_body,
            "path": "src/Primary.kt",
            "start_line": 40,
            "start_side": "RIGHT",
            "line": 43,
            "side": "RIGHT",
        }
        spec = valid_spec(
            primary_body,
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        spec["primary"]["start_line"] = 40  # type: ignore[index]
        spec["companions"] = []
        runner = FakeGhRunner([primary_response])

        # Act
        result = post_review_comments(spec, runner=runner)

        # Assert
        self.assertEqual(result, [primary_response])
        self.assertIn("start_line=40", runner.calls[0])
        self.assertIn("start_side=RIGHT", runner.calls[0])
        self.assertIn("line=43", runner.calls[0])
        self.assertIn("side=RIGHT", runner.calls[0])

    def test_posts_multiline_companion_with_range_arguments(self) -> None:
        # Arrange
        primary_body = "**[LOW-1] Finding**"
        primary_url = "https://github.com/owner/repo/pull/29#discussion_r100"
        companion_template = (
            "**[LOW-1] Finding**\n\n"
            "Companion detail.\n\n"
            "See primary comment: {primary_url}"
        )
        primary_response = {
            "id": 100,
            "html_url": primary_url,
            "body": primary_body,
            "path": "src/Primary.kt",
            "line": 43,
        }
        companion_response = {
            "id": 101,
            "html_url": "https://github.com/owner/repo/pull/29#discussion_r101",
            "body": companion_template.format(primary_url=primary_url),
            "path": "src/Companion.kt",
            "start_line": 24,
            "start_side": "RIGHT",
            "line": 27,
            "side": "RIGHT",
        }
        spec = valid_spec(primary_body, companion_template)
        spec["companions"][0]["start_line"] = 24  # type: ignore[index]
        runner = FakeGhRunner([primary_response, companion_response])

        # Act
        result = post_review_comments(spec, runner=runner)

        # Assert
        self.assertEqual(result, [primary_response, companion_response])
        self.assertIn("start_line=24", runner.calls[1])
        self.assertIn("start_side=RIGHT", runner.calls[1])
        self.assertIn("line=27", runner.calls[1])
        self.assertIn("side=RIGHT", runner.calls[1])

    def test_rejects_invalid_multiline_start_line_before_mutation(self) -> None:
        for invalid_start_line in (True, 0, -1, "40", 40.5):
            with self.subTest(start_line=invalid_start_line):
                # Arrange
                spec = valid_spec(
                    "**[LOW-1] Finding**",
                    "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
                )
                spec["primary"]["start_line"] = invalid_start_line  # type: ignore[index]
                spec["companions"] = []
                runner = FakeGhRunner([])

                # Act and Assert
                with self.assertRaisesRegex(PostReviewCommentsError, "start_line"):
                    post_review_comments(spec, runner=runner)
                self.assertEqual(runner.calls, [])

    def test_rejects_multiline_start_line_at_or_after_end_line_before_mutation(self) -> None:
        for invalid_start_line in (43, 44):
            with self.subTest(start_line=invalid_start_line):
                # Arrange
                spec = valid_spec(
                    "**[LOW-1] Finding**",
                    "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
                )
                spec["primary"]["start_line"] = invalid_start_line  # type: ignore[index]
                spec["companions"] = []
                runner = FakeGhRunner([])

                # Act and Assert
                with self.assertRaisesRegex(PostReviewCommentsError, "less than"):
                    post_review_comments(spec, runner=runner)
                self.assertEqual(runner.calls, [])

    def test_mismatched_multiline_response_stops_and_reports_created_comment(self) -> None:
        # Arrange
        primary_url = "https://github.com/owner/repo/pull/29#discussion_r100"
        spec = valid_spec(
            "**[LOW-1] Finding**",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        spec["primary"]["start_line"] = 40  # type: ignore[index]
        spec["companions"] = []
        runner = FakeGhRunner(
            [
                {
                    "id": 100,
                    "html_url": primary_url,
                    "body": "**[LOW-1] Finding**",
                    "path": "src/Primary.kt",
                    "start_line": 41,
                    "start_side": "RIGHT",
                    "line": 43,
                    "side": "RIGHT",
                }
            ]
        )

        # Act and Assert
        with self.assertRaisesRegex(PostReviewCommentsError, "start_line") as error:
            post_review_comments(spec, runner=runner)
        self.assertIn(primary_url, str(error.exception))
        self.assertEqual(len(runner.calls), 1)

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

    def test_cli_dry_run_reports_multiline_target_range(self) -> None:
        # Arrange
        spec = valid_spec(
            "**[LOW-1] Finding**",
            "**[LOW-1] Finding**\n\nSee primary comment: {primary_url}",
        )
        spec["primary"]["start_line"] = 40  # type: ignore[index]
        spec["companions"] = []
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
        self.assertIn("validated src/Primary.kt:40-43", result.stdout)

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

    @patch("post_review_comments.subprocess.run")
    def test_gh_runner_preserves_stdout_and_stderr_on_failure(self, run_mock) -> None:
        # Arrange
        run_mock.return_value.returncode = 1
        run_mock.return_value.stdout = '{"message":"Validation Failed","errors":["invalid range"]}'
        run_mock.return_value.stderr = "gh: Validation Failed (HTTP 422)"
        args = ["gh", "api", "repos/owner/repo/pulls/29/comments"]

        # Act and Assert
        with self.assertRaises(PostReviewCommentsError) as error:
            run_gh_api(args)
        self.assertIn("gh: Validation Failed (HTTP 422)", str(error.exception))
        self.assertIn('"errors":["invalid range"]', str(error.exception))


if __name__ == "__main__":
    unittest.main()
