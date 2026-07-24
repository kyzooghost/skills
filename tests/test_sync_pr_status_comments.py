from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "scoped-tickets" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sync_pr_status_comments as sync_pr_status_comments_module  # noqa: E402
from sync_pr_status_comments import (  # noqa: E402
    AuditReport,
    COMMENT_HEADER,
    COMMENTS_PLANNED_FIELD,
    GhClient,
    IssueCommentPlan,
    IssueSnapshot,
    LinkedPullRequest,
    MERGED_STATUS,
    MODE_APPLY,
    MODE_DRY_RUN,
    OPEN_STATUS,
    POSTED_PREFIX,
    PullRequestStatus,
    StatusEntry,
    SyncPrStatusCommentsError,
    VERIFICATION_PASSED_LINE,
    audit_repository,
    format_audit_report,
    main,
    normalize_status,
    plan_issue_comment,
    synchronize,
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


class FakeGhRunner:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> dict[str, object]:
        self.calls.append(args)
        if not self.responses:
            raise AssertionError(f"unexpected gh call: {args}")
        return self.responses.pop(0)


class GhClientTest(unittest.TestCase):
    def test_lists_every_labeled_issue_page(self) -> None:
        # Arrange
        runner = FakeGhRunner(
            [
                {
                    "data": {
                        "repository": {
                            "issues": {
                                "nodes": [{"number": 10}],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": "issue-cursor",
                                },
                            }
                        }
                    }
                },
                {
                    "data": {
                        "repository": {
                            "issues": {
                                "nodes": [{"number": 11}],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            }
                        }
                    }
                },
            ]
        )
        client = GhClient("issue-owner/issues", "pr-owner/prs", runner=runner)

        # Act
        result = client.list_labeled_issue_numbers("demo")

        # Assert
        self.assertEqual(result, (10, 11))
        self.assertIn("after=issue-cursor", runner.calls[1])
        self.assertIn("states: [OPEN, CLOSED]", " ".join(runner.calls[0]))

    def test_snapshot_returns_unique_target_repository_pull_requests(self) -> None:
        # Arrange
        target = {
            "__typename": "PullRequest",
            "number": 17,
            "url": "https://github.com/pr-owner/prs/pull/17",
            "repository": {"nameWithOwner": "pr-owner/prs"},
        }
        runner = FakeGhRunner(
            [
                {
                    "data": {
                        "repository": {
                            "issue": {
                                "comments": {
                                    "nodes": [{"body": "existing comment"}],
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                }
                            }
                        }
                    }
                },
                {
                    "data": {
                        "repository": {
                            "issue": {
                                "timelineItems": {
                                    "nodes": [
                                        {
                                            "__typename": "CrossReferencedEvent",
                                            "source": target,
                                        },
                                        {
                                            "__typename": "ConnectedEvent",
                                            "subject": target,
                                        },
                                        {
                                            "__typename": "CrossReferencedEvent",
                                            "source": {
                                                "__typename": "PullRequest",
                                                "number": 18,
                                                "url": "https://github.com/other/prs/pull/18",
                                                "repository": {
                                                    "nameWithOwner": "other/prs"
                                                },
                                            },
                                        },
                                        {
                                            "__typename": "CrossReferencedEvent",
                                            "source": {"__typename": "Issue"},
                                        },
                                    ],
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                }
                            }
                        }
                    }
                },
            ]
        )
        client = GhClient("issue-owner/issues", "pr-owner/prs", runner=runner)

        # Act
        result = client.get_issue_snapshot(44)

        # Assert
        self.assertEqual(
            result,
            IssueSnapshot(
                number=44,
                comments=("existing comment",),
                linked_pull_requests=(
                    LinkedPullRequest(
                        repository="pr-owner/prs",
                        number=17,
                        url="https://github.com/pr-owner/prs/pull/17",
                    ),
                ),
            ),
        )

    def test_snapshot_paginates_comments(self) -> None:
        # Arrange
        runner = FakeGhRunner(
            [
                {
                    "data": {
                        "repository": {
                            "issue": {
                                "comments": {
                                    "nodes": [{"body": "first"}],
                                    "pageInfo": {
                                        "hasNextPage": True,
                                        "endCursor": "comment-cursor",
                                    },
                                }
                            }
                        }
                    }
                },
                {
                    "data": {
                        "repository": {
                            "issue": {
                                "comments": {
                                    "nodes": [{"body": "second"}],
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                }
                            }
                        }
                    }
                },
                {
                    "data": {
                        "repository": {
                            "issue": {
                                "timelineItems": {
                                    "nodes": [],
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                }
                            }
                        }
                    }
                },
            ]
        )
        client = GhClient("issue-owner/issues", "pr-owner/prs", runner=runner)

        # Act
        result = client.get_issue_snapshot(44)

        # Assert
        self.assertEqual(result.comments, ("first", "second"))
        self.assertIn("after=comment-cursor", runner.calls[1])

    def test_snapshot_paginates_timeline_items(self) -> None:
        # Arrange
        first = {
            "__typename": "PullRequest",
            "number": 17,
            "url": "https://github.com/pr-owner/prs/pull/17",
            "repository": {"nameWithOwner": "pr-owner/prs"},
        }
        second = {
            "__typename": "PullRequest",
            "number": 18,
            "url": "https://github.com/pr-owner/prs/pull/18",
            "repository": {"nameWithOwner": "pr-owner/prs"},
        }
        runner = FakeGhRunner(
            [
                {
                    "data": {
                        "repository": {
                            "issue": {
                                "comments": {
                                    "nodes": [],
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                }
                            }
                        }
                    }
                },
                {
                    "data": {
                        "repository": {
                            "issue": {
                                "timelineItems": {
                                    "nodes": [
                                        {
                                            "__typename": "CrossReferencedEvent",
                                            "source": first,
                                        }
                                    ],
                                    "pageInfo": {
                                        "hasNextPage": True,
                                        "endCursor": "timeline-cursor",
                                    },
                                }
                            }
                        }
                    }
                },
                {
                    "data": {
                        "repository": {
                            "issue": {
                                "timelineItems": {
                                    "nodes": [
                                        {
                                            "__typename": "CrossReferencedEvent",
                                            "source": second,
                                        }
                                    ],
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                }
                            }
                        }
                    }
                },
            ]
        )
        client = GhClient("issue-owner/issues", "pr-owner/prs", runner=runner)

        # Act
        result = client.get_issue_snapshot(44)

        # Assert
        self.assertEqual(
            tuple(item.number for item in result.linked_pull_requests),
            (17, 18),
        )
        self.assertIn("after=timeline-cursor", runner.calls[2])

    def test_pull_request_status_is_read_from_pr_repository(self) -> None:
        # Arrange
        runner = FakeGhRunner(
            [
                {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "number": 17,
                                "url": "https://github.com/pr-owner/prs/pull/17",
                                "state": "OPEN",
                                "mergedAt": None,
                                "isDraft": False,
                                "repository": {"nameWithOwner": "pr-owner/prs"},
                            }
                        }
                    }
                }
            ]
        )
        client = GhClient("issue-owner/issues", "pr-owner/prs", runner=runner)

        # Act
        result = client.get_pull_request(17)

        # Assert
        self.assertEqual(result, pull_request(repository="pr-owner/prs"))
        self.assertIn("owner=pr-owner", runner.calls[0])
        self.assertIn("name=prs", runner.calls[0])

    def test_label_recheck_reads_issue_repository(self) -> None:
        # Arrange
        runner = FakeGhRunner([{"labels": [{"name": "demo"}]}])
        client = GhClient("issue-owner/issues", "pr-owner/prs", runner=runner)

        # Act
        result = client.issue_has_label(44, "demo")

        # Assert
        self.assertTrue(result)
        self.assertEqual(
            runner.calls[0],
            ["gh", "api", "repos/issue-owner/issues/issues/44"],
        )

    def test_comment_is_posted_only_to_issue_repository(self) -> None:
        # Arrange
        body = "status body"
        runner = FakeGhRunner(
            [
                {
                    "body": body,
                    "html_url": (
                        "https://github.com/issue-owner/issues/"
                        "issues/44#issuecomment-100"
                    ),
                }
            ]
        )
        client = GhClient("issue-owner/issues", "pr-owner/prs", runner=runner)

        # Act
        result = client.add_issue_comment(44, body)

        # Assert
        self.assertEqual(
            result,
            "https://github.com/issue-owner/issues/issues/44#issuecomment-100",
        )
        self.assertEqual(
            runner.calls[0][:3],
            ["gh", "api", "repos/issue-owner/issues/issues/44/comments"],
        )
        self.assertIn(f"body={body}", runner.calls[0])


