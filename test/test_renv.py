"""Test basic functionality of renv module."""

# pylint: disable=protected-access  # Tests need to access private methods

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import os

from rockerc.renv import RenvManager


class TestRenvManager:
    """Test cases for RenvManager class."""

    def test_get_renv_home_default(self):
        """Test that default renv home is ~/renv when no environment variable is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {}, clear=True):
                manager = RenvManager(renv_home=temp_dir)
                assert manager.renv_home == Path(temp_dir).resolve()

    def test_get_renv_home_from_env(self):
        """Test that renv home is read from RENV_HOME environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = str(Path(temp_dir) / "test-renv")
            with patch.dict(os.environ, {"RENV_HOME": test_path}):
                manager = RenvManager()
                assert manager.renv_home == Path(test_path).resolve()

    def test_parse_repo_spec_simple(self):
        """Test parsing simple repo specification."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            manager = RenvManager(repo_root=temp_dir)
            repo_name, branch, folder = manager.parse_repo_spec("origin:main")

            assert repo_name == "origin"
            assert branch == "main"
            assert folder is None

    def test_parse_repo_spec_with_folder(self):
        """Test parsing repo specification with folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            manager = RenvManager(repo_root=temp_dir)
            repo_name, branch, folder = manager.parse_repo_spec("origin:main:src/package")

            assert repo_name == "origin"
            assert branch == "main"
            assert folder == "src/package"

    def test_parse_repo_spec_invalid(self):
        """Test parsing edge case repo specifications."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            manager = RenvManager(repo_root=temp_dir)

            # Test that even "invalid" specs get parsed with defaults
            repo, branch, folder = manager.parse_repo_spec("invalid-spec")
            assert repo == "invalid-spec"
            assert branch == "main"  # defaults to main
            assert folder is None

    def test_auto_git_repo_initialization(self):
        """Test that git repository is auto-initialized when not present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Should not raise an error, but auto-initialize git repo
            RenvManager(repo_root=temp_dir)
            assert (Path(temp_dir) / ".git").exists()

    @patch("rockerc.renv.subprocess.run")
    def test_run_git_command(self, mock_run):
        """Test running git commands."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            # Mock successful git command
            mock_result = MagicMock()
            mock_result.stdout = "main\n"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            manager = RenvManager(repo_root=temp_dir)
            result = manager._run_git_command(["branch"])

            assert result == mock_result
            mock_run.assert_called_once()

            # Check that git was called with correct arguments
            call_args = mock_run.call_args
            assert call_args[0][0] == ["git", "branch"]
            assert call_args[1]["cwd"] == Path(temp_dir)

    def test_install_custom_path(self):
        """Test install with custom path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            custom_renv = Path(temp_dir) / "custom-renv"

            with patch("rockerc.renv.RenvManager._set_renv_home") as mock_set_home:
                mock_set_home.return_value = custom_renv

                manager = RenvManager(repo_root=temp_dir)
                manager.install(str(custom_renv))

                mock_set_home.assert_called_once_with(Path(str(custom_renv)))

    @patch("rockerc.renv.subprocess.run")
    @patch("rockerc.rockerc.collect_arguments")
    @patch("rockerc.rockerc.yaml_dict_to_args")
    def test_run_rockerc_command(self, mock_yaml_to_args, mock_collect_args, mock_run):
        """Test running rockerc command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            # Mock rockerc functions
            mock_collect_args.return_value = {"image": "test:latest"}
            mock_yaml_to_args.return_value = "test:latest"

            # Mock successful subprocess run
            mock_run.return_value = MagicMock()

            manager = RenvManager(repo_root=temp_dir)
            result = manager._run_rockerc_command(temp_dir)

            assert result is True
            mock_collect_args.assert_called_once_with(str(temp_dir))
            mock_yaml_to_args.assert_called_once_with({"image": "test:latest"})
            mock_run.assert_called_once()

    @patch("rockerc.rockerc.collect_arguments")
    def test_run_rockerc_command_no_config(self, mock_collect_args):
        """Test running rockerc command when no config is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake git repo
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            # Mock no config found
            mock_collect_args.return_value = {}

            manager = RenvManager(repo_root=temp_dir)
            result = manager._run_rockerc_command(temp_dir)

            assert result is False
            mock_collect_args.assert_called_once_with(str(temp_dir))

    def test_generate_workspace_name(self):
        """Test workspace name generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = RenvManager(renv_home=temp_dir)  # Test simple case
            name = manager.generate_workspace_name("myrepo", "main")
            assert name == "myrepo"  # For main branch, just use repo name

            # Test with org/repo format
            name = manager.generate_workspace_name("blooop/bencher", "main")
            assert name == "bencher"  # For main branch, just use repo name

            # Test with .git suffix
            name = manager.generate_workspace_name("blooop/bencher.git", "feature/test")
            assert name == "bencher-feature-test"

            # Test with invalid characters
            name = manager.generate_workspace_name("my-repo.test", "feature/branch-name")
            assert name == "my-repo-test-feature-branch-name"
