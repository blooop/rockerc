"""
Tests for renvvsc - VSCode integration architecture
Verifies that renvvsc correctly implements the layered architecture by
calling rockervsc instead of rockerc while maintaining same functionality as renv.
"""

import pathlib
from unittest.mock import Mock, patch
from rockerc.renvsc import (
    run_renvvsc,
    manage_container_vscode,
    run_rocker_command_vscode,
    run_rockervsc,
)
from rockerc.renv import RepoSpec


class TestRenvvscArchitecture:
    """Test the layered architecture implementation"""

    @patch("rockerc.renvsc.subprocess.run")
    @patch("rockerc.renvsc.collect_arguments")
    def test_run_rockervsc_calls_rockervsc_not_rockerc(self, mock_collect, mock_subprocess):
        """Test that run_rockervsc calls rockervsc instead of rockerc"""
        # Setup mock data
        mock_collect.return_value = {"image": "ubuntu:22.04", "args": ["x11", "user", "git"]}
        mock_subprocess.return_value = Mock(returncode=0)

        # Call the function
        result = run_rockervsc(".")

        # Verify it calls rockervsc, not rockerc
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "rockervsc"
        assert "rockerc" not in call_args
        assert "--x11" in call_args
        assert "--user" in call_args
        assert "--git" in call_args
        assert "ubuntu:22.04" in call_args
        assert result == 0

    @patch("rockerc.renvsc.os.chdir")
    @patch("rockerc.renvsc.os.getcwd")
    @patch("rockerc.rockervsc.run_rockervsc")
    def test_run_rocker_command_vscode_calls_rockervsc(self, mock_run_rockervsc, mock_getcwd, mock_chdir):
        """Test that run_rocker_command_vscode calls rockervsc with correct working directory"""
        # Setup mock data
        mock_getcwd.return_value = "/original/dir"
        mock_run_rockervsc.return_value = 0

        config = {"name": "test-container", "image": "ubuntu:22.04", "args": ["x11", "user"]}
        worktree_dir = pathlib.Path("/test/worktree")

        # Call the function
        result = run_rocker_command_vscode(config, worktree_dir=worktree_dir)

        # Verify it changes to worktree directory and calls rockervsc
        mock_chdir.assert_any_call(str(worktree_dir))
        mock_chdir.assert_any_call("/original/dir")  # Restore original directory
        mock_run_rockervsc.assert_called_once_with(
            path=str(worktree_dir),
            force=False,
            extra_args=[]
        )
        assert result == 0

    @patch("rockerc.renvsc.run_rocker_command_vscode")
    @patch("rockerc.renv.setup_worktree")
    @patch("rockerc.renv.build_rocker_config")
    def test_manage_container_vscode_uses_vscode_command(
        self, mock_build_config, mock_setup_worktree, mock_run_rocker_vscode
    ):
        """Test that manage_container_vscode uses the VSCode rocker command"""
        # Setup mocks
        spec = RepoSpec("blooop", "test_repo", "main")
        mock_setup_worktree.return_value = pathlib.Path("/test/worktree")
        mock_build_config.return_value = {"image": "ubuntu:22.04", "args": ["user"]}
        mock_run_rocker_vscode.return_value = 0

        # Call the function
        result = manage_container_vscode(spec)

        # Verify it uses the VSCode version
        assert result == 0
        mock_setup_worktree.assert_called_once_with(spec)
        mock_build_config.assert_called_once_with(spec, force=False, nocache=False)
        mock_run_rocker_vscode.assert_called_once()

    @patch("rockerc.renvsc.manage_container_vscode")
    def test_run_renvvsc_uses_vscode_container_management(self, mock_manage_vscode):
        """Test that run_renvvsc uses VSCode container management"""
        mock_manage_vscode.return_value = 0

        result = run_renvvsc(["blooop/test_repo"])

        assert result == 0
        mock_manage_vscode.assert_called_once()

        # Check the arguments passed
        call_args = mock_manage_vscode.call_args
        repo_spec = call_args[1]["repo_spec"]
        assert repo_spec.owner == "blooop"
        assert repo_spec.repo == "test_repo"
        assert repo_spec.branch == "main"


