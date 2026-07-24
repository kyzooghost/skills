#!/usr/bin/env python3
"""Audit or add missing linked-PR status comments on labeled GitHub issues."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence


OPEN_STATUS = "open"
MERGED_STATUS = "merged"
OPEN_STATE = "OPEN"
CLOSED_STATE = "CLOSED"
MERGED_STATE = "MERGED"
COMMENT_HEADER = "For visibility, this issue has linked PR activity:"


class SyncPrStatusCommentsError(ValueError):
    """Raised when GitHub data or a synchronization result cannot be trusted."""


@dataclass(frozen=True)
class LinkedPullRequest:
    repository: str
    number: int
    url: str


@dataclass(frozen=True)
class PullRequestStatus:
    repository: str
    number: int
    url: str
    state: str
    merged_at: str | None
    is_draft: bool


@dataclass(frozen=True)
class StatusEntry:
    pull_request: PullRequestStatus
    status: str


@dataclass(frozen=True)
class IssueCommentPlan:
    issue_number: int
    entries: tuple[StatusEntry, ...]
    body: str


def normalize_status(pull_request: PullRequestStatus) -> str | None:
    if pull_request.merged_at is not None:
        return MERGED_STATUS
    if pull_request.state == MERGED_STATE:
        raise SyncPrStatusCommentsError(
            f"pull request #{pull_request.number} is merged but missing mergedAt"
        )
    if pull_request.state == OPEN_STATE:
        return OPEN_STATUS
    if pull_request.state == CLOSED_STATE:
        return None
    raise SyncPrStatusCommentsError(
        f"pull request #{pull_request.number} has unsupported state "
        f"{pull_request.state}"
    )


def _line_mentions_pull_request(
    line: str,
    pull_request: PullRequestStatus,
    issue_repo: str,
) -> bool:
    normalized_line = line.casefold()
    url_pattern = re.compile(
        re.escape(pull_request.url.casefold()) + r"(?!\d)"
    )
    if url_pattern.search(normalized_line):
        return True

    qualified_pattern = re.compile(
        rf"(?<![\w./-]){re.escape(pull_request.repository.casefold())}"
        rf"#{pull_request.number}(?!\d)"
    )
    if qualified_pattern.search(normalized_line):
        return True

    if issue_repo.casefold() != pull_request.repository.casefold():
        return False
    same_repo_pattern = re.compile(
        rf"(?<!\w)pr\s+#{pull_request.number}(?!\d)",
        re.IGNORECASE,
    )
    return same_repo_pattern.search(line) is not None


def _line_states_status(line: str, status: str) -> bool:
    if status == OPEN_STATUS:
        return re.search(r"(?<!\w)open(?!\w)", line, re.IGNORECASE) is not None
    if status == MERGED_STATUS:
        return re.search(r"(?<!\w)merged(?!\w)", line, re.IGNORECASE) is not None
    raise SyncPrStatusCommentsError(f"unsupported PR status: {status}")


def _comment_covers(
    comment: str,
    pull_request: PullRequestStatus,
    status: str,
    issue_repo: str,
) -> bool:
    return any(
        _line_mentions_pull_request(line, pull_request, issue_repo)
        and _line_states_status(line, status)
        for line in comment.splitlines()
    )


def uncovered_entries(
    comments: Sequence[str],
    pull_requests: Sequence[PullRequestStatus],
    issue_repo: str,
) -> tuple[StatusEntry, ...]:
    deduplicated: dict[tuple[str, int], PullRequestStatus] = {}
    for pull_request in pull_requests:
        key = (pull_request.repository.casefold(), pull_request.number)
        deduplicated[key] = pull_request

    entries: list[StatusEntry] = []
    for pull_request in sorted(
        deduplicated.values(),
        key=lambda item: (item.repository.casefold(), item.number),
    ):
        status = normalize_status(pull_request)
        if status is None:
            continue
        if any(
            _comment_covers(comment, pull_request, status, issue_repo)
            for comment in comments
        ):
            continue
        entries.append(StatusEntry(pull_request=pull_request, status=status))
    return tuple(entries)


def _comment_body(entries: Sequence[StatusEntry]) -> str:
    lines = [COMMENT_HEADER, ""]
    lines.extend(
        f"- {entry.pull_request.url} - {entry.status}"
        for entry in entries
    )
    return "\n".join(lines)


def plan_issue_comment(
    issue_number: int,
    comments: Sequence[str],
    pull_requests: Sequence[PullRequestStatus],
    issue_repo: str,
) -> IssueCommentPlan | None:
    entries = uncovered_entries(comments, pull_requests, issue_repo)
    if not entries:
        return None
    return IssueCommentPlan(
        issue_number=issue_number,
        entries=entries,
        body=_comment_body(entries),
    )
