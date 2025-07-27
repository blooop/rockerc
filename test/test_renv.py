#!/usr/bin/env python3
"""
Tests for renv module.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rockerc.renv import (
    parse_repo_spec,
    get_renv_base_dir,
    get_repo_dir,
    get_worktree_dir,
    repo_exists,
    worktree_exists,
)


class TestRenvParsing(unittest.TestCase):
    """Test repository specification parsing."""

    def test_parse_repo_spec_with_branch(self):
        """Test parsing repo spec with branch."""
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher@main")
        self.assertEqual(owner, "blooop")
        self.assertEqual(repo, "bencher")
        self.assertEqual(branch, "main")
        self.assertEqual(subfolder, "")

    def test_parse_repo_spec_without_branch(self):
        """Test parsing repo spec without branch (defaults to main)."""
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher")
        self.assertEqual(owner, "blooop")
        self.assertEqual(repo, "bencher")
        self.assertEqual(branch, "main")
        self.assertEqual(subfolder, "")

    def test_parse_repo_spec_with_feature_branch(self):
        """Test parsing repo spec with feature branch."""
        owner, repo, branch, subfolder = parse_repo_spec("osrf/rocker@feature-branch")
        self.assertEqual(owner, "osrf")
        self.assertEqual(repo, "rocker")
        self.assertEqual(branch, "feature-branch")
        self.assertEqual(subfolder, "")

    def test_parse_repo_spec_with_subfolder(self):
        """Test parsing repo spec with subfolder."""
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher@main#scripts")
        self.assertEqual(owner, "blooop")
        self.assertEqual(repo, "bencher")
        self.assertEqual(branch, "main")
        self.assertEqual(subfolder, "scripts")

    def test_parse_repo_spec_with_nested_subfolder(self):
        """Test parsing repo spec with nested subfolder."""
        owner, repo, branch, subfolder = parse_repo_spec("osrf/rocker#docs/examples")
        self.assertEqual(owner, "osrf")
        self.assertEqual(repo, "rocker")
        self.assertEqual(branch, "main")
        self.assertEqual(subfolder, "docs/examples")

    def test_parse_repo_spec_with_branch_and_subfolder(self):
        """Test parsing repo spec with both branch and subfolder."""
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher@feature#src/main")
        self.assertEqual(owner, "blooop")
        self.assertEqual(repo, "bencher")
        self.assertEqual(branch, "feature")
        self.assertEqual(subfolder, "src/main")

    def test_parse_repo_spec_invalid_no_slash(self):
        """Test parsing invalid repo spec without slash."""
        with self.assertRaises(ValueError) as context:
            parse_repo_spec("invalid-repo")
        self.assertIn("Invalid repo specification", str(context.exception))

    def test_parse_repo_spec_invalid_empty_owner(self):
        """Test parsing invalid repo spec with empty owner."""
        with self.assertRaises(ValueError) as context:
            parse_repo_spec("/repo")
        self.assertIn("Owner and repo cannot be empty", str(context.exception))

    def test_parse_repo_spec_invalid_empty_repo(self):
        """Test parsing invalid repo spec with empty repo."""
        with self.assertRaises(ValueError) as context:
            parse_repo_spec("owner/")
        self.assertIn("Owner and repo cannot be empty", str(context.exception))


class TestRenvPaths(unittest.TestCase):
    """Test path generation functions."""

    def test_get_renv_base_dir(self):
        """Test getting renv base directory."""
        base_dir = get_renv_base_dir()
        expected = Path.home() / "renv"
        self.assertEqual(base_dir, expected)

    def test_get_repo_dir(self):
        """Test getting repository directory."""
        repo_dir = get_repo_dir("blooop", "bencher")
        expected = Path.home() / "renv" / "blooop" / "bencher"
        self.assertEqual(repo_dir, expected)

    def test_get_worktree_dir(self):
        """Test getting worktree directory."""
        worktree_dir = get_worktree_dir("blooop", "bencher", "main")
        expected = Path.home() / "renv" / "blooop" / "bencher" / "worktree-main"
        self.assertEqual(worktree_dir, expected)

    def test_get_worktree_dir_with_feature_branch(self):
        """Test getting worktree directory with feature branch."""
        worktree_dir = get_worktree_dir("osrf", "rocker", "feature-branch")
        expected = Path.home() / "renv" / "osrf" / "rocker" / "worktree-feature-branch"
        self.assertEqual(worktree_dir, expected)

    def test_get_worktree_dir_with_slash_in_branch(self):
        """Test getting worktree directory with slash in branch name."""
        worktree_dir = get_worktree_dir("osrf", "rocker", "feature/some-feature")
        expected = Path.home() / "renv" / "osrf" / "rocker" / "worktree-feature-some-feature"
        self.assertEqual(worktree_dir, expected)


class TestRenvExistence(unittest.TestCase):
    """Test repository and worktree existence checking."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch("rockerc.renv.get_renv_base_dir")
        self.mock_get_renv_base_dir = self.patcher.start()
        self.mock_get_renv_base_dir.return_value = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_repo_exists_false_when_dir_not_exists(self):
        """Test repo_exists returns False when directory doesn't exist."""
        self.assertFalse(repo_exists("blooop", "bencher"))

    def test_repo_exists_false_when_dir_exists_but_no_git(self):
        """Test repo_exists returns False when directory exists but no .git."""
        repo_dir = Path(self.temp_dir) / "blooop" / "bencher"
        repo_dir.mkdir(parents=True)
        self.assertFalse(repo_exists("blooop", "bencher"))

    def test_repo_exists_true_when_head_file_exists(self):
        """Test repo_exists returns True when HEAD file exists (bare repo)."""
        repo_dir = Path(self.temp_dir) / "blooop" / "bencher"
        repo_dir.mkdir(parents=True)
        (repo_dir / "HEAD").touch()  # Bare repos have HEAD file
        self.assertTrue(repo_exists("blooop", "bencher"))

    def test_worktree_exists_false_when_dir_not_exists(self):
        """Test worktree_exists returns False when directory doesn't exist."""
        self.assertFalse(worktree_exists("blooop", "bencher", "main"))

    def test_worktree_exists_false_when_dir_exists_but_no_git(self):
        """Test worktree_exists returns False when directory exists but no .git."""
        worktree_dir = Path(self.temp_dir) / "blooop" / "bencher" / "worktree-main"
        worktree_dir.mkdir(parents=True)
        self.assertFalse(worktree_exists("blooop", "bencher", "main"))

    def test_worktree_exists_true_when_git_file_exists(self):
        """Test worktree_exists returns True when .git file exists."""
        worktree_dir = Path(self.temp_dir) / "blooop" / "bencher" / "worktree-main"
        worktree_dir.mkdir(parents=True)
        (worktree_dir / ".git").touch()  # Worktrees have .git file, not directory
        self.assertTrue(worktree_exists("blooop", "bencher", "main"))


if __name__ == "__main__":
    unittest.main()