class TestArgumentPassing:
    """Test that arguments are correctly passed through the layers"""

    @patch("rockerc.renvsc.subprocess.run")
    @patch("rockerc.renvsc.collect_arguments")
    def test_args_passed_from_config_to_rockervsc(self, mock_collect, mock_subprocess):
        """Test that arguments from config are correctly passed to rockervsc"""
        # Setup complex configuration
        mock_collect.return_value = {
            "image": "ros:melodic",
            "args": ["nvidia", "x11", "user", "pull", "git", "deps"],
            "volume": ["/host/path:/container/path"],
            "name": "test-container",
        }
        mock_subprocess.return_value = Mock(returncode=0)

        result = run_rockervsc(".")

        # Verify all arguments are passed correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]

        assert "rockervsc" == call_args[0]
        assert "--nvidia" in call_args
        assert "--x11" in call_args
        assert "--user" in call_args
        assert "--pull" in call_args
        assert "--git" in call_args
        assert "--deps" in call_args
        # Volume arguments are passed as list items in yaml_dict_to_args
        assert "--volume" in call_args
        # The volume path should be in the args after --volume - it's converted to string
        volume_index = call_args.index("--volume")
        assert "['/host/path:/container/path']" == call_args[volume_index + 1]
        assert "--name" in call_args
        assert "test-container" in call_args
        assert "ros:melodic" in call_args
        assert result == 0

    @patch("rockerc.renvsc.run_rocker_command_vscode")
    @patch("rockerc.renv.setup_worktree")
    @patch("rockerc.renv.build_rocker_config")
    def test_renv_config_passed_to_vscode_command(
        self, mock_build_config, mock_setup_worktree, mock_run_rocker_vscode
    ):
        """Test that renv configuration is correctly passed to VSCode command"""
        spec = RepoSpec("owner", "repo", "feature-branch", "src/subfolder")
        mock_setup_worktree.return_value = pathlib.Path("/test/worktree")

        # Setup complex renv configuration
        complex_config = {
            "image": "ubuntu:20.04",
            "args": ["nvidia", "x11", "user", "persist-image"],
            "name": "repo-feature-branch",
            "hostname": "repo-feature-branch",
            "volume": [
                "/host/bare:/workspace/repo.git",
                "/host/worktree:/workspace/repo",
                "/host/worktree-git:/workspace/repo.git/worktrees/worktree-feature-branch",
            ],
            "oyr-run-arg": "--workdir=/workspace/repo/src/subfolder --env=REPO_NAME=repo --env=BRANCH_NAME=feature-branch",
        }
        mock_build_config.return_value = complex_config
        mock_run_rocker_vscode.return_value = 0

        result = manage_container_vscode(spec, command=["pytest"], force=True, nocache=True)

        # Verify the configuration is passed correctly
        assert result == 0
        mock_build_config.assert_called_once_with(spec, force=True, nocache=True)
        mock_run_rocker_vscode.assert_called_once_with(
            complex_config, ["pytest"], mock_setup_worktree.return_value
        )

    @patch("rockerc.renvsc.manage_container_vscode")
    def test_renvvsc_forwards_all_arguments(self, mock_manage_vscode):
        """Test that renvvsc forwards all command line arguments to container management"""
        mock_manage_vscode.return_value = 0

        # Test with various arguments - pytest flags should be part of command
        result = run_renvvsc(["--force", "--nocache", "owner/repo@feature-branch#src", "pytest"])

        assert result == 0
        mock_manage_vscode.assert_called_once()

        call_kwargs = mock_manage_vscode.call_args[1]

        # Check repo spec parsing
        repo_spec = call_kwargs["repo_spec"]
        assert repo_spec.owner == "owner"
        assert repo_spec.repo == "repo"
        assert repo_spec.branch == "feature-branch"
        assert repo_spec.subfolder == "src"

        # Check other arguments
        assert call_kwargs["command"] == ["pytest"]
        assert call_kwargs["force"] is True
        assert call_kwargs["nocache"] is True


class TestVSCodeSpecificBehavior:
    """Test VSCode-specific behaviors and differences from regular renv"""

    @patch("rockerc.renvsc.subprocess.run")
    @patch("rockerc.renvsc.collect_arguments")
    def test_dockerfile_handling_calls_rockervsc(self, mock_collect, mock_subprocess):
        """Test that dockerfile builds still call rockervsc instead of rockerc"""
        # Setup dockerfile configuration
        mock_collect.return_value = {"dockerfile": "Dockerfile", "args": ["user", "x11"]}
        mock_subprocess.return_value = Mock(returncode=0)

        with patch("rockerc.renvsc.build_docker") as mock_build:
            mock_build.return_value = 0

            result = run_rockervsc(".")

            # Verify dockerfile build and rockervsc call
            mock_build.assert_called_once_with("Dockerfile")
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            assert call_args[0] == "rockervsc"
            assert result == 0

    @patch("rockerc.renvsc.os.chdir")
    @patch("rockerc.renvsc.os.getcwd")
    @patch("rockerc.rockervsc.run_rockervsc")
    def test_command_passed_to_rockervsc(self, mock_run_rockervsc, mock_getcwd, mock_chdir):
        """Test that custom commands are passed to rockervsc"""
        mock_getcwd.return_value = "/original/dir"
        mock_run_rockervsc.return_value = 0

        config = {"name": "test-container", "image": "ubuntu:22.04", "args": ["user"]}
        command = ["python", "script.py", "--arg"]

        result = run_rocker_command_vscode(config, command=command)

        # Verify command is passed to rockervsc
        mock_run_rockervsc.assert_called_once_with(
            path=".",
            force=False,
            extra_args=command
        )
        assert result == 0

    @patch("rockerc.renvsc.run_rocker_command_vscode")
    @patch("rockerc.renv.setup_worktree")
    @patch("rockerc.renv.build_rocker_config")
    def test_no_container_mode_vscode(
        self, mock_build_config, mock_setup_worktree, mock_run_rocker_vscode
    ):
        """Test that --no-container mode works correctly with VSCode"""
        spec = RepoSpec("owner", "repo", "main")
        mock_setup_worktree.return_value = pathlib.Path("/test/worktree")

        result = manage_container_vscode(spec, no_container=True)

        # Should only setup worktree, not call rocker
        assert result == 0
        mock_setup_worktree.assert_called_once_with(spec)
        mock_build_config.assert_not_called()
        mock_run_rocker_vscode.assert_not_called()


