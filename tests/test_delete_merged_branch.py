from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "cleanup-merged-pr" / "scripts" / "delete_merged_branch.py"
DEFAULT_BRANCH = "main"
FEATURE_BRANCH = "feature"

# Isolates tests from the user's git config, such as commit signing.
GIT_CONFIG = """\
[user]
\tname = Test
\temail = test@example.com
[init]
\tdefaultBranch = main
[commit]
\tgpgsign = false
[protocol "file"]
\tallow = always
"""

# Answers only the two gh calls the script makes.
GH_STUB = """\
#!/usr/bin/env python3
import os
import sys

args = sys.argv[1:]
if args[:2] == ["repo", "view"]:
    print('{"defaultBranchRef": {"name": "main"}}')
elif args[:2] == ["pr", "list"] and "merged" in args:
    # Tests always use the branch "feature".
    if args[args.index("--head") + 1] != "feature":
        sys.exit("unexpected --head value")
    print(os.environ["GH_STUB_MERGED_PRS"])
else:
    sys.exit(f"unexpected gh call: {args}")
"""


class Fixture:
    """A bare origin, a clone at `main_checkout`, and a stub `gh` on PATH."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.worktrees: list[Path] = []
        bin_dir = root / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(GH_STUB, encoding="utf-8")
        gh.chmod(0o755)
        git_config = root / "gitconfig"
        git_config.write_text(GIT_CONFIG, encoding="utf-8")
        self.env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "GIT_CONFIG_GLOBAL": str(git_config),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GH_STUB_MERGED_PRS": "[]",
        }
        self.origin = root / "origin.git"
        self.git(root, "init", "--bare", str(self.origin))
        self.main_checkout = root / "repo"
        self.git(root, "clone", str(self.origin), str(self.main_checkout))
        (self.main_checkout / ".gitignore").write_text(".env\nnode_modules/\n", encoding="utf-8")
        self.commit(self.main_checkout, "README.md")
        self.git(self.main_checkout, "push", "origin", DEFAULT_BRANCH)

    def git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=cwd, env=self.env, check=True, capture_output=True, text=True
        )
        return result.stdout.strip()

    def commit(self, cwd: Path, file_name: str) -> str:
        (cwd / file_name).write_text(f"{file_name}\n", encoding="utf-8")
        self.git(cwd, "add", "-A")
        self.git(cwd, "commit", "-m", f"add {file_name}")
        return self.git(cwd, "rev-parse", "HEAD")

    def add_worktree(self, branch: str = FEATURE_BRANCH) -> Path:
        path = self.root / f"wt-{branch}"
        self.git(self.main_checkout, "worktree", "add", "-b", branch, str(path))
        self.worktrees.append(path)
        return path

    def create_submodule_origin(self) -> Path:
        source = self.root / "sub-src"
        self.git(self.root, "init", str(source))
        self.commit(source, "lib.txt")
        sub_origin = self.root / "sub.git"
        self.git(self.root, "clone", "--bare", str(source), str(sub_origin))
        return sub_origin

    def add_submodule(self) -> None:
        sub_origin = self.create_submodule_origin()
        self.git(self.main_checkout, "submodule", "add", str(sub_origin), "sub")
        self.git(self.main_checkout, "commit", "-m", "add submodule")
        self.git(self.main_checkout, "push", "origin", DEFAULT_BRANCH)

    def ignore_locally(self, repo: Path, *patterns: str) -> None:
        """Append patterns to the repository's `info/exclude`, so `git status` stays clean."""
        exclude = Path(self.git(repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as file:
            file.write("".join(f"{pattern}\n" for pattern in patterns))

    def set_merged_prs(self, *head_oids: str) -> None:
        prs = [{"number": 7 + index, "headRefOid": oid} for index, oid in enumerate(head_oids)]
        self.env["GH_STUB_MERGED_PRS"] = json.dumps(prs)

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def branch_exists(self, branch: str) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=self.main_checkout,
            env=self.env,
            capture_output=True,
        )
        return result.returncode == 0


class DeleteMergedBranchTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.fixture = Fixture(Path(temp_dir.name).resolve())

    def assert_refused(self, result: subprocess.CompletedProcess[str], reason: str) -> None:
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("refused:", result.stderr)
        self.assertIn(reason, result.stderr)
        self.assertTrue(self.fixture.branch_exists(FEATURE_BRANCH))
        for worktree in self.fixture.worktrees:
            self.assertTrue(worktree.exists(), f"{worktree} was removed")

    def test_merged_pr_matching_tip_deletes_current_worktree_and_branch(self) -> None:
        worktree = self.fixture.add_worktree()
        tip = self.fixture.commit(worktree, "feature.txt")
        self.fixture.set_merged_prs(tip)

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(worktree.exists())
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))
        self.assertIn(f"removed worktree: {worktree}", result.stdout)
        self.assertIn(f"main worktree: {self.fixture.main_checkout}", result.stdout)

    def test_local_tip_ahead_of_merged_head_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        self.fixture.commit(worktree, "after-merge.txt")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "not on origin/main")

    def test_branch_without_pr_or_new_commits_is_deleted(self) -> None:
        worktree = self.fixture.add_worktree()

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))

    def test_unmerged_commits_are_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.commit(worktree, "feature.txt")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "not on origin/main")

    def test_branch_in_main_checkout_switches_to_default_then_deletes(self) -> None:
        main_checkout = self.fixture.main_checkout
        self.fixture.git(main_checkout, "switch", "-c", FEATURE_BRANCH)
        self.fixture.set_merged_prs(self.fixture.commit(main_checkout, "feature.txt"))
        (main_checkout / ".env").write_text("TOKEN=x\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(main_checkout))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.fixture.git(main_checkout, "branch", "--show-current"), DEFAULT_BRANCH)
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))
        self.assertTrue((main_checkout / ".env").exists())

    def test_local_tip_behind_merged_head_is_deleted(self) -> None:
        fixture = self.fixture
        worktree = fixture.add_worktree()
        fixture.commit(worktree, "feature.txt")
        fixture.git(worktree, "push", "origin", FEATURE_BRANCH)
        other = fixture.root / "other"
        fixture.git(fixture.root, "clone", str(fixture.origin), str(other))
        fixture.git(other, "checkout", FEATURE_BRANCH)
        later_head = fixture.commit(other, "review-suggestion.txt")
        fixture.git(other, "push", "origin", "HEAD:refs/pull/7/head")
        fixture.set_merged_prs(later_head)

        result = fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(fixture.branch_exists(FEATURE_BRANCH))

    def test_unfetchable_merged_head_is_refused_with_fetch_error(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.commit(worktree, "feature.txt")
        self.fixture.set_merged_prs("0" * 40)

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "could not fetch refs/pull/7/head")

    def test_branch_not_checked_out_is_deleted(self) -> None:
        main_checkout = self.fixture.main_checkout
        self.fixture.git(main_checkout, "branch", FEATURE_BRANCH)

        result = self.fixture.run_script("--repo", str(main_checkout), "--branch", FEATURE_BRANCH)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))
        self.assertIn("removed worktree: none", result.stdout)

    def test_branch_in_two_worktrees_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        second = self.fixture.root / "wt-feature-2"
        self.fixture.git(self.fixture.main_checkout, "worktree", "add", "-f", str(second), FEATURE_BRANCH)
        self.fixture.worktrees.append(second)

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "checked out in 2 worktrees")

    def test_default_branch_is_refused(self) -> None:
        result = self.fixture.run_script("--repo", str(self.fixture.main_checkout), "--branch", DEFAULT_BRANCH)

        self.assertEqual(result.returncode, 1)
        self.assertIn("refused: main is the default branch", result.stderr)

    def test_uncommitted_change_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        (worktree / "feature.txt").write_text("changed\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "uncommitted changes")
        self.assertTrue(worktree.exists())

    def test_untracked_file_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        (worktree / "notes.txt").write_text("draft\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "notes.txt")

    def test_dirty_submodule_is_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        (worktree / "sub" / "scratch.txt").write_text("draft\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "has uncommitted changes")

    def test_submodule_commit_on_no_remote_is_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.commit(worktree / "sub", "local-only.txt")
        self.fixture.git(worktree, "add", "sub")
        self.fixture.git(worktree, "commit", "-m", "bump submodule")
        self.fixture.set_merged_prs(self.fixture.git(worktree, "rev-parse", "HEAD"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "submodule sub has commits that are on no remote")


    def test_submodule_branch_on_no_remote_is_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        self.fixture.git(worktree / "sub", "switch", "-c", "wip")
        self.fixture.commit(worktree / "sub", "wip.txt")
        self.fixture.git(worktree, "submodule", "update")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "submodule sub has commits that are on no remote")

    def test_submodule_stash_is_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        (worktree / "sub" / "lib.txt").write_text("changed\n", encoding="utf-8")
        self.fixture.git(worktree / "sub", "stash")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "submodule sub has a stash")

    def test_deinitialized_submodule_with_unpushed_commit_is_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.commit(worktree / "sub", "local-only.txt")
        self.fixture.git(worktree, "add", "sub")
        self.fixture.git(worktree, "commit", "-m", "bump submodule")
        self.fixture.git(worktree, "submodule", "deinit", "-f", "sub")
        self.fixture.set_merged_prs(self.fixture.git(worktree, "rev-parse", "HEAD"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "submodule sub has commits that are on no remote")

    def test_deleted_current_directory_with_repo_still_works(self) -> None:
        self.fixture.add_worktree()
        gone = self.fixture.root / "gone"
        gone.mkdir()
        command = [
            "sh", "-c", 'cd "$1" && rmdir "$1" && shift && exec "$@"', "sh", str(gone),
            sys.executable, str(SCRIPT),
            "--repo", str(self.fixture.main_checkout), "--branch", FEATURE_BRANCH,
        ]

        result = subprocess.run(command, env=self.fixture.env, capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))


    def test_embedded_submodule_git_dir_with_unpushed_commit_is_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        sub_origin = self.fixture.root / "sub.git"
        self.fixture.git(worktree, "clone", str(sub_origin), "libx")
        self.fixture.commit(worktree / "libx", "local-only.txt")
        self.fixture.git(worktree, "submodule", "add", str(sub_origin), "libx")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "submodule libx has commits that are on no remote")

    def test_submodule_worktree_commit_is_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        sub_worktree = self.fixture.root / "subwt"
        self.fixture.git(worktree / "sub", "worktree", "add", "--detach", str(sub_worktree))
        self.fixture.commit(sub_worktree, "local-only.txt")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "submodule sub has commits that are on no remote")

    def test_submodule_fetched_off_branch_tag_does_not_block(self) -> None:
        self.fixture.add_submodule()
        source = self.fixture.root / "sub-src"
        sub_origin = self.fixture.root / "sub.git"
        self.fixture.git(source, "switch", "--detach")
        self.fixture.commit(source, "release.txt")
        self.fixture.git(source, "tag", "v1.0.0")
        self.fixture.git(source, "switch", DEFAULT_BRANCH)
        self.fixture.git(source, "push", str(sub_origin), "v1.0.0")
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.git(worktree / "sub", "fetch", "--tags")
        self.assertEqual(self.fixture.git(worktree / "sub", "tag", "--list", "v1.0.0"), "v1.0.0")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))

    def test_main_checkout_submodule_branch_does_not_block(self) -> None:
        main_checkout = self.fixture.main_checkout
        self.fixture.add_submodule()
        self.fixture.git(main_checkout, "submodule", "update", "--init")
        self.fixture.git(main_checkout / "sub", "switch", "-c", "keep")
        self.fixture.commit(main_checkout / "sub", "local-only.txt")
        self.fixture.git(main_checkout, "submodule", "update")
        self.fixture.git(main_checkout, "switch", "-c", FEATURE_BRANCH)
        self.fixture.set_merged_prs(self.fixture.commit(main_checkout, "feature.txt"))

        result = self.fixture.run_script("--repo", str(main_checkout))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))

    def test_ignored_env_file_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        (worktree / ".env").write_text("TOKEN=x\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, ".env")

    def test_ignored_regenerable_directory_is_deleted_and_listed(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        package = worktree / "node_modules" / "pkg"
        package.mkdir(parents=True)
        (package / "index.js").write_text("module.exports = 1;\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(worktree.exists())
        self.assertIn("deleted ignored paths: node_modules/", result.stdout)

    def test_ignored_env_file_in_submodule_is_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        submodule = worktree / "sub"
        exclude = Path(self.fixture.git(submodule, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(".env\n", encoding="utf-8")
        (submodule / ".env").write_text("TOKEN=x\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "sub/.env")

    def test_ignored_nested_repository_with_unpushed_commit_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.ignore_locally(worktree, "tmp/")
        self.fixture.git(worktree, "init", "tmp/helper")
        self.fixture.commit(worktree / "tmp" / "helper", "local.txt")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "nested repository tmp/helper has commits that are on no remote")

    def test_ignored_clean_nested_clone_does_not_block(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.ignore_locally(worktree, "tmp/")
        self.fixture.git(worktree, "clone", str(self.fixture.origin), "tmp/dep")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(worktree.exists())

    def test_ignored_nested_worktree_of_same_repository_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.ignore_locally(worktree, ".worktrees/")
        nested = worktree / ".worktrees" / "other"
        self.fixture.git(self.fixture.main_checkout, "worktree", "add", "-b", "other", str(nested))
        self.fixture.worktrees.append(nested)
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "nested worktree .worktrees/other belongs to this repository")

    def test_ignored_nested_repository_submodule_with_unpushed_branch_is_refused(self) -> None:
        # The nested repository is clean and pushed, and its submodule is detached at the pinned
        # commit, so status is clean everywhere. Only the unpushed `wip` branch in the submodule
        # can make the script refuse.
        sub_origin = self.fixture.create_submodule_origin()
        worktree = self.fixture.add_worktree()
        self.fixture.ignore_locally(worktree, "tmp/")
        helper = worktree / "tmp" / "helper"
        self.fixture.git(worktree, "clone", str(self.fixture.origin), "tmp/helper")
        self.fixture.git(helper, "submodule", "add", str(sub_origin), "inner")
        self.fixture.git(helper, "commit", "-m", "add inner")
        self.fixture.git(helper, "push", "origin", "HEAD:refs/heads/helper-base")
        pinned = self.fixture.git(helper / "inner", "rev-parse", "HEAD")
        self.fixture.git(helper / "inner", "switch", "-c", "wip")
        self.fixture.commit(helper / "inner", "wip.txt")
        self.fixture.git(helper / "inner", "switch", "--detach", pinned)
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "submodule tmp/helper/inner has commits that are on no remote")

    def test_ignored_nested_clone_at_fetched_off_branch_tag_does_not_block(self) -> None:
        main_checkout = self.fixture.main_checkout
        self.fixture.git(main_checkout, "switch", "--detach")
        self.fixture.commit(main_checkout, "release.txt")
        self.fixture.git(main_checkout, "tag", "v1.0.0")
        self.fixture.git(main_checkout, "push", "origin", "v1.0.0")
        self.fixture.git(main_checkout, "switch", DEFAULT_BRANCH)
        worktree = self.fixture.add_worktree()
        self.fixture.ignore_locally(worktree, "lib/")
        self.fixture.git(worktree, "clone", str(self.fixture.origin), "lib/dep")
        self.fixture.git(worktree / "lib" / "dep", "checkout", "v1.0.0")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(worktree.exists())

    def test_sensitive_looking_names_in_package_directories_do_not_block(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        viem = worktree / "node_modules" / "viem"
        viem.mkdir(parents=True)
        (viem / "createWebAuthnCredential.js").write_text("module.exports = 1;\n", encoding="utf-8")
        package = worktree / "node_modules" / "pkg"
        package.mkdir()
        (package / "server.pem").write_text("public\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(worktree.exists())

    def test_ignored_env_file_with_uppercase_name_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.ignore_locally(worktree, ".ENV")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        (worktree / ".ENV").write_text("TOKEN=x\n", encoding="utf-8")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, ".ENV")

    def test_files_at_deinitialized_submodule_path_are_refused(self) -> None:
        self.fixture.add_submodule()
        worktree = self.fixture.add_worktree()
        self.fixture.git(worktree, "submodule", "update", "--init")
        self.fixture.git(worktree, "submodule", "deinit", "-f", "sub")
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        (worktree / "sub" / "notes.txt").write_text("draft\n", encoding="utf-8")
        status = self.fixture.git(worktree, "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none")
        self.assertEqual(status, "")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "submodule path sub is not initialized but contains files")


if __name__ == "__main__":
    unittest.main()
