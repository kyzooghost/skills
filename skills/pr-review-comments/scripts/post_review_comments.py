#!/usr/bin/env python3
"""Post approved GitHub review comments without shell interpolation."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


PRIMARY_URL_TOKEN = "{primary_url}"
PRIMARY_URL_FOOTER = f"See primary comment: {PRIMARY_URL_TOKEN}"
RIGHT_SIDE = "RIGHT"
DISCUSSION_URL_PATTERN = re.compile(
    r"^https://github\.com/[^/]+/[^/]+/pull/\d+#discussion_r\d+$"
)
UNRESOLVED_MARKERS = (
    "$primary_url",
    "<primary html_url",
    "{primary_url}",
    "{owner}",
    "{repo}",
    "{pr}",
    "{id}",
)


class PostReviewCommentsError(ValueError):
    """Raised when a spec or GitHub response cannot be trusted."""


@dataclass(frozen=True)
class CommentTarget:
    path: str
    line: int
    body: str
    start_line: int | None = None


@dataclass(frozen=True)
class CommentSpec:
    repo: str
    pr: int
    commit: str
    primary: CommentTarget
    companions: tuple[CommentTarget, ...]


Runner = Callable[[list[str]], dict[str, Any]]


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PostReviewCommentsError(f"{label} must be an object")
    return value


def _target(value: Any, label: str) -> CommentTarget:
    data = _require_mapping(value, label)
    path = data.get("path")
    line = data.get("line")
    body = data.get("body")
    start_line = data.get("start_line")
    if not isinstance(path, str) or not path:
        raise PostReviewCommentsError(f"{label}.path must be a non-empty string")
    if isinstance(line, bool) or not isinstance(line, int) or line <= 0:
        raise PostReviewCommentsError(f"{label}.line must be a positive integer")
    if not isinstance(body, str) or not body:
        raise PostReviewCommentsError(f"{label}.body must be a non-empty string")
    if start_line is not None:
        if isinstance(start_line, bool) or not isinstance(start_line, int) or start_line <= 0:
            raise PostReviewCommentsError(f"{label}.start_line must be a positive integer")
        if start_line >= line:
            raise PostReviewCommentsError(f"{label}.start_line must be less than {label}.line")
    return CommentTarget(path=path, line=line, body=body, start_line=start_line)


def _reject_unresolved_markers(body: str, label: str, *, allow_primary_url: bool = False) -> None:
    for marker in UNRESOLVED_MARKERS:
        if marker == PRIMARY_URL_TOKEN and allow_primary_url:
            continue
        if marker in body:
            raise PostReviewCommentsError(f"{label}.body contains unresolved marker {marker}")


def _title(body: str) -> str:
    return next((line for line in body.splitlines() if line.strip()), "")


def _require_companion_footer(body: str, label: str, primary_url: str) -> None:
    footer = PRIMARY_URL_FOOTER.replace(PRIMARY_URL_TOKEN, primary_url)
    if not body.rstrip("\r\n").endswith(footer):
        raise PostReviewCommentsError(
            f"{label} must end with the captured primary discussion URL"
        )


def validate_spec(raw_spec: dict[str, Any]) -> CommentSpec:
    data = _require_mapping(raw_spec, "spec")
    repo = data.get("repo")
    pr = data.get("pr")
    commit = data.get("commit")
    if not isinstance(repo, str) or not repo or repo.count("/") != 1:
        raise PostReviewCommentsError("spec.repo must be an owner/repository string")
    owner, repository = repo.split("/")
    if not owner or not repository:
        raise PostReviewCommentsError("spec.repo must be an owner/repository string")
    if isinstance(pr, bool) or not isinstance(pr, int) or pr <= 0:
        raise PostReviewCommentsError("spec.pr must be a positive integer")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise PostReviewCommentsError("spec.commit must be a 40-character commit SHA")

    primary = _target(data.get("primary"), "spec.primary")
    _reject_unresolved_markers(primary.body, "spec.primary")
    raw_companions = data.get("companions", [])
    if not isinstance(raw_companions, list):
        raise PostReviewCommentsError("spec.companions must be an array")

    companions: list[CommentTarget] = []
    primary_title = _title(primary.body)
    for index, raw_companion in enumerate(raw_companions):
        companion = _target(raw_companion, f"spec.companions[{index}]")
        _reject_unresolved_markers(
            companion.body,
            f"spec.companions[{index}]",
            allow_primary_url=True,
        )
        if companion.body.count(PRIMARY_URL_TOKEN) != 1:
            raise PostReviewCommentsError(
                f"spec.companions[{index}].body must contain exactly one {PRIMARY_URL_TOKEN} token"
            )
        _require_companion_footer(
            companion.body,
            f"spec.companions[{index}].body",
            PRIMARY_URL_TOKEN,
        )
        if _title(companion.body) != primary_title:
            raise PostReviewCommentsError(
                f"spec.companions[{index}].body must use the primary title verbatim"
            )
        companions.append(companion)

    return CommentSpec(repo, pr, commit, primary, tuple(companions))


def load_spec(spec_path: Path) -> CommentSpec:
    try:
        raw_spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PostReviewCommentsError(f"cannot read spec {spec_path}: {error}") from error
    except json.JSONDecodeError as error:
        raise PostReviewCommentsError(f"invalid JSON in spec {spec_path}: {error}") from error
    return validate_spec(raw_spec)


def _request_args(spec: CommentSpec, target: CommentTarget) -> list[str]:
    args = [
        "gh",
        "api",
        f"repos/{spec.repo}/pulls/{spec.pr}/comments",
        "-f",
        f"body={target.body}",
        "-f",
        f"path={target.path}",
    ]
    if target.start_line is not None:
        args.extend(
            [
                "-F",
                f"start_line={target.start_line}",
                "-f",
                f"start_side={RIGHT_SIDE}",
            ]
        )
    args.extend(
        [
        "-F",
        f"line={target.line}",
        "-f",
        f"side={RIGHT_SIDE}",
        "-f",
        f"commit_id={spec.commit}",
        ]
    )
    return args


def run_gh_api(args: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(args, check=False, capture_output=True, text=True)
    except OSError as error:
        raise PostReviewCommentsError(f"could not run gh api: {error}") from error
    if completed.returncode != 0:
        output = [stream.strip() for stream in (completed.stderr, completed.stdout) if stream.strip()]
        detail = "\n".join(output) or "no gh output"
        raise PostReviewCommentsError(f"gh api failed: {detail}")
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise PostReviewCommentsError(f"gh api returned invalid JSON: {error}") from error
    if not isinstance(response, dict):
        raise PostReviewCommentsError("gh api returned a non-object response")
    return response


def _validate_response(
    response: dict[str, Any],
    target: CommentTarget,
    label: str,
    expected_url_prefix: str,
) -> str:
    if not isinstance(response, dict):
        raise PostReviewCommentsError(f"{label} response must be an object")
    if response.get("body") != target.body:
        raise PostReviewCommentsError(f"{label} response body does not match the submitted body")
    if response.get("path") != target.path:
        raise PostReviewCommentsError(f"{label} response path does not match the submitted path")
    if response.get("line") != target.line:
        raise PostReviewCommentsError(f"{label} response line does not match the submitted line")
    if target.start_line is not None:
        if response.get("start_line") != target.start_line:
            raise PostReviewCommentsError(f"{label} response start_line does not match the submitted start_line")
        if response.get("start_side") != RIGHT_SIDE:
            raise PostReviewCommentsError(f"{label} response start_side does not match the submitted start_side")
        if response.get("side") != RIGHT_SIDE:
            raise PostReviewCommentsError(f"{label} response side does not match the submitted side")
    url = response.get("html_url")
    if (
        not isinstance(url, str)
        or not DISCUSSION_URL_PATTERN.fullmatch(url)
        or not url.startswith(expected_url_prefix)
    ):
        raise PostReviewCommentsError(f"{label} response lacks a valid GitHub discussion URL")
    return url


def post_review_comments(
    raw_spec: dict[str, Any] | CommentSpec,
    *,
    runner: Runner = run_gh_api,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    spec = raw_spec if isinstance(raw_spec, CommentSpec) else validate_spec(raw_spec)
    if dry_run:
        targets = []
        for target in (spec.primary, *spec.companions):
            validated_target = {"path": target.path, "line": target.line, "body": target.body}
            if target.start_line is not None:
                validated_target["start_line"] = target.start_line
            targets.append(validated_target)
        return targets

    primary_response = runner(_request_args(spec, spec.primary))
    url_prefix = f"https://github.com/{spec.repo}/pull/{spec.pr}#discussion_r"
    try:
        primary_url = _validate_response(primary_response, spec.primary, "primary", url_prefix)
    except PostReviewCommentsError as error:
        returned_url = primary_response.get("html_url")
        if isinstance(returned_url, str) and DISCUSSION_URL_PATTERN.fullmatch(returned_url):
            raise PostReviewCommentsError(f"{error}; primary comment returned at {returned_url}") from error
        raise
    responses = [primary_response]

    for index, companion in enumerate(spec.companions):
        try:
            body = companion.body.replace(PRIMARY_URL_TOKEN, primary_url)
            _require_companion_footer(body, f"companion {index}", primary_url)
            resolved = CommentTarget(companion.path, companion.line, body, companion.start_line)
            response = runner(_request_args(spec, resolved))
            _validate_response(response, resolved, f"companion {index}", url_prefix)
        except PostReviewCommentsError as error:
            raise PostReviewCommentsError(
                f"{error}; primary comment posted at {primary_url}"
            ) from error
        responses.append(response)
    return responses


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="JSON comment spec path")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the spec and print targets without calling GitHub",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        spec = load_spec(args.spec)
        responses = post_review_comments(spec, dry_run=args.dry_run)
    except PostReviewCommentsError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        for target in responses:
            line_range = (
                f"{target['start_line']}-{target['line']}"
                if "start_line" in target
                else str(target["line"])
            )
            print(f"validated {target['path']}:{line_range}")
    else:
        for response in responses:
            print(response["html_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
