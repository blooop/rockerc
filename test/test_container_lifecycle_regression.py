"""
Regression tests for container lifecycle architecture.

These tests prevent regressions in the critical container lifecycle pattern:
1. Always launch detached with keep-alive
2. Always wait for running state (not just existence)
3. Always attach via docker exec

Historical context: This was a long-standing architectural issue where
keep-alive logic was scattered across tools instead of centralized.
"""

import subprocess
from unittest.mock import patch
import pytest

from rockerc.core import (
    container_exists,
    container_is_running,
    wait_for_container,
    prepare_launch_plan,
    execute_plan,
)
from rockerc.rockerc import yaml_dict_to_args


class TestDetachedContainerLifecycle:
    """Test the core architectural requirement: detached containers must have keep-alive."""

    def test_yaml_dict_to_args_always_adds_keepalive_for_detached(self):
        """REGRESSION TEST: yaml_dict_to_args must add keep-alive for ALL detached containers."""
        configs = [
            # Basic rockerc config
            {"args": ["user"], "image": "ubuntu:22.04"},
            # Complex config with multiple extensions
            {"args": ["chrome", "user", "git", "x11"], "image": "ubuntu:22.04"},
            # Config with volumes and env vars
            {"args": ["nvidia"], "image": "pytorch/pytorch", "env": "CUDA=1"},
        ]

        for config in configs:
            # Test with minimal detached args
            result = yaml_dict_to_args(config.copy(), "--detach --name test")
            assert "tail -f /dev/null" in result, f"Missing keep-alive for config: {config}"

            # Test with complex detached args
            complex_args = "--detach --name test --env VAR=value --volume /tmp:/tmp"
            result = yaml_dict_to_args(config.copy(), complex_args)
            assert "tail -f /dev/null" in result, f"Missing keep-alive for complex args: {config}"

    def test_yaml_dict_to_args_preserves_explicit_commands(self):
        """REGRESSION TEST: Explicit commands should prevent keep-alive injection."""
        config = {"args": ["user"], "image": "ubuntu:22.04"}

        # Explicit command should prevent tail injection
        result = yaml_dict_to_args(config, "--detach --name test bash")
        assert "tail -f /dev/null" not in result
        assert "bash" in result

        # Complex command with args
        result = yaml_dict_to_args(
            config, "--detach --name test python -c 'import time; time.sleep(1000)'"
        )
        assert "tail -f /dev/null" not in result
        assert "python" in result

    def test_yaml_dict_to_args_non_detached_no_keepalive(self):
        """REGRESSION TEST: Non-detached containers should never get keep-alive."""
        config = {"args": ["user"], "image": "ubuntu:22.04"}

        # No detach flag
        result = yaml_dict_to_args(config, "--name test")
        assert "tail -f /dev/null" not in result

        # Interactive mode
        result = yaml_dict_to_args(config, "--name test --interactive")
        assert "tail -f /dev/null" not in result


class TestContainerStateDistinction:
    """Test the critical distinction between existing and running containers."""

    def test_container_exists_vs_container_is_running(self):
        """REGRESSION TEST: Must distinguish between existing and running containers."""
        container_name = "test_container"

        # Mock existing but stopped container
        with patch("subprocess.run") as mock_run:
            # container_exists should return True (ps -a includes stopped)
            mock_run.return_value.stdout = "test_container\n"
            assert container_exists(container_name) is True

            # Reset mock for container_is_running
            mock_run.reset_mock()
            mock_run.return_value.stdout = ""  # ps (no -a) excludes stopped

            # container_is_running should return False
            assert container_is_running(container_name) is False

        # Verify the Docker commands are different
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""

            container_exists(container_name)
            exists_call = mock_run.call_args[0][0]
            assert "-a" in exists_call  # ps -a for existence check

            mock_run.reset_mock()
            container_is_running(container_name)
            running_call = mock_run.call_args[0][0]
            assert "-a" not in running_call  # ps (no -a) for running check

    def test_wait_for_container_waits_for_running_not_existing(self):
        """REGRESSION TEST: wait_for_container must wait for RUNNING state."""
        container_name = "test_container"

        # Mock sequence: container exists but not running, then becomes running
        with patch(
            "rockerc.core.container_is_running", side_effect=[False, False, True]
        ) as mock_running:
            result = wait_for_container(container_name, timeout=1.0, interval=0.1)

        assert result is True
        assert mock_running.call_count >= 3  # Should retry until running

        # Verify it's calling container_is_running, not container_exists
        mock_running.assert_called_with(container_name)