class FakeSyncClient:
    def __init__(
        self,
        *,
        pull_request_states: list[PullRequestStatus],
        cover_on_second_snapshot: bool = False,
        unlink_on_second_snapshot: bool = False,
        has_label: bool = True,
    ) -> None:
        self.issue_repo = "issue-owner/issues"
        self.pr_repo = "pr-owner/pr-repo"
        self._pull_request_states = list(pull_request_states)
        self._cover_on_second_snapshot = cover_on_second_snapshot
        self._unlink_on_second_snapshot = unlink_on_second_snapshot
        self._has_label = has_label
        self._inventory_calls = 0
        self._snapshot_calls = 0
        self.comments: list[str] = []
        self.posted: list[tuple[int, str]] = []

    def list_labeled_issue_numbers(self, issue_tag: str) -> tuple[int, ...]:
        if issue_tag != "demo":
            raise AssertionError(issue_tag)
        self._inventory_calls += 1
        if not self._has_label and self._inventory_calls > 1:
            return ()
        return (44,)

    def get_issue_snapshot(self, issue_number: int) -> IssueSnapshot:
        if issue_number != 44:
            raise AssertionError(issue_number)
        self._snapshot_calls += 1
        comments = list(self.comments)
        if self._cover_on_second_snapshot and self._snapshot_calls >= 2:
            comments.append(
                "https://github.com/pr-owner/pr-repo/pull/17 - open"
            )
        linked_pull_requests = (
            ()
            if self._unlink_on_second_snapshot and self._snapshot_calls >= 2
            else (
                LinkedPullRequest(
                    repository="pr-owner/pr-repo",
                    number=17,
                    url="https://github.com/pr-owner/pr-repo/pull/17",
                ),
            )
        )
        return IssueSnapshot(
            number=44,
            comments=tuple(comments),
            linked_pull_requests=linked_pull_requests,
        )

    def get_pull_request(self, number: int) -> PullRequestStatus:
        if number != 17:
            raise AssertionError(number)
        if len(self._pull_request_states) > 1:
            return self._pull_request_states.pop(0)
        return self._pull_request_states[0]

    def issue_has_label(self, issue_number: int, issue_tag: str) -> bool:
        return self._has_label and issue_number == 44 and issue_tag == "demo"

    def add_issue_comment(self, issue_number: int, body: str) -> str:
        self.posted.append((issue_number, body))
        self.comments.append(body)
        return (
            "https://github.com/issue-owner/issues/"
            "issues/44#issuecomment-100"
        )


