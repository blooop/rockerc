#!/usr/bin/env python3
"""
Tests for renv path and directory management functionality.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from rockerc.renv import repo_exists, worktree_exists


class TestRenvExistenceChecks(unittest.TestCase):
    """Test repository and worktree existence checking."""

    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch("rockerc.renv.get_renv_base_dir")
        self.mock_get_renv_base_dir = self.patcher.start()
        self.mock_get_renv_base_dir.return_value = Path(self.temp_dir)

    def test_worktree_exists_false_when_dir_not_exists(self):
        """Test worktree_exists returns False when directory doesn't exist."""
        self.assertFalse(worktree_exists("owner", "repo", "main"))

    def test_worktree_exists_false_when_dir_exists_but_no_git(self):
        """Test worktree_exists returns False when directory exists but no .git file."""
        worktree_dir = Path(self.temp_dir) / "owner" / "repo" / "worktree-main"
        worktree_dir.mkdir(parents=True)
        self.assertFalse(worktree_exists("owner", "repo", "main"))

    def test_worktree_exists_true_when_git_file_exists(self):
        """Test worktree_exists returns True when .git file exists."""
        worktree_dir = Path(self.temp_dir) / "owner" / "repo" / "worktree-main"
        worktree_dir.mkdir(parents=True)
        (worktree_dir / ".git").touch()
        self.assertTrue(worktree_exists("owner", "repo", "main"))

    def test_worktree_exists_with_git_worktree_structure(self):
        """Test worktree_exists with realistic git worktree structure."""
        worktree_dir = Path(self.temp_dir) / "company" / "project" / "worktree-feature-auth"
        worktree_dir.mkdir(parents=True)

        # Git worktrees have a .git file (not directory) pointing to the main repo
        (worktree_dir / ".git").write_text(
            "gitdir: /path/to/main/repo/.git/worktrees/feature-auth\n"
        )

        self.assertTrue(worktree_exists("company", "project", "feature/auth"))

    def test_multiple_repos_and_worktrees(self):
        """Test existence checks with multiple repos and worktrees."""
        # Set up multiple repositories
        repos = [
            ("blooop", "bencher"),
            ("osrf", "rocker"),
            ("user", "project"),
        ]

        for owner, repo in repos:
            repo_dir = Path(self.temp_dir) / owner / repo
            repo_dir.mkdir(parents=True)
            (repo_dir / "HEAD").touch()

            # Create multiple worktrees for each repo
            branches = ["main", "develop", "feature/test"]
            for branch in branches:
                safe_branch = branch.replace("/", "-")
                worktree_dir = repo_dir / f"worktree-{safe_branch}"
                worktree_dir.mkdir(parents=True)
                (worktree_dir / ".git").touch()

        # Test existence checks
        for owner, repo in repos:
            with self.subTest(owner=owner, repo=repo):
                self.assertTrue(repo_exists(owner, repo))
                self.assertTrue(worktree_exists(owner, repo, "main"))
                self.assertTrue(worktree_exists(owner, repo, "develop"))
                self.assertTrue(worktree_exists(owner, repo, "feature/test"))
                self.assertFalse(worktree_exists(owner, repo, "nonexistent"))

    def test_nested_owner_names(self):
        """Test handling of complex owner names."""
        # Some organizations use nested names or special characters
        complex_owners = [
            "my-org",
            "company.internal",
            "user_name",
            "123numeric",
        ]

        for owner in complex_owners:
            with self.subTest(owner=owner):
                repo_dir = Path(self.temp_dir) / owner / "test-repo"
                repo_dir.mkdir(parents=True)
                (repo_dir / "HEAD").touch()

                self.assertTrue(repo_exists(owner, "test-repo"))
                self.assertFalse(repo_exists(owner, "nonexistent-repo"))


if __name__ == "__main__":
    unittest.main()
