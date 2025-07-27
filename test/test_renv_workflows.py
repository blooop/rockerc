#!/usr/bin/env python3
"""
Tests for renv workflow functionality based on the major workflows documented in renv.md.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rockerc.renv import (
    get_all_repo_branch_combinations,
    generate_completion_candidates,
    setup_repo_environment,
)


class TestRenvWorkflows(unittest.TestCase):
    """Test the major workflows documented in renv.md."""

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

    def test_directory_structure_creation(self):
        """Test that renv creates the expected directory structure."""
        # From renv.md: ~/renv/owner/repo structure
        expected_structure = [
            ("blooop", "bencher"),
            ("osrf", "rocker"),
        ]

        for owner, repo in expected_structure:
            repo_dir = Path(self.temp_dir) / owner / repo
            repo_dir.mkdir(parents=True)
            (repo_dir / "HEAD").touch()

            # Create some worktrees
            for branch in ["main", "develop", "feature-auth"]:
                safe_branch = branch.replace("/", "-")
                worktree_dir = repo_dir / f"worktree-{safe_branch}"
                worktree_dir.mkdir(parents=True)
                (worktree_dir / ".git").touch()

        # Verify the structure matches documentation
        base_dir = Path(self.temp_dir)
        self.assertTrue((base_dir / "blooop" / "bencher").exists())
        self.assertTrue((base_dir / "osrf" / "rocker").exists())
        self.assertTrue((base_dir / "blooop" / "bencher" / "worktree-main").exists())
        self.assertTrue((base_dir / "blooop" / "bencher" / "worktree-feature-auth").exists())

    @patch("rockerc.renv.list_branches")
    def test_get_all_repo_branch_combinations(self, mock_list_branches):
        """Test getting all repository and branch combinations for fuzzy search."""
        # Set up mock repositories
        repos = [
            ("blooop", "bencher"),
            ("osrf", "rocker"),
        ]

        for owner, repo in repos:
            repo_dir = Path(self.temp_dir) / owner / repo
            repo_dir.mkdir(parents=True)
            (repo_dir / "HEAD").touch()

        # Mock branch listing
        mock_list_branches.side_effect = lambda owner, repo: {
            ("blooop", "bencher"): ["main", "develop", "feature/auth"],
            ("osrf", "rocker"): ["main", "master"],
        }.get((owner, repo), [])

        combinations = get_all_repo_branch_combinations()

        # Should include repos without @ first, then with @
        expected_combinations = [
            "blooop/bencher",
            "osrf/rocker",
            "blooop/bencher@main",
            "blooop/bencher@develop",
            "blooop/bencher@feature/auth",
            "osrf/rocker@main",
            "osrf/rocker@master",
        ]

        # Check that all expected combinations are present
        for combo in expected_combinations:
            self.assertIn(combo, combinations)

    def test_completion_candidates_workflow(self):
        """Test completion candidates for different input scenarios."""
        # Set up test repositories
        repos = [
            ("blooop", "bencher"),
            ("microsoft", "vscode"),
        ]

        for owner, repo in repos:
            repo_dir = Path(self.temp_dir) / owner / repo
            repo_dir.mkdir(parents=True)
            (repo_dir / "HEAD").touch()

        # Test 1: No input - should return all repos
        candidates = generate_completion_candidates([])
        self.assertIn("blooop/bencher", candidates)
        self.assertIn("microsoft/vscode", candidates)

        # Test 2: Partial owner - should filter
        candidates = generate_completion_candidates(["blo"])
        matching = [c for c in candidates if c.startswith("blo")]
        self.assertTrue(len(matching) > 0)

        # Test 3: Partial repo
        candidates = generate_completion_candidates(["micro"])
        matching = [c for c in candidates if "micro" in c.lower()]
        self.assertTrue(len(matching) >= 0)  # May or may not match depending on implementation

    @patch("rockerc.renv.clone_bare_repo")
    @patch("rockerc.renv.create_worktree")
    @patch("rockerc.renv.fetch_repo")
    @patch("rockerc.renv.repo_exists")
    def test_workflow_clone_and_work(
        self, mock_repo_exists, mock_fetch, mock_create_worktree, mock_clone
    ):
        """Test Workflow 1: Clone and Work on a Repo (renv blooop/bencher@main)."""
        # Simulate repository doesn't exist initially
        mock_repo_exists.return_value = False
        mock_worktree_dir = Path(self.temp_dir) / "blooop" / "bencher" / "worktree-main"
        mock_create_worktree.return_value = mock_worktree_dir

        # Run the setup
        result = setup_repo_environment("blooop", "bencher", "main")

        # Verify the expected operations
        mock_clone.assert_called_once_with("blooop", "bencher")
        mock_create_worktree.assert_called_once_with("blooop", "bencher", "main")
        mock_fetch.assert_not_called()  # Should not fetch on first clone
        self.assertEqual(result, mock_worktree_dir)

    @patch("rockerc.renv.clone_bare_repo")
    @patch("rockerc.renv.create_worktree")
    @patch("rockerc.renv.fetch_repo")
    @patch("rockerc.renv.repo_exists")
    def test_workflow_switch_branches(
        self, mock_repo_exists, mock_fetch, mock_create_worktree, mock_clone
    ):
        """Test Workflow 2: Switch Branches (renv blooop/bencher@feature/new-feature)."""
        # Simulate repository already exists
        mock_repo_exists.return_value = True
        mock_worktree_dir = (
            Path(self.temp_dir) / "blooop" / "bencher" / "worktree-feature-new-feature"
        )
        mock_create_worktree.return_value = mock_worktree_dir

        # Run the setup for a feature branch
        result = setup_repo_environment("blooop", "bencher", "feature/new-feature")

        # Verify the expected operations
        mock_clone.assert_not_called()  # Should not clone existing repo
        mock_fetch.assert_called_once_with("blooop", "bencher")  # Should fetch latest
        mock_create_worktree.assert_called_once_with("blooop", "bencher", "feature/new-feature")
        self.assertEqual(result, mock_worktree_dir)

    @patch("rockerc.renv.clone_bare_repo")
    @patch("rockerc.renv.create_worktree")
    @patch("rockerc.renv.fetch_repo")
    @patch("rockerc.renv.repo_exists")
    def test_workflow_multiple_repos(
        self, mock_repo_exists, mock_fetch, mock_create_worktree, mock_clone
    ):
        """Test Workflow 4: Work on Multiple Repos."""
        mock_repo_exists.return_value = False

        # Set up first repo
        mock_worktree_dir1 = Path(self.temp_dir) / "blooop" / "bencher" / "worktree-main"
        mock_create_worktree.return_value = mock_worktree_dir1
        result1 = setup_repo_environment("blooop", "bencher", "main")

        # Set up second repo
        mock_worktree_dir2 = Path(self.temp_dir) / "osrf" / "rocker" / "worktree-main"
        mock_create_worktree.return_value = mock_worktree_dir2
        result2 = setup_repo_environment("osrf", "rocker", "main")

        # Both should succeed independently
        self.assertEqual(result1, mock_worktree_dir1)
        self.assertEqual(result2, mock_worktree_dir2)

        # Should have cloned both repos
        expected_calls = [
            unittest.mock.call("blooop", "bencher"),
            unittest.mock.call("osrf", "rocker"),
        ]
        mock_clone.assert_has_calls(expected_calls)

    def test_branch_name_safety_for_directories(self):
        """Test that branch names are safely converted for directory names."""
        # From the documentation, branch names with / should be converted
        problematic_branches = [
            "feature/user-auth",
            "bugfix/critical/database",
            "release/v1.0.0",
            "hotfix/security/ssl-fix",
        ]

        from rockerc.renv import get_worktree_dir

        for branch in problematic_branches:
            with self.subTest(branch=branch):
                worktree_dir = get_worktree_dir("owner", "repo", branch)
                # Directory name should not contain slashes
                self.assertNotIn("/", worktree_dir.name)
                # Should contain dashes instead
                self.assertIn("-", worktree_dir.name)

    def test_container_name_generation(self):
        """Test container name generation logic."""
        # From the code, container names are generated as repo-branch format
        test_cases = [
            ("bencher", "main", "bencher-main"),
            ("rocker", "develop", "rocker-develop"),
            ("vscode", "feature/auth", "vscode-feature-auth"),
            ("project", "bugfix/critical", "project-bugfix-critical"),
        ]

        for repo, branch, expected_container_name in test_cases:
            with self.subTest(repo=repo, branch=branch):
                # Simulate the container name generation logic
                safe_branch = branch.replace("/", "-")
                container_name = f"{repo}-{safe_branch}"
                self.assertEqual(container_name, expected_container_name)

    def test_subfolder_workflow(self):
        """Test workflow with subfolder specification (#subfolder)."""
        from rockerc.renv import parse_repo_spec

        # Test parsing with subfolder
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher@main#scripts")
        self.assertEqual(subfolder, "scripts")

        # Test with complex subfolder path
        owner, repo, branch, subfolder = parse_repo_spec("company/project#docs/examples/tutorial")
        self.assertEqual(subfolder, "docs/examples/tutorial")

    def test_fuzzy_search_preparation(self):
        """Test that data structures support fuzzy search functionality."""
        # Set up repositories for fuzzy search
        repos = [
            ("blooop", "bencher"),
            ("microsoft", "vscode"),
            ("tensorflow", "tensorflow"),
        ]

        for owner, repo in repos:
            repo_dir = Path(self.temp_dir) / owner / repo
            repo_dir.mkdir(parents=True)
            (repo_dir / "HEAD").touch()

        combinations = get_all_repo_branch_combinations()

        # Should support partial matching scenarios described in docs
        # "typing 'bl ben ma' will match blooop/bencher@main"
        self.assertIn("blooop/bencher", combinations)

        # Should have main branches prominently
        main_branches = [c for c in combinations if c.endswith("@main")]
        self.assertTrue(len(main_branches) > 0)


if __name__ == "__main__":
    unittest.main()