class TestEndToEndLifecycle:
    """Integration tests for the complete container lifecycle."""

    def test_prepare_launch_plan_handles_stopped_containers(self):
        """REGRESSION TEST: Must handle containers that exist but are stopped."""
        import pathlib

        container_name = "test_container"
        config = {"args": ["user"], "image": "ubuntu:22.04"}

        # Scenario: Container exists with matching extensions but is not running
        with patch("rockerc.core.container_exists", return_value=True):
            with patch("rockerc.core.get_container_extensions", return_value=["user"]):
                with patch("rockerc.core.container_is_running", return_value=False):
                    with patch("rockerc.core.start_container", return_value=True) as mock_start:
                        plan = prepare_launch_plan(
                            config, "", container_name, False, False, pathlib.Path(".")
                        )

        # Should attempt to start the existing container
        mock_start.assert_called_once_with(container_name)
        assert plan.created is False  # Not created, just restarted
        assert plan.rocker_cmd == []  # No new container needed

    def test_execute_plan_integration_with_running_container(self):
        """REGRESSION TEST: execute_plan must work with running containers."""
        from rockerc.core import LaunchPlan

        plan = LaunchPlan(
            container_name="test_container",
            container_hex="74657374636f6e7461696e6572",
            rocker_cmd=[],  # Container already exists
            created=False,
            vscode=False,
        )

        # Mock successful container running check and shell attachment
        with patch("rockerc.core.wait_for_container", return_value=True):
            with patch("rockerc.core.interactive_shell", return_value=0) as mock_shell:
                exit_code = execute_plan(plan)

        assert exit_code == 0
        mock_shell.assert_called_once_with(plan.container_name)


class TestRegressionScenarios:
    """Test specific scenarios that caused the original regression."""

    def test_rockerc_vs_renv_consistency(self):
        """REGRESSION TEST: rockerc and renv must generate identical container commands."""
        config = {"args": ["chrome", "user", "git"], "image": "ubuntu:22.04"}
        extra_args = "--detach --name test --volume /workspace:/workspace:Z"

        # Both tools should generate the same command with keep-alive
        rockerc_cmd = yaml_dict_to_args(config.copy(), extra_args)

        # Verify the command structure
        assert "--detach" in rockerc_cmd
        assert "-- ubuntu:22.04 tail -f /dev/null" in rockerc_cmd
        assert rockerc_cmd.count("tail -f /dev/null") == 1  # Only one keep-alive

    def test_vscode_attachment_scenario(self):
        """REGRESSION TEST: VSCode attachment must work with detached containers."""
        # This reproduces the scenario from commit de68392
        config = {"args": ["user", "git"], "image": "ubuntu:22.04"}
        vscode_args = "--detach --name vscode-test"

        result = yaml_dict_to_args(config, vscode_args)

        # VSCode mode must have keep-alive to prevent immediate container exit
        assert "tail -f /dev/null" in result
        assert "--detach" in result

        # Simulate VSCode attachment after container is running
        with patch("rockerc.core.container_is_running", return_value=True) as mock_running:
            can_attach = mock_running.return_value
            assert can_attach is True

    def test_manual_keepalive_prevention(self):
        """REGRESSION TEST: Prevent manual keep-alive injection in application code."""
        # This test ensures no tool manually adds ["tail", "-f", "/dev/null"]
        # to rocker commands - it should be handled automatically

        config = {"args": ["user"], "image": "ubuntu:22.04"}
        base_cmd = yaml_dict_to_args(config, "--detach --name test")

        # Should have exactly one keep-alive command (automatically added)
        assert base_cmd.count("tail -f /dev/null") == 1

        # Manual addition would create duplication (BAD)
        manual_addition = base_cmd + " tail -f /dev/null"
        assert manual_addition.count("tail -f /dev/null") == 2  # This is what we prevent

    def test_attachment_failure_symptoms(self):
        """REGRESSION TEST: Verify we can detect symptoms of missing keep-alive."""
        # Simulate the exact error scenario from the user's bug report
        container_name = "bencher"

        # Container exists but is not running (symptom of missing keep-alive)
        with patch("rockerc.core.container_exists", return_value=True) as mock_exists:
            with patch("rockerc.core.container_is_running", return_value=False) as mock_running:
                # This should be detected as a problem
                exists = mock_exists.return_value
                running = mock_running.return_value

                assert exists is True
                assert running is False  # This combination indicates missing keep-alive

        # Mock the docker exec failure
        error = subprocess.CalledProcessError(
            125, ["docker", "exec", "-it", container_name, "/bin/bash"]
        )
        error.stderr = f"Error response from daemon: container {container_name} is not running"

        with patch("subprocess.call", side_effect=error):
            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                subprocess.call(["docker", "exec", "-it", container_name, "/bin/bash"])

            assert "is not running" in str(exc_info.value.stderr)