class FakeRepositoryClient:
    def __init__(
        self,
        *,
        issue_numbers: tuple[int, ...],
        snapshots: dict[int, IssueSnapshot],
        pull_requests: dict[int, PullRequestStatus],
        issue_repo: str = "issue-owner/issues",
        pr_repo: str = "pr-owner/pr-repo",
        labels: dict[int, set[str]] | None = None,
    ) -> None:
        self.issue_repo = issue_repo
        self.pr_repo = pr_repo
        self._issue_numbers = issue_numbers
        self._pull_requests = dict(pull_requests)
        self._comments = {
            issue_number: list(snapshot.comments)
            for issue_number, snapshot in snapshots.items()
        }
        self._linked_pull_requests = {
            issue_number: snapshot.linked_pull_requests
            for issue_number, snapshot in snapshots.items()
        }
        self._labels = labels or {
            issue_number: {"demo"} for issue_number in issue_numbers
        }
        self.posted: list[tuple[int, str]] = []

    def list_labeled_issue_numbers(self, issue_tag: str) -> tuple[int, ...]:
        if issue_tag != "demo":
            raise AssertionError(issue_tag)
        return tuple(
            issue_number
            for issue_number in self._issue_numbers
            if issue_tag in self._labels.get(issue_number, set())
        )

    def get_issue_snapshot(self, issue_number: int) -> IssueSnapshot:
        return IssueSnapshot(
            number=issue_number,
            comments=tuple(self._comments[issue_number]),
            linked_pull_requests=self._linked_pull_requests[issue_number],
        )

    def get_pull_request(self, number: int) -> PullRequestStatus:
        return self._pull_requests[number]

    def issue_has_label(self, issue_number: int, issue_tag: str) -> bool:
        return issue_tag in self._labels.get(issue_number, set())

    def add_issue_comment(self, issue_number: int, body: str) -> str:
        self.posted.append((issue_number, body))
        self._comments[issue_number].append(body)
        return (
            "https://github.com/issue-owner/issues/"
            f"issues/{issue_number}#issuecomment-100"
        )


