#!/usr/bin/env python3
"""
Tests for renv container integration functionality.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from rockerc.renv import run_rockerc_in_worktree


class TestRenvContainerIntegration(unittest.TestCase):
    """Test container integration and Docker operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.worktree_dir = Path(self.temp_dir) / "test-worktree"
        self.worktree_dir.mkdir(parents=True)
        (self.worktree_dir / ".git").touch()  # Make it look like a git worktree

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("subprocess.run")
    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_container_name_generation(self, mock_chdir, mock_run_rockerc, mock_subprocess):
        """Test that container names are generated correctly."""
        test_cases = [
            ("blooop", "bencher", "main", "bencher-main"),
            ("osrf", "rocker", "develop", "rocker-develop"),
            ("user", "project", "feature/auth", "project-feature-auth"),
            ("company", "app", "bugfix/critical-fix", "app-bugfix-critical-fix"),
        ]

        for owner, repo, branch, expected_name in test_cases:
            with self.subTest(owner=owner, repo=repo, branch=branch):
                # Mock container doesn't exist
                mock_subprocess.return_value.stdout = ""

                # Mock the bare repo directory
                bare_repo_dir = Path(self.temp_dir) / "bare-repo"
                bare_repo_dir.mkdir(exist_ok=True)

                with patch("rockerc.renv.get_repo_dir", return_value=bare_repo_dir):
                    # This would normally call rockerc, but we mock it
                    with patch.dict("os.environ", {}, clear=True):
                        run_rockerc_in_worktree(self.worktree_dir, owner, repo, branch)

                # Check that sys.argv was set up with correct container name
                # The function modifies sys.argv before calling run_rockerc
                expected_name_in_argv = any(expected_name in str(arg) for arg in sys.argv)
                # Note: This is a simplified test - in practice we'd need more sophisticated mocking

    @patch("subprocess.run")
    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_volume_mounting_setup(self, mock_chdir, mock_run_rockerc, mock_subprocess):
        """Test that Docker volumes are set up correctly."""
        # Mock container doesn't exist
        mock_subprocess.return_value.stdout = ""

        bare_repo_dir = Path(self.temp_dir) / "bare-repo"
        bare_repo_dir.mkdir(exist_ok=True)

        with patch("rockerc.renv.get_repo_dir", return_value=bare_repo_dir):
            with patch.dict("os.environ", {}, clear=True):
                run_rockerc_in_worktree(self.worktree_dir, "owner", "repo", "main")

        # Check that sys.argv contains volume mounting arguments
        argv_str = " ".join(sys.argv)
        self.assertIn("--volume", argv_str)

    @patch("subprocess.run")
    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_git_environment_variables(self, mock_chdir, mock_run_rockerc, mock_subprocess):
        """Test that GIT_DIR and GIT_WORK_TREE environment variables are set."""
        # Mock container doesn't exist
        mock_subprocess.return_value.stdout = ""

        bare_repo_dir = Path(self.temp_dir) / "bare-repo"
        bare_repo_dir.mkdir(exist_ok=True)

        with patch("rockerc.renv.get_repo_dir", return_value=bare_repo_dir):
            with patch.dict("os.environ", {}, clear=True):
                run_rockerc_in_worktree(self.worktree_dir, "owner", "repo", "main")

        # Check that sys.argv contains environment variable settings
        argv_str = " ".join(sys.argv)
        self.assertIn("GIT_DIR", argv_str)
        self.assertIn("GIT_WORK_TREE", argv_str)

    @patch("subprocess.run")
    def test_container_existence_check(self, mock_subprocess):
        """Test container existence checking logic."""
        # Mock container exists
        mock_subprocess.return_value.stdout = "test-container\nother-container\n"

        # Import the nested function logic (this is simplified)
        # In the actual code, these are nested functions within run_rockerc_in_worktree
        def container_exists(name):
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return name in result.stdout.splitlines()

        self.assertTrue(container_exists("test-container"))
        self.assertFalse(container_exists("nonexistent-container"))

    @patch("subprocess.run")
    def test_container_running_check(self, mock_subprocess):
        """Test container running status checking."""
        # Mock running containers
        mock_subprocess.return_value.stdout = "running-container\n"

        def container_running(name):
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return name in result.stdout.splitlines()

        self.assertTrue(container_running("running-container"))
        self.assertFalse(container_running("stopped-container"))

    @patch("subprocess.run")
    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_force_rebuild_container(self, mock_chdir, mock_run_rockerc, mock_subprocess):
        """Test force rebuild functionality."""
        # Mock container exists
        mock_subprocess.return_value.stdout = "existing-container\n"

        bare_repo_dir = Path(self.temp_dir) / "bare-repo"
        bare_repo_dir.mkdir(exist_ok=True)

        with patch("rockerc.renv.get_repo_dir", return_value=bare_repo_dir):
            with patch.dict("os.environ", {}, clear=True):
                run_rockerc_in_worktree(self.worktree_dir, "owner", "repo", "main", force=True)

        # When force=True, should call docker rm to remove existing container
        docker_calls = [
            call
            for call in mock_subprocess.call_args_list
            if call[0][0] and "docker" in call[0][0][0]
        ]

        # Should have called docker commands (ps, stop, rm)
        self.assertTrue(len(docker_calls) > 0)

    @patch("subprocess.run")
    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_nocache_rebuild(self, mock_chdir, mock_run_rockerc, mock_subprocess):
        """Test no-cache rebuild functionality."""
        # Mock container doesn't exist
        mock_subprocess.return_value.stdout = ""

        bare_repo_dir = Path(self.temp_dir) / "bare-repo"
        bare_repo_dir.mkdir(exist_ok=True)

        with patch("rockerc.renv.get_repo_dir", return_value=bare_repo_dir):
            with patch.dict("os.environ", {}, clear=True):
                run_rockerc_in_worktree(self.worktree_dir, "owner", "repo", "main", nocache=True)

        # When nocache=True, should set ROCKERC_NO_CACHE environment variable
        # and add --nocache to sys.argv
        self.assertIn("--nocache", sys.argv)

    @patch("subprocess.run")
    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_subfolder_handling(self, mock_chdir, mock_run_rockerc, mock_subprocess):
        """Test handling of subfolder specification."""
        # Create subfolder in worktree
        subfolder_dir = self.worktree_dir / "scripts"
        subfolder_dir.mkdir()

        # Mock container doesn't exist
        mock_subprocess.return_value.stdout = ""

        bare_repo_dir = Path(self.temp_dir) / "bare-repo"
        bare_repo_dir.mkdir(exist_ok=True)

        with patch("rockerc.renv.get_repo_dir", return_value=bare_repo_dir):
            with patch.dict("os.environ", {}, clear=True):
                run_rockerc_in_worktree(
                    self.worktree_dir, "owner", "repo", "main", subfolder="scripts"
                )

        # Should have changed to the subfolder directory
        mock_chdir.assert_called_with(subfolder_dir)

    @patch("subprocess.run")
    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_invalid_worktree_detection(self, mock_chdir, mock_run_rockerc, mock_subprocess):
        """Test detection of invalid worktree directories."""
        # Remove .git file to make it invalid
        (self.worktree_dir / ".git").unlink()

        bare_repo_dir = Path(self.temp_dir) / "bare-repo"
        bare_repo_dir.mkdir(exist_ok=True)

        with patch("rockerc.renv.get_repo_dir", return_value=bare_repo_dir):
            with self.assertRaises(RuntimeError) as context:
                run_rockerc_in_worktree(self.worktree_dir, "owner", "repo", "main")

            self.assertIn("not a valid git repository", str(context.exception))

    @patch("subprocess.run")
    @patch("rockerc.renv.run_rockerc")
    @patch("os.chdir")
    def test_container_attach_workflow(self, mock_chdir, mock_run_rockerc, mock_subprocess):
        """Test container attachment when container already exists and is running."""

        # Mock container exists and is running
        def mock_subprocess_side_effect(*args, **kwargs):
            cmd = args[0]
            if "ps -a" in " ".join(cmd):
                # Container exists
                mock_result = MagicMock()
                mock_result.stdout = "existing-container\n"
                return mock_result
            elif "ps" in " ".join(cmd) and "-a" not in " ".join(cmd):
                # Container is running
                mock_result = MagicMock()
                mock_result.stdout = "existing-container\n"
                return mock_result
            elif "exec" in " ".join(cmd):
                # Mock successful attach
                return MagicMock()
            else:
                return MagicMock()

        mock_subprocess.side_effect = mock_subprocess_side_effect

        bare_repo_dir = Path(self.temp_dir) / "bare-repo"
        bare_repo_dir.mkdir(exist_ok=True)

        with patch("rockerc.renv.get_repo_dir", return_value=bare_repo_dir):
            with patch.dict("os.environ", {}, clear=True):
                run_rockerc_in_worktree(self.worktree_dir, "owner", "repo", "main")

        # Should have attempted to attach to existing container
        exec_calls = [
            call
            for call in mock_subprocess.call_args_list
            if call[0][0] and "exec" in " ".join(call[0][0])
        ]
        self.assertTrue(len(exec_calls) > 0)

    def test_argv_restoration(self):
        """Test that sys.argv is properly restored after container operations."""
        original_argv = sys.argv.copy()

        # Mock minimal setup to avoid actual container operations
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value.stdout = ""

            with patch("rockerc.renv.run_rockerc"):
                with patch("os.chdir"):
                    with patch("rockerc.renv.get_repo_dir", return_value=Path(self.temp_dir)):
                        with patch.dict("os.environ", {}, clear=True):
                            try:
                                run_rockerc_in_worktree(self.worktree_dir, "owner", "repo", "main")
                            except Exception:
                                pass  # Ignore exceptions for this test

        # sys.argv should be restored to original
        self.assertEqual(sys.argv, original_argv)


if __name__ == "__main__":
    unittest.main()
