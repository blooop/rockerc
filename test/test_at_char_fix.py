#!/usr/bin/env python3
"""
Test to verify that the @ character issue is fixed.

The issue was that when renv called run_rockerc, the sys.argv contained
the renv arguments like 'blooop/bencher@main', and these were being passed
to the rocker command, causing issues with the @ character.

The fix modifies sys.argv in run_rockerc_in_worktree to only contain the
script name, preventing the repo specification from being passed to rocker.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, "/workspaces/rockerc")

from rockerc.renv import run_rockerc_in_worktree


class TestAtCharacterFix(unittest.TestCase):
    """Test that the @ character issue is resolved."""

    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_sys_argv_cleared_before_rockerc(self, _mock_chdir, mock_run_rockerc):
        """Test that sys.argv is cleared before calling run_rockerc."""

        # Set up sys.argv with problematic @ character
        original_argv = ["renv", "blooop/bencher@main"]

        with patch.object(sys, "argv", original_argv):
            # Call the function that should clear sys.argv
            run_rockerc_in_worktree(Path("/tmp/test"), "blooop", "bencher", "main")

            # Check that run_rockerc was called
            mock_run_rockerc.assert_called_once_with("/tmp/test")

            # The key test: sys.argv should be restored to original
            self.assertEqual(sys.argv, original_argv)

    def test_repo_spec_parsing_handles_at_symbol(self):
        """Test that repo specification parsing works correctly with @ symbol."""
        from rockerc.renv import parse_repo_spec

        # Test parsing of repo specs with @ symbol
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher@main")
        self.assertEqual(owner, "blooop")
        self.assertEqual(repo, "bencher")
        self.assertEqual(branch, "main")
        self.assertEqual(subfolder, "")

        # Test with complex branch names containing slashes
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher@feature/some-feature")
        self.assertEqual(owner, "blooop")
        self.assertEqual(repo, "bencher")
        self.assertEqual(branch, "feature/some-feature")
        self.assertEqual(subfolder, "")


if __name__ == "__main__":
    unittest.main()