class FakeMainGhClient(FakeRepositoryClient):
    configured_issue_numbers: tuple[int, ...] = ()
    configured_snapshots: dict[int, IssueSnapshot] = {}
    configured_pull_requests: dict[int, PullRequestStatus] = {}
    configured_labels: dict[int, set[str]] = {}
    last_instance: FakeMainGhClient | None = None

    @classmethod
    def configure(
        cls,
        *,
        issue_numbers: tuple[int, ...],
        snapshots: dict[int, IssueSnapshot],
        pull_requests: dict[int, PullRequestStatus],
        labels: dict[int, set[str]] | None = None,
    ) -> None:
        cls.configured_issue_numbers = issue_numbers
        cls.configured_snapshots = snapshots
        cls.configured_pull_requests = pull_requests
        cls.configured_labels = labels or {
            issue_number: {"demo"} for issue_number in issue_numbers
        }
        cls.last_instance = None

    def __init__(self, issue_repo: str, pr_repo: str) -> None:
        super().__init__(
            issue_numbers=self.configured_issue_numbers,
            snapshots=self.configured_snapshots,
            pull_requests=self.configured_pull_requests,
            issue_repo=issue_repo,
            pr_repo=pr_repo,
            labels=self.configured_labels,
        )
        type(self).last_instance = self


class AuditRepositoryTest(unittest.TestCase):
    def test_mixed_inventory_counts_statuses_and_grouped_plans(self) -> None:
        # Arrange
        covered_merged = pull_request(
            number=18,
            state="MERGED",
            merged_at="2026-07-24T10:45:21Z",
        )
        covered_open = pull_request(number=19)
        client = FakeRepositoryClient(
            issue_numbers=(44, 45),
            snapshots={
                44: IssueSnapshot(
                    number=44,
                    comments=(f"{covered_merged.url} - merged",),
                    linked_pull_requests=(
                        LinkedPullRequest(
                            repository="pr-owner/pr-repo",
                            number=17,
                            url="https://github.com/pr-owner/pr-repo/pull/17",
                        ),
                        LinkedPullRequest(
                            repository="pr-owner/pr-repo",
                            number=18,
                            url=covered_merged.url,
                        ),
                    ),
                ),
                45: IssueSnapshot(
                    number=45,
                    comments=("pr-owner/pr-repo#19 is open",),
                    linked_pull_requests=(
                        LinkedPullRequest(
                            repository="pr-owner/pr-repo",
                            number=19,
                            url=covered_open.url,
                        ),
                        LinkedPullRequest(
                            repository="pr-owner/pr-repo",
                            number=20,
                            url="https://github.com/pr-owner/pr-repo/pull/20",
                        ),
                    ),
                ),
            },
            pull_requests={
                17: pull_request(number=17),
                18: covered_merged,
                19: covered_open,
                20: pull_request(number=20, state="CLOSED"),
            },
        )

        # Act
        result = audit_repository(client, "demo")

        # Assert
        self.assertEqual(result.issues_inspected, 2)
        self.assertEqual(result.linked_pull_requests, 4)
        self.assertEqual(result.eligible_open, 2)
        self.assertEqual(result.eligible_merged, 1)
        self.assertEqual(result.already_covered, 2)
        self.assertEqual(result.ignored_closed_unmerged, 1)
        self.assertEqual(
            result.plans,
            (
                IssueCommentPlan(
                    issue_number=44,
                    entries=(
                        StatusEntry(
                            pull_request=pull_request(number=17),
                            status=OPEN_STATUS,
                        ),
                    ),
                    body=(
                        f"{COMMENT_HEADER}\n\n"
                        "- https://github.com/pr-owner/pr-repo/pull/17 - open"
                    ),
                ),
            ),
        )


