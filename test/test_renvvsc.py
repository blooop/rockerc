"""
Tests for renvvsc - VSCode integration thin wrapper
Verifies that renvvsc correctly implements the thin wrapper pattern by
adding --vsc flag and delegating to run_renv().
"""

import sys
from unittest.mock import patch
from rockerc.renvsc import main


class TestRenvvscThinWrapper:
    """Test that renvvsc is a thin wrapper that adds --vsc and delegates to run_renv"""

    @patch("rockerc.renvsc.run_renv")
    def test_main_adds_vsc_flag(self, mock_run_renv):
        """Test that main() adds --vsc flag if not present"""
        # Setup
        sys.argv = ["renvvsc", "owner/repo"]
        mock_run_renv.return_value = 0

        # Execute and catch sys.exit
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

        # Verify --vsc was added
        assert "--vsc" in sys.argv
        mock_run_renv.assert_called_once()

    @patch("rockerc.renvsc.run_renv")
    def test_main_does_not_duplicate_vsc_flag(self, mock_run_renv):
        """Test that main() doesn't add --vsc if already present"""
        # Setup
        sys.argv = ["renvvsc", "--vsc", "owner/repo"]
        mock_run_renv.return_value = 0
        initial_vsc_count = sys.argv.count("--vsc")

        # Execute and catch sys.exit
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

        # Verify --vsc wasn't duplicated
        assert sys.argv.count("--vsc") == initial_vsc_count
        mock_run_renv.assert_called_once()

    @patch("rockerc.renvsc.run_renv")
    def test_main_preserves_all_arguments(self, mock_run_renv):
        """Test that main() preserves all arguments while adding --vsc"""
        # Setup
        sys.argv = ["renvvsc", "--force", "--git", "owner/repo@branch", "pytest"]
        mock_run_renv.return_value = 0

        # Execute and catch sys.exit
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

        # Verify all arguments are preserved
        assert "--force" in sys.argv
        assert "--git" in sys.argv
        assert "owner/repo@branch" in sys.argv
        assert "pytest" in sys.argv
        assert "--vsc" in sys.argv
        mock_run_renv.assert_called_once()
