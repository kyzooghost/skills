from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "scoped-tickets" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from sync_pr_status_comments import (  # noqa: E402
    COMMENT_HEADER,
    MERGED_STATUS,
    OPEN_STATUS,
    PullRequestStatus,
    StatusEntry,
    SyncPrStatusCommentsError,
    normalize_status,
    plan_issue_comment,
    uncovered_entries,
)


def pull_request(
    *,
    repository: str = "pr-owner/pr-repo",
    number: int = 17,
    state: str = "OPEN",
    merged_at: str | None = None,
    is_draft: bool = False,
) -> PullRequestStatus:
    return PullRequestStatus(
        repository=repository,
        number=number,
        url=f"https://github.com/{repository}/pull/{number}",
        state=state,
        merged_at=merged_at,
        is_draft=is_draft,
    )


class NormalizeStatusTest(unittest.TestCase):
    def test_open_pull_request_has_open_status(self) -> None:
        # Arrange
        candidate = pull_request(state="OPEN")

        # Act
        result = normalize_status(candidate)

        # Assert
        self.assertEqual(result, OPEN_STATUS)

    def test_draft_pull_request_has_open_status(self) -> None:
        # Arrange
        candidate = pull_request(state="OPEN", is_draft=True)

        # Act
        result = normalize_status(candidate)

        # Assert
        self.assertEqual(result, OPEN_STATUS)

    def test_merged_pull_request_has_merged_status(self) -> None:
        # Arrange
        candidate = pull_request(state="MERGED", merged_at="2026-07-10T10:45:21Z")

        # Act
        result = normalize_status(candidate)

        # Assert
        self.assertEqual(result, MERGED_STATUS)

    def test_closed_unmerged_pull_request_has_no_status(self) -> None:
        # Arrange
        candidate = pull_request(state="CLOSED", merged_at=None)

        # Act
        result = normalize_status(candidate)

        # Assert
        self.assertIsNone(result)

    def test_merged_state_without_timestamp_fails(self) -> None:
        # Arrange
        candidate = pull_request(state="MERGED", merged_at=None)

        # Act and Assert
        with self.assertRaisesRegex(
            SyncPrStatusCommentsError,
            "missing mergedAt",
        ):
            normalize_status(candidate)


class CommentCoverageTest(unittest.TestCase):
    def test_full_url_with_current_status_covers_pull_request(self) -> None:
        # Arrange
        candidate = pull_request()
        comments = (f"{candidate.url} - open",)

        # Act
        result = uncovered_entries(comments, (candidate,), "issue-owner/issues")

        # Assert
        self.assertEqual(result, ())

    def test_qualified_cross_repository_reference_with_status_covers_pull_request(self) -> None:
        # Arrange
        candidate = pull_request()
        comments = ("pr-owner/pr-repo#17 is open",)

        # Act
        result = uncovered_entries(comments, (candidate,), "issue-owner/issues")

        # Assert
        self.assertEqual(result, ())

    def test_same_repository_pr_reference_with_status_covers_pull_request(self) -> None:
        # Arrange
        candidate = pull_request(repository="owner/repo")
        comments = ("PR #17 is open",)

        # Act
        result = uncovered_entries(comments, (candidate,), "owner/repo")

        # Assert
        self.assertEqual(result, ())

    def test_bare_pull_request_url_does_not_cover_status(self) -> None:
        # Arrange
        candidate = pull_request()
        comments = (candidate.url,)

        # Act
        result = uncovered_entries(comments, (candidate,), "issue-owner/issues")

        # Assert
        self.assertEqual(
            result,
            (StatusEntry(pull_request=candidate, status=OPEN_STATUS),),
        )

    def test_longer_pull_number_url_does_not_cover_shorter_pull_request(self) -> None:
        # Arrange
        candidate = pull_request(number=17)
        other_url = "https://github.com/pr-owner/pr-repo/pull/170"
        comments = (f"{other_url} - open",)

        # Act
        result = uncovered_entries(comments, (candidate,), "issue-owner/issues")

        # Assert
        self.assertEqual(
            result,
            (StatusEntry(pull_request=candidate, status=OPEN_STATUS),),
        )

    def test_open_comment_does_not_cover_merged_status(self) -> None:
        # Arrange
        candidate = pull_request(state="MERGED", merged_at="2026-07-10T10:45:21Z")
        comments = (f"{candidate.url} - open",)

        # Act
        result = uncovered_entries(comments, (candidate,), "issue-owner/issues")

        # Assert
        self.assertEqual(
            result,
            (StatusEntry(pull_request=candidate, status=MERGED_STATUS),),
        )

    def test_closed_merged_wording_covers_merged_status(self) -> None:
        # Arrange
        candidate = pull_request(state="MERGED", merged_at="2026-07-10T10:45:21Z")
        comments = (f"{candidate.url} - closed (merged)",)

        # Act
        result = uncovered_entries(comments, (candidate,), "issue-owner/issues")

        # Assert
        self.assertEqual(result, ())

    def test_closed_unmerged_pull_request_is_not_planned(self) -> None:
        # Arrange
        candidate = pull_request(state="CLOSED")

        # Act
        result = plan_issue_comment(44, (), (candidate,), "issue-owner/issues")

        # Assert
        self.assertIsNone(result)

    def test_multiple_uncovered_pull_requests_share_one_comment(self) -> None:
        # Arrange
        open_pr = pull_request(number=17)
        merged_pr = pull_request(
            number=18,
            state="MERGED",
            merged_at="2026-07-11T10:45:21Z",
        )

        # Act
        result = plan_issue_comment(
            44,
            (),
            (merged_pr, open_pr),
            "issue-owner/issues",
        )

        # Assert
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.issue_number, 44)
        self.assertEqual(
            result.body,
            (
                f"{COMMENT_HEADER}\n\n"
                f"- {open_pr.url} - open\n"
                f"- {merged_pr.url} - merged"
            ),
        )