class SynchronizationTest(unittest.TestCase):
    def test_dry_run_reports_missing_status_without_mutation(self) -> None:
        # Arrange
        client = FakeSyncClient(pull_request_states=[pull_request()])

        # Act
        result = synchronize(client, "demo", apply=False)

        # Assert
        self.assertEqual(len(result.initial.plans), 1)
        self.assertEqual(result.posted_urls, ())
        self.assertEqual(client.posted, [])

    def test_apply_skips_status_covered_during_recheck(self) -> None:
        # Arrange
        client = FakeSyncClient(
            pull_request_states=[pull_request()],
            cover_on_second_snapshot=True,
        )

        # Act
        result = synchronize(client, "demo", apply=True)

        # Assert
        self.assertEqual(result.posted_urls, ())
        self.assertEqual(client.posted, [])
        self.assertEqual(result.verification.plans, ())

    def test_apply_skips_issue_after_label_removal(self) -> None:
        # Arrange
        client = FakeSyncClient(
            pull_request_states=[pull_request()],
            has_label=False,
        )

        # Act
        result = synchronize(client, "demo", apply=True)

        # Assert
        self.assertEqual(result.posted_urls, ())
        self.assertEqual(client.posted, [])

    def test_apply_skips_removed_pr_relationship(self) -> None:
        # Arrange
        client = FakeSyncClient(
            pull_request_states=[pull_request()],
            unlink_on_second_snapshot=True,
        )

        # Act
        result = synchronize(client, "demo", apply=True)

        # Assert
        self.assertEqual(result.posted_urls, ())
        self.assertEqual(client.posted, [])
        self.assertEqual(result.verification.plans, ())

    def test_apply_posts_grouped_comment_with_verified_coverage(self) -> None:
        # Arrange
        client = FakeSyncClient(pull_request_states=[pull_request()])

        # Act
        result = synchronize(client, "demo", apply=True)

        # Assert
        self.assertEqual(
            result.posted_urls,
            (
                "https://github.com/issue-owner/issues/"
                "issues/44#issuecomment-100",
            ),
        )
        self.assertEqual(len(client.posted), 1)
        self.assertEqual(result.verification.plans, ())

    def test_apply_skips_pr_that_closes_without_merge_before_post(self) -> None:
        # Arrange
        client = FakeSyncClient(
            pull_request_states=[
                pull_request(),
                pull_request(state="CLOSED"),
            ]
        )

        # Act
        result = synchronize(client, "demo", apply=True)

        # Assert
        self.assertEqual(result.posted_urls, ())
        self.assertEqual(client.posted, [])
        self.assertEqual(result.verification.ignored_closed_unmerged, 1)

    def test_verification_names_status_that_changed_after_post(self) -> None:
        # Arrange
        client = FakeSyncClient(
            pull_request_states=[
                pull_request(),
                pull_request(),
                pull_request(
                    state="MERGED",
                    merged_at="2026-07-24T10:45:21Z",
                ),
            ]
        )

        # Act and Assert
        with self.assertRaisesRegex(
            SyncPrStatusCommentsError,
            r"issue #44.*pull/17.*merged",
        ):
            synchronize(client, "demo", apply=True)


class AuditOutputTest(unittest.TestCase):
    def test_report_includes_counts_for_grouped_plans(self) -> None:
        # Arrange
        candidate = pull_request()
        report = AuditReport(
            issues_inspected=2,
            linked_pull_requests=3,
            eligible_open=1,
            eligible_merged=1,
            already_covered=1,
            ignored_closed_unmerged=1,
            plans=(
                IssueCommentPlan(
                    issue_number=44,
                    entries=(
                        StatusEntry(
                            pull_request=candidate,
                            status=OPEN_STATUS,
                        ),
                    ),
                    body=f"{COMMENT_HEADER}\n\n- {candidate.url} - open",
                ),
            ),
        )

        # Act
        result = format_audit_report(report, apply=False)

        # Assert
        self.assertEqual(
            result,
            (
                f"mode={MODE_DRY_RUN}\n"
                "issues_inspected=2\n"
                "linked_pull_requests=3\n"
                "eligible_open=1\n"
                "eligible_merged=1\n"
                "already_covered=1\n"
                "ignored_closed_unmerged=1\n"
                f"{COMMENTS_PLANNED_FIELD}=1\n"
                f"issue #44: {candidate.url} - open"
            ),
        )


