#!/usr/bin/env python3
"""
Tests for renv fuzzy finder functionality.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rockerc.renv import (
    get_all_repo_branch_combinations,
    fuzzy_select_repo_spec,
)


class TestRenvFuzzyFinder(unittest.TestCase):
    """Test fuzzy finder functionality for interactive repository selection."""

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

    def _setup_test_repos(self):
        """Set up test repositories for fuzzy finder tests."""
        repos = [
            ("blooop", "bencher", ["main", "develop", "feature/auth"]),
            ("microsoft", "vscode", ["main", "insiders"]),
            ("osrf", "rocker", ["main", "master", "melodic"]),
        ]

        for owner, repo, _branches in repos:
            repo_dir = Path(self.temp_dir) / owner / repo
            repo_dir.mkdir(parents=True)
            (repo_dir / "HEAD").touch()

        return repos

    @patch("rockerc.renv.list_branches")
    def test_get_all_repo_branch_combinations_sorting(self, mock_list_branches):
        """Test that repo@branch combinations are properly sorted."""
        self._setup_test_repos()

        # Mock branch listing
        mock_list_branches.side_effect = lambda owner, repo: {
            ("blooop", "bencher"): ["main", "develop", "feature/auth"],
            ("microsoft", "vscode"): ["main", "insiders"],
            ("osrf", "rocker"): ["main", "master", "melodic"],
        }.get((owner, repo), [])

        combinations = get_all_repo_branch_combinations()

        # Should have repos without @ first
        repo_only = [c for c in combinations if "@" not in c]
        repo_with_branch = [c for c in combinations if "@" in c]

        # Repos without @ should come first
        repo_only_indices = [combinations.index(c) for c in repo_only]
        repo_with_branch_indices = [combinations.index(c) for c in repo_with_branch]

        self.assertTrue(max(repo_only_indices) < min(repo_with_branch_indices))

    @patch("rockerc.renv.list_branches")
    def test_get_all_repo_branch_combinations_branch_priority(self, mock_list_branches):
        """Test that main/master branches are prioritized in combinations."""
        self._setup_test_repos()

        # Mock branch listing with different order
        mock_list_branches.side_effect = lambda owner, repo: {
            ("blooop", "bencher"): ["develop", "main", "feature/auth"],  # main not first
            ("osrf", "rocker"): ["melodic", "master", "main"],  # main and master mixed
        }.get((owner, repo), [])

        combinations = get_all_repo_branch_combinations()

        # Find main/master branches for each repo
        bencher_branches = [c for c in combinations if c.startswith("blooop/bencher@")]
        rocker_branches = [c for c in combinations if c.startswith("osrf/rocker@")]

        # main should come before other branches for bencher
        self.assertEqual(bencher_branches[0], "blooop/bencher@main")

        # main should come before master for rocker
        main_index = rocker_branches.index("osrf/rocker@main")
        master_index = rocker_branches.index("osrf/rocker@master")
        self.assertTrue(main_index < master_index)

    @patch("iterfzf.iterfzf")
    def test_fuzzy_select_repo_spec_success(self, mock_iterfzf):
        """Test successful fuzzy selection."""
        self._setup_test_repos()

        # Mock user selection
        mock_iterfzf.return_value = "blooop/bencher@main"

        result = fuzzy_select_repo_spec()

        self.assertEqual(result, "blooop/bencher@main")
        mock_iterfzf.assert_called_once()

    @patch("iterfzf.iterfzf")
    def test_fuzzy_select_repo_spec_cancelled(self, mock_iterfzf):
        """Test fuzzy selection when user cancels."""
        self._setup_test_repos()

        # Mock user cancellation
        mock_iterfzf.side_effect = KeyboardInterrupt()

        result = fuzzy_select_repo_spec()

        self.assertIsNone(result)

    @patch("iterfzf.iterfzf")
    def test_fuzzy_select_repo_spec_no_repos(self, mock_iterfzf):
        """Test fuzzy selection when no repositories exist."""
        # Don't set up any repos

        result = fuzzy_select_repo_spec()

        self.assertIsNone(result)
        mock_iterfzf.assert_not_called()

    @patch("iterfzf.iterfzf")
    @patch("builtins.input")
    def test_fuzzy_select_repo_spec_fallback(self, mock_input, mock_iterfzf):
        """Test fallback to simple input when iterfzf fails."""
        self._setup_test_repos()

        # Mock iterfzf failure and user input fallback
        mock_iterfzf.side_effect = Exception("iterfzf failed")
        mock_input.return_value = "blooop/bencher@develop"

        result = fuzzy_select_repo_spec()

        self.assertEqual(result, "blooop/bencher@develop")
        mock_input.assert_called_once()

    @patch("iterfzf.iterfzf")
    @patch("builtins.input")
    def test_fuzzy_select_repo_spec_fallback_cancelled(self, mock_input, mock_iterfzf):
        """Test fallback when both iterfzf and input are cancelled."""
        self._setup_test_repos()

        # Mock both failing
        mock_iterfzf.side_effect = Exception("iterfzf failed")
        mock_input.side_effect = KeyboardInterrupt()

        result = fuzzy_select_repo_spec()

        self.assertIsNone(result)

    @patch("rockerc.renv.list_branches")
    def test_fuzzy_search_data_structure(self, mock_list_branches):
        """Test that fuzzy search data supports partial matching scenarios."""
        self._setup_test_repos()

        # Mock branch listing
        mock_list_branches.side_effect = lambda owner, repo: {
            ("blooop", "bencher"): ["main", "develop"],
            ("microsoft", "vscode"): ["main"],
            ("osrf", "rocker"): ["main"],
        }.get((owner, repo), [])

        combinations = get_all_repo_branch_combinations()

        # Test scenarios from documentation:
        # "typing 'bl ben ma' will match blooop/bencher@main"

        # Should contain the components for partial matching
        self.assertIn("blooop/bencher", combinations)  # For "bl ben"
        self.assertIn("blooop/bencher@main", combinations)  # For "bl ben ma"

        # Should support fuzzy matching across all combinations
        target_matches = [
            "blooop/bencher",
            "blooop/bencher@main",
            "microsoft/vscode",
            "microsoft/vscode@main",
            "osrf/rocker",
            "osrf/rocker@main",
        ]

        for match in target_matches:
            self.assertIn(match, combinations)

    @patch("iterfzf.iterfzf")
    def test_fuzzy_select_prompt_message(self, mock_iterfzf):
        """Test that fuzzy select uses the correct prompt message."""
        self._setup_test_repos()

        mock_iterfzf.return_value = "test/repo@main"

        fuzzy_select_repo_spec()

        # Check that iterfzf was called with the expected prompt
        call_args = mock_iterfzf.call_args
        self.assertIn("prompt", call_args[1])
        prompt = call_args[1]["prompt"]
        self.assertIn("repo@branch", prompt)
        self.assertIn("bl ben ma", prompt)  # Example from docs

    @patch("rockerc.renv.list_branches")
    def test_combination_generation_with_branch_errors(self, mock_list_branches):
        """Test combination generation when some repos have branch listing errors."""
        self._setup_test_repos()

        # Mock branch listing with some failures
        def mock_branches(owner, repo):
            if owner == "blooop" and repo == "bencher":
                return ["main", "develop"]
            if owner == "microsoft" and repo == "vscode":
                raise RuntimeError("Git error")  # Simulate git error

            return ["main"]

        mock_list_branches.side_effect = mock_branches

        combinations = get_all_repo_branch_combinations()

        # Should still include repos without @ even if branch listing fails
        self.assertIn("blooop/bencher", combinations)
        self.assertIn("microsoft/vscode", combinations)  # Should not be excluded
        self.assertIn("osrf/rocker", combinations)

        # Should include branches for successful repos
        self.assertIn("blooop/bencher@main", combinations)
        self.assertIn("osrf/rocker@main", combinations)

        # Should not crash on branch listing errors
        vscode_branches = [c for c in combinations if c.startswith("microsoft/vscode@")]
        # Should be empty due to the mocked error
        self.assertEqual(len(vscode_branches), 0)

    @patch("rockerc.renv.list_branches")
    def test_empty_branch_list_handling(self, mock_list_branches):
        """Test handling of repositories with no branches."""
        self._setup_test_repos()

        # Mock some repos with empty branch lists
        mock_list_branches.side_effect = lambda owner, repo: {
            ("blooop", "bencher"): [],  # No branches
            ("microsoft", "vscode"): ["main"],
            ("osrf", "rocker"): [],  # No branches
        }.get((owner, repo), [])

        combinations = get_all_repo_branch_combinations()

        # Should still include repo names without @
        self.assertIn("blooop/bencher", combinations)
        self.assertIn("microsoft/vscode", combinations)
        self.assertIn("osrf/rocker", combinations)

        # Should only include @branch for repos with branches
        bencher_branches = [c for c in combinations if c.startswith("blooop/bencher@")]
        vscode_branches = [c for c in combinations if c.startswith("microsoft/vscode@")]
        rocker_branches = [c for c in combinations if c.startswith("osrf/rocker@")]

        self.assertEqual(len(bencher_branches), 0)  # No branches
        self.assertEqual(len(vscode_branches), 1)  # Has main
        self.assertEqual(len(rocker_branches), 0)  # No branches


if __name__ == "__main__":
    unittest.main()
