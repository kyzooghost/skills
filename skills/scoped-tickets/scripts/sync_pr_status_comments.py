#!/usr/bin/env python3
"""Audit or add missing linked-PR status comments on labeled GitHub issues."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Sequence


OPEN_STATUS = "open"
MERGED_STATUS = "merged"
OPEN_STATE = "OPEN"
CLOSED_STATE = "CLOSED"
MERGED_STATE = "MERGED"
COMMENT_HEADER = "For visibility, this issue has linked PR activity:"

PULL_REQUEST_TYPENAME = "PullRequest"
CROSS_REFERENCED_EVENT = "CrossReferencedEvent"
CONNECTED_EVENT = "ConnectedEvent"

ISSUES_QUERY = """
query(
  $owner: String!,
  $name: String!,
  $label: String!,
  $after: String
) {
  repository(owner: $owner, name: $name) {
    issues(
      first: 100,
      after: $after,
      labels: [$label],
      states: [OPEN, CLOSED],
      orderBy: {field: CREATED_AT, direction: ASC}
    ) {
      nodes { number }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

COMMENTS_QUERY = """
query(
  $owner: String!,
  $name: String!,
  $number: Int!,
  $after: String
) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      comments(first: 100, after: $after) {
        nodes { body }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""

TIMELINE_QUERY = """
query(
  $owner: String!,
  $name: String!,
  $number: Int!,
  $after: String
) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      timelineItems(
        first: 100,
        after: $after,
        itemTypes: [CROSS_REFERENCED_EVENT, CONNECTED_EVENT]
      ) {
        nodes {
          __typename
          ... on CrossReferencedEvent {
            source {
              __typename
              ... on PullRequest {
                number
                url
                repository { nameWithOwner }
              }
            }
          }
          ... on ConnectedEvent {
            subject {
              __typename
              ... on PullRequest {
                number
                url
                repository { nameWithOwner }
              }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""

PULL_REQUEST_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number
      url
      state
      mergedAt
      isDraft
      repository { nameWithOwner }
    }
  }
}
"""


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


@dataclass(frozen=True)
class IssueSnapshot:
    number: int
    comments: tuple[str, ...]
    linked_pull_requests: tuple[LinkedPullRequest, ...]


GhRunner = Callable[[list[str]], dict[str, Any]]


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


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SyncPrStatusCommentsError(f"{label} must be an object")
    return value


def _split_repository(repository: str, label: str) -> tuple[str, str]:
    parts = repository.split("/")
    if len(parts) != 2 or not all(parts):
        raise SyncPrStatusCommentsError(
            f"{label} must be an owner/repository string"
        )
    return parts[0], parts[1]


def run_gh_api(args: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise SyncPrStatusCommentsError(f"could not run gh api: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no gh output"
        raise SyncPrStatusCommentsError(f"gh api failed: {detail}")
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SyncPrStatusCommentsError(
            f"gh api returned invalid JSON: {error}"
        ) from error
    return _require_mapping(response, "gh api response")


class GhClient:
    def __init__(
        self,
        issue_repo: str,
        pr_repo: str,
        *,
        runner: GhRunner = run_gh_api,
    ) -> None:
        self.issue_repo = issue_repo
        self.pr_repo = pr_repo
        self._issue_owner, self._issue_name = _split_repository(
            issue_repo,
            "issue repository",
        )
        self._pr_owner, self._pr_name = _split_repository(
            pr_repo,
            "PR repository",
        )
        self._runner = runner

    def _graphql(
        self,
        query: str,
        variables: dict[str, str | int | None],
    ) -> dict[str, Any]:
        args = ["gh", "api", "graphql", "-f", f"query={query}"]
        for key, value in variables.items():
            if value is None:
                continue
            flag = "-F" if isinstance(value, int) else "-f"
            args.extend([flag, f"{key}={value}"])
        response = self._runner(args)
        errors = response.get("errors")
        if errors:
            raise SyncPrStatusCommentsError(f"GitHub GraphQL errors: {errors}")
        return _require_mapping(response.get("data"), "GraphQL data")

    @staticmethod
    def _page(
        connection: Any,
        label: str,
    ) -> tuple[list[Any], str | None]:
        data = _require_mapping(connection, label)
        nodes = data.get("nodes")
        if not isinstance(nodes, list):
            raise SyncPrStatusCommentsError(f"{label}.nodes must be an array")
        page_info = _require_mapping(data.get("pageInfo"), f"{label}.pageInfo")
        has_next_page = page_info.get("hasNextPage")
        end_cursor = page_info.get("endCursor")
        if not isinstance(has_next_page, bool):
            raise SyncPrStatusCommentsError(
                f"{label}.pageInfo.hasNextPage must be a boolean"
            )
        if has_next_page and not isinstance(end_cursor, str):
            raise SyncPrStatusCommentsError(
                f"{label}.pageInfo.endCursor is required for another page"
            )
        return nodes, end_cursor if has_next_page else None

    @staticmethod
    def _repository(data: dict[str, Any]) -> dict[str, Any]:
        return _require_mapping(data.get("repository"), "GraphQL repository")

    def list_labeled_issue_numbers(self, issue_tag: str) -> tuple[int, ...]:
        numbers: list[int] = []
        cursor: str | None = None
        while True:
            data = self._graphql(
                ISSUES_QUERY,
                {
                    "owner": self._issue_owner,
                    "name": self._issue_name,
                    "label": issue_tag,
                    "after": cursor,
                },
            )
            repository = self._repository(data)
            nodes, cursor = self._page(repository.get("issues"), "issues")
            for node in nodes:
                issue = _require_mapping(node, "issue")
                number = issue.get("number")
                if isinstance(number, bool) or not isinstance(number, int):
                    raise SyncPrStatusCommentsError(
                        "issue.number must be an integer"
                    )
                numbers.append(number)
            if cursor is None:
                return tuple(numbers)

    def _comments(self, issue_number: int) -> tuple[str, ...]:
        comments: list[str] = []
        cursor: str | None = None
        while True:
            data = self._graphql(
                COMMENTS_QUERY,
                {
                    "owner": self._issue_owner,
                    "name": self._issue_name,
                    "number": issue_number,
                    "after": cursor,
                },
            )
            issue = _require_mapping(
                self._repository(data).get("issue"),
                f"issue #{issue_number}",
            )
            nodes, cursor = self._page(issue.get("comments"), "comments")
            for node in nodes:
                comment = _require_mapping(node, "comment")
                body = comment.get("body")
                if not isinstance(body, str):
                    raise SyncPrStatusCommentsError(
                        "comment.body must be a string"
                    )
                comments.append(body)
            if cursor is None:
                return tuple(comments)

    def _linked_pull_requests(
        self,
        issue_number: int,
    ) -> tuple[LinkedPullRequest, ...]:
        linked: dict[int, LinkedPullRequest] = {}
        cursor: str | None = None
        while True:
            data = self._graphql(
                TIMELINE_QUERY,
                {
                    "owner": self._issue_owner,
                    "name": self._issue_name,
                    "number": issue_number,
                    "after": cursor,
                },
            )
            issue = _require_mapping(
                self._repository(data).get("issue"),
                f"issue #{issue_number}",
            )
            nodes, cursor = self._page(
                issue.get("timelineItems"),
                "timeline items",
            )
            for node in nodes:
                event = _require_mapping(node, "timeline item")
                event_type = event.get("__typename")
                if event_type == CROSS_REFERENCED_EVENT:
                    candidate = event.get("source")
                elif event_type == CONNECTED_EVENT:
                    candidate = event.get("subject")
                else:
                    raise SyncPrStatusCommentsError(
                        f"unexpected timeline item type: {event_type}"
                    )
                reference = _require_mapping(candidate, "timeline reference")
                if reference.get("__typename") != PULL_REQUEST_TYPENAME:
                    continue
                repository = _require_mapping(
                    reference.get("repository"),
                    "pull request repository",
                ).get("nameWithOwner")
                if not isinstance(repository, str):
                    raise SyncPrStatusCommentsError(
                        "pull request repository name must be a string"
                    )
                if repository.casefold() != self.pr_repo.casefold():
                    continue
                number = reference.get("number")
                url = reference.get("url")
                if isinstance(number, bool) or not isinstance(number, int):
                    raise SyncPrStatusCommentsError(
                        "pull request number must be an integer"
                    )
                if not isinstance(url, str):
                    raise SyncPrStatusCommentsError(
                        "pull request URL must be a string"
                    )
                linked[number] = LinkedPullRequest(repository, number, url)
            if cursor is None:
                return tuple(linked[number] for number in sorted(linked))

    def get_issue_snapshot(self, issue_number: int) -> IssueSnapshot:
        return IssueSnapshot(
            number=issue_number,
            comments=self._comments(issue_number),
            linked_pull_requests=self._linked_pull_requests(issue_number),
        )

    def get_pull_request(self, number: int) -> PullRequestStatus:
        data = self._graphql(
            PULL_REQUEST_QUERY,
            {
                "owner": self._pr_owner,
                "name": self._pr_name,
                "number": number,
            },
        )
        pull_request = _require_mapping(
            self._repository(data).get("pullRequest"),
            f"pull request #{number}",
        )
        repository = _require_mapping(
            pull_request.get("repository"),
            "pull request repository",
        ).get("nameWithOwner")
        url = pull_request.get("url")
        state = pull_request.get("state")
        merged_at = pull_request.get("mergedAt")
        is_draft = pull_request.get("isDraft")
        returned_number = pull_request.get("number")
        if (
            isinstance(returned_number, bool)
            or not isinstance(returned_number, int)
            or returned_number != number
        ):
            raise SyncPrStatusCommentsError(
                f"pull request response number {returned_number} does not match #{number}"
            )
        if not isinstance(repository, str):
            raise SyncPrStatusCommentsError(
                f"pull request #{number} repository must be a string"
            )
        if repository.casefold() != self.pr_repo.casefold():
            raise SyncPrStatusCommentsError(
                f"pull request #{number} belongs to {repository}, not {self.pr_repo}"
            )
        if not isinstance(url, str) or not isinstance(state, str):
            raise SyncPrStatusCommentsError(
                f"pull request #{number} has incomplete status data"
            )
        if merged_at is not None and not isinstance(merged_at, str):
            raise SyncPrStatusCommentsError(
                f"pull request #{number}.mergedAt must be a string or null"
            )
        if not isinstance(is_draft, bool):
            raise SyncPrStatusCommentsError(
                f"pull request #{number}.isDraft must be a boolean"
            )
        return PullRequestStatus(
            repository=repository,
            number=number,
            url=url,
            state=state,
            merged_at=merged_at,
            is_draft=is_draft,
        )

    def issue_has_label(self, issue_number: int, issue_tag: str) -> bool:
        response = self._runner(
            ["gh", "api", f"repos/{self.issue_repo}/issues/{issue_number}"]
        )
        labels = response.get("labels")
        if not isinstance(labels, list):
            raise SyncPrStatusCommentsError(
                f"issue #{issue_number}.labels must be an array"
            )
        names: list[str] = []
        for value in labels:
            label = _require_mapping(value, "issue label")
            name = label.get("name")
            if not isinstance(name, str):
                raise SyncPrStatusCommentsError(
                    "issue label name must be a string"
                )
            names.append(name)
        return issue_tag in names

    def add_issue_comment(self, issue_number: int, body: str) -> str:
        response = self._runner(
            [
                "gh",
                "api",
                f"repos/{self.issue_repo}/issues/{issue_number}/comments",
                "-X",
                "POST",
                "-f",
                f"body={body}",
            ]
        )
        if response.get("body") != body:
            raise SyncPrStatusCommentsError(
                f"issue #{issue_number} comment response body mismatch"
            )
        url = response.get("html_url")
        expected_prefix = (
            f"https://github.com/{self.issue_repo}/issues/"
            f"{issue_number}#issuecomment-"
        )
        if not isinstance(url, str) or not url.startswith(expected_prefix):
            raise SyncPrStatusCommentsError(
                f"issue #{issue_number} comment response URL is invalid"
            )
        return url
