#!/usr/bin/env python3
"""
Tests for renv git operations functionality.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from rockerc.renv import (
    list_branches,
    get_default_branch,
    list_owners_and_repos,
)


class TestRenvGitOperations(unittest.TestCase):
    """Test git-related operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch("rockerc.renv.get_renv_base_dir")
        self.mock_get_renv_base_dir = self.patcher.start()
        self.mock_get_renv_base_dir.return_value = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        self.patcher.stop()
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("subprocess.run")
    def test_list_branches_success(self, mock_run):
        """Test successful branch listing."""
        # Mock git branch command output
        mock_result = MagicMock()
        mock_result.stdout = """  remotes/origin/main
  remotes/origin/develop
  remotes/origin/feature/user-auth
  remotes/origin/bugfix/critical-fix
  remotes/origin/HEAD -> origin/main
* main
+ feature-local"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Set up repo directory
        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "HEAD").touch()

        branches = list_branches("owner", "repo")

        expected_branches = [
            "bugfix/critical-fix",
            "develop",
            "feature-local",
            "feature/user-auth",
            "main",
        ]
        self.assertEqual(sorted(branches), expected_branches)

    @patch("subprocess.run")
    def test_list_branches_no_repo(self, mock_run):
        """Test branch listing when repository doesn't exist."""
        branches = list_branches("nonexistent", "repo")
        self.assertEqual(branches, [])
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_list_branches_git_error(self, mock_run):
        """Test branch listing when git command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Set up repo directory
        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "HEAD").touch()

        branches = list_branches("owner", "repo")
        self.assertEqual(branches, [])

    @patch("subprocess.run")
    def test_list_branches_filters_head_pointer(self, mock_run):
        """Test that HEAD pointer is filtered out of branch list."""
        mock_result = MagicMock()
        mock_result.stdout = """  remotes/origin/main
  remotes/origin/HEAD -> origin/main
  remotes/origin/develop"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Set up repo directory
        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "HEAD").touch()

        branches = list_branches("owner", "repo")
        self.assertNotIn("HEAD", branches)
        self.assertIn("main", branches)
        self.assertIn("develop", branches)

    @patch("subprocess.run")
    def test_list_branches_handles_prefixes(self, mock_run):
        """Test that branch prefixes (* and +) are handled correctly."""
        mock_result = MagicMock()
        mock_result.stdout = """* main
+ feature-branch
  develop
  remotes/origin/release"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Set up repo directory
        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "HEAD").touch()

        branches = list_branches("owner", "repo")
        expected = ["develop", "feature-branch", "main", "release"]
        self.assertEqual(sorted(branches), expected)

    def test_list_owners_and_repos_empty(self):
        """Test listing owners and repos when none exist."""
        result = list_owners_and_repos()
        self.assertEqual(result, [])

    def test_list_owners_and_repos_with_repos(self):
        """Test listing owners and repos with actual repositories."""
        # Create test repository structure
        repos = [
            ("blooop", "bencher"),
            ("osrf", "rocker"),
            ("microsoft", "vscode"),
        ]

        for owner, repo in repos:
            repo_dir = Path(self.temp_dir) / owner / repo
            repo_dir.mkdir(parents=True)
            (repo_dir / "HEAD").touch()  # Make it look like a bare repo

        result = list_owners_and_repos()
        expected = ["blooop/bencher", "microsoft/vscode", "osrf/rocker"]
        self.assertEqual(sorted(result), expected)

    def test_list_owners_and_repos_ignores_non_repos(self):
        """Test that non-repository directories are ignored."""
        # Create mix of repos and non-repos
        repo_dir = Path(self.temp_dir) / "owner" / "real-repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "HEAD").touch()

        not_repo_dir = Path(self.temp_dir) / "owner" / "not-repo"
        not_repo_dir.mkdir(parents=True)
        # Don't create HEAD file

        result = list_owners_and_repos()
        self.assertEqual(result, ["owner/real-repo"])

    @patch("subprocess.run")
    def test_get_default_branch_from_head(self, mock_run):
        """Test getting default branch from HEAD."""
        mock_result = MagicMock()
        mock_result.stdout = "main\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)

        result = get_default_branch(repo_dir)
        self.assertEqual(result, "main")

    @patch("subprocess.run")
    def test_get_default_branch_fallback_to_branches(self, mock_run):
        """Test fallback to branch listing when HEAD method fails."""

        # First call (rev-parse) fails
        # Second call (branch listing) succeeds
        def side_effect(*args, **_kwargs):
            if "rev-parse" in args[0]:
                raise subprocess.CalledProcessError(1, "git")

            mock_result = MagicMock()
            mock_result.stdout = "* main\n  develop\n  feature\n"
            mock_result.returncode = 0
            return mock_result

        mock_run.side_effect = side_effect

        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)

        result = get_default_branch(repo_dir)
        self.assertEqual(result, "main")

    @patch("subprocess.run")
    def test_get_default_branch_prefers_main_over_master(self, mock_run):
        """Test that 'main' is preferred over 'master' when both exist."""

        def side_effect(*args, **_kwargs):
            if "rev-parse" in args[0]:
                raise subprocess.CalledProcessError(1, "git")

            mock_result = MagicMock()
            mock_result.stdout = "  master\n  main\n  develop\n"
            mock_result.returncode = 0
            return mock_result

        mock_run.side_effect = side_effect

        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)

        result = get_default_branch(repo_dir)
        self.assertEqual(result, "main")

    @patch("subprocess.run")
    def test_get_default_branch_uses_master_when_no_main(self, mock_run):
        """Test that 'master' is used when 'main' doesn't exist."""

        def side_effect(*args, **_kwargs):
            if "rev-parse" in args[0]:
                raise subprocess.CalledProcessError(1, "git")

            mock_result = MagicMock()
            mock_result.stdout = "  master\n  develop\n  feature\n"
            mock_result.returncode = 0
            return mock_result

        mock_run.side_effect = side_effect

        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)

        result = get_default_branch(repo_dir)
        self.assertEqual(result, "master")

    @patch("subprocess.run")
    def test_get_default_branch_ultimate_fallback(self, mock_run):
        """Test ultimate fallback to 'main' when all git operations fail."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        repo_dir = Path(self.temp_dir) / "owner" / "repo"
        repo_dir.mkdir(parents=True)

        result = get_default_branch(repo_dir)
        self.assertEqual(result, "main")


class TestRenvGitIntegration(unittest.TestCase):
    """Integration tests for git operations (requires git)."""

    def setUp(self):
        """Set up real git repository for integration tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir) / "test-repo"

        # Create a real git repository
        try:
            subprocess.run(
                ["git", "init", "--bare", str(self.repo_dir)], check=True, capture_output=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.skipTest("Git not available for integration tests")

    def tearDown(self):
        """Clean up integration test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_default_branch_with_real_repo(self):
        """Test get_default_branch with a real git repository."""
        # This test may vary based on git version and configuration
        result = get_default_branch(self.repo_dir)
        # Should return some valid branch name
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        # Common default branches
        self.assertIn(result, ["main", "master"])


if __name__ == "__main__":
    unittest.main()