class TestCommandLineInterface:
    """Test the command line interface compatibility with renv"""

    @patch("rockerc.renvsc.manage_container_vscode")
    def test_help_and_argument_parsing(self, mock_manage_vscode):
        """Test that argument parsing works the same as renv"""
        mock_manage_vscode.return_value = 0

        # Test various argument combinations
        test_cases = [
            (["owner/repo"], {"force": False, "nocache": False, "no_container": False}),
            (["owner/repo", "--force"], {"force": True, "nocache": False, "no_container": False}),
            (["owner/repo", "--nocache"], {"force": False, "nocache": True, "no_container": False}),
            (
                ["owner/repo", "--no-container"],
                {"force": False, "nocache": False, "no_container": True},
            ),
            (
                ["owner/repo", "-f", "--nocache"],
                {"force": True, "nocache": True, "no_container": False},
            ),
        ]

        for args, expected_flags in test_cases:
            mock_manage_vscode.reset_mock()
            result = run_renvvsc(args)

            assert result == 0
            mock_manage_vscode.assert_called_once()
            call_kwargs = mock_manage_vscode.call_args[1]

            for flag, expected_value in expected_flags.items():
                assert call_kwargs[flag] == expected_value

    @patch("rockerc.renv.fuzzy_select_repo")
    def test_fuzzy_selection_compatibility(self, mock_fuzzy_select):
        """Test that fuzzy selection works the same as renv"""
        mock_fuzzy_select.return_value = None

        result = run_renvvsc([])

        assert result == 1
        mock_fuzzy_select.assert_called_once()

    @patch("rockerc.renv.install_shell_completion")
    def test_install_completion_compatibility(self, mock_install):
        """Test that --install flag works the same as renv"""
        mock_install.return_value = 0

        result = run_renvvsc(["--install"])

        assert result == 0
        mock_install.assert_called_once()


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_repo_spec(self):
        """Test that invalid repo specs are handled correctly"""
        result = run_renvvsc(["invalid-spec"])
        assert result == 1

    @patch("rockerc.renvsc.subprocess.run")
    @patch("rockerc.renvsc.collect_arguments")
    def test_no_config_found(self, mock_collect, mock_subprocess):
        """Test behavior when no rockerc.yaml is found"""
        mock_collect.return_value = {}

        result = run_rockervsc(".")

        assert result == 1
        mock_subprocess.assert_not_called()

    @patch("rockerc.renvsc.subprocess.run")
    @patch("rockerc.renvsc.collect_arguments")
    def test_build_docker_failure(self, mock_collect, mock_subprocess):
        """Test handling of docker build failures"""
        mock_collect.return_value = {"dockerfile": "Dockerfile", "args": ["user"]}

        with patch("rockerc.renvsc.build_docker") as mock_build:
            mock_build.return_value = 1  # Build failure

            result = run_rockervsc(".")

            assert result == 1
            mock_subprocess.assert_not_called()

    @patch("rockerc.renvsc.os.chdir")
    @patch("rockerc.renvsc.os.getcwd")
    @patch("rockerc.rockervsc.run_rockervsc")
    def test_rockervsc_command_failure(self, mock_run_rockervsc, mock_getcwd, mock_chdir):
        """Test handling of rockervsc command failures"""
        mock_getcwd.return_value = "/original/dir"
        mock_run_rockervsc.return_value = 1  # Command failure

        config = {"name": "test-container", "image": "ubuntu:22.04", "args": ["user"]}

        result = run_rocker_command_vscode(config)

        assert result == 1