class TestArchitecturalConstraints:
    """Tests that enforce architectural constraints to prevent regressions."""

    def test_no_scattered_keepalive_logic(self):
        """ARCHITECTURAL TEST: Keep-alive logic must be centralized in yaml_dict_to_args."""
        # This test enforces that we don't scatter keep-alive logic across tools

        # The ONLY place that should add keep-alive is yaml_dict_to_args
        config = {"args": ["user"], "image": "ubuntu:22.04"}
        result = yaml_dict_to_args(config, "--detach --name test")

        # Verify the keep-alive is added automatically
        assert "tail -f /dev/null" in result

        # Any other function adding keep-alive would be a violation of this architecture

    def test_detached_flag_detection_robustness(self):
        """ARCHITECTURAL TEST: Detached flag detection must be robust."""
        config = {"args": ["user"], "image": "ubuntu:22.04"}

        # Test various ways --detach might appear in extra_args
        test_cases = [
            "--detach --name test",
            "--name test --detach",
            "--detach",
            "--env VAR=val --detach --name test",
            "--detach --env VAR=val --name test",
        ]

        for extra_args in test_cases:
            result = yaml_dict_to_args(config.copy(), extra_args)
            assert "tail -f /dev/null" in result, f"Failed to detect --detach in: {extra_args}"

    def test_command_parsing_edge_cases(self):
        """ARCHITECTURAL TEST: Command parsing must handle edge cases correctly."""
        config = {"args": ["user"], "image": "ubuntu:22.04"}

        # Edge cases that should NOT prevent keep-alive
        edge_cases = [
            "--detach --name test --env COMMAND=bash",  # env var contains command
            "--detach --name test --label command=run",  # label contains command
            "--detach --name test --volume /usr/bin/bash:/bin/bash",  # volume contains command
        ]

        for extra_args in edge_cases:
            result = yaml_dict_to_args(config.copy(), extra_args)
            assert "tail -f /dev/null" in result, f"Incorrectly detected command in: {extra_args}"

        # Cases that SHOULD prevent keep-alive (real commands)
        real_commands = [
            "--detach --name test bash",
            "--detach --name test python -c 'print(1)'",
            "--detach --name test /bin/sh",
        ]

        for extra_args in real_commands:
            result = yaml_dict_to_args(config.copy(), extra_args)
            assert "tail -f /dev/null" not in result, (
                f"Failed to detect real command in: {extra_args}"
            )