class MainTest(unittest.TestCase):
    def test_main_requires_issue_repo_pr_repo_and_issue_tag(self) -> None:
        # Arrange
        stderr = io.StringIO()

        # Act and Assert
        with self.assertRaises(SystemExit) as error:
            with redirect_stderr(stderr):
                main([])
        self.assertEqual(error.exception.code, 2)
        self.assertIn("--issue-repo", stderr.getvalue())
        self.assertIn("--pr-repo", stderr.getvalue())
        self.assertIn("--issue-tag", stderr.getvalue())

    def test_main_defaults_to_dry_run_without_mutation(self) -> None:
        # Arrange
        FakeMainGhClient.configure(
            issue_numbers=(44,),
            snapshots={
                44: IssueSnapshot(
                    number=44,
                    comments=(),
                    linked_pull_requests=(
                        LinkedPullRequest(
                            repository="pr-owner/pr-repo",
                            number=17,
                            url="https://github.com/pr-owner/pr-repo/pull/17",
                        ),
                    ),
                ),
            },
            pull_requests={17: pull_request()},
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        # Act
        with patch("sync_pr_status_comments.GhClient", FakeMainGhClient):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(
                    [
                        "--issue-repo",
                        "issue-owner/issues",
                        "--pr-repo",
                        "pr-owner/pr-repo",
                        "--issue-tag",
                        "demo",
                    ]
                )

        # Assert
        self.assertEqual(result, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn(f"mode={MODE_DRY_RUN}", stdout.getvalue())
        self.assertNotIn(POSTED_PREFIX, stdout.getvalue())
        self.assertNotIn(VERIFICATION_PASSED_LINE, stdout.getvalue())
        self.assertIsNotNone(FakeMainGhClient.last_instance)
        assert FakeMainGhClient.last_instance is not None
        self.assertEqual(FakeMainGhClient.last_instance.posted, [])

    def test_main_selects_mutation_only_with_apply(self) -> None:
        # Arrange
        FakeMainGhClient.configure(
            issue_numbers=(44,),
            snapshots={
                44: IssueSnapshot(
                    number=44,
                    comments=(),
                    linked_pull_requests=(
                        LinkedPullRequest(
                            repository="pr-owner/pr-repo",
                            number=17,
                            url="https://github.com/pr-owner/pr-repo/pull/17",
                        ),
                    ),
                ),
            },
            pull_requests={17: pull_request()},
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        # Act
        with patch("sync_pr_status_comments.GhClient", FakeMainGhClient):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(
                    [
                        "--issue-repo",
                        "issue-owner/issues",
                        "--pr-repo",
                        "pr-owner/pr-repo",
                        "--issue-tag",
                        "demo",
                        "--apply",
                    ]
                )

        # Assert
        self.assertEqual(result, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn(f"mode={MODE_APPLY}", stdout.getvalue())
        self.assertIn(POSTED_PREFIX, stdout.getvalue())
        self.assertIn(VERIFICATION_PASSED_LINE, stdout.getvalue())
        self.assertIsNotNone(FakeMainGhClient.last_instance)
        assert FakeMainGhClient.last_instance is not None
        self.assertEqual(len(FakeMainGhClient.last_instance.posted), 1)

    def test_main_returns_non_zero_for_sync_error(self) -> None:
        # Arrange
        FakeMainGhClient.configure(
            issue_numbers=(44,),
            snapshots={
                44: IssueSnapshot(
                    number=44,
                    comments=(),
                    linked_pull_requests=(
                        LinkedPullRequest(
                            repository="pr-owner/pr-repo",
                            number=17,
                            url="https://github.com/pr-owner/pr-repo/pull/17",
                        ),
                    ),
                ),
            },
            pull_requests={
                17: pull_request(state="MERGED", merged_at=None),
            },
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        # Act
        with patch("sync_pr_status_comments.GhClient", FakeMainGhClient):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(
                    [
                        "--issue-repo",
                        "issue-owner/issues",
                        "--pr-repo",
                        "pr-owner/pr-repo",
                        "--issue-tag",
                        "demo",
                    ]
                )

        # Assert
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("missing mergedAt", stderr.getvalue())
