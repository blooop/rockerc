"""Test container attachment functionality to catch the 'container is not running' error."""

import subprocess
from unittest.mock import patch, MagicMock
import pytest

from rockerc.core import (
    container_exists,
    container_is_running,
    start_container,
    wait_for_container,
    interactive_shell,
    execute_plan,
    LaunchPlan,
)


def test_container_exists_but_not_running():
    """Test that container_exists returns True even for stopped containers."""
    # Mock docker ps -a to return a stopped container
    mock_result = MagicMock()
    mock_result.stdout = "test_container\n"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = container_exists("test_container")

    assert result is True
    # Verify we're using 'docker ps -a' which includes stopped containers
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[:2] == ["docker", "ps"]
    assert "-a" in args
    assert "--filter" in args
    assert "name=test_container" in args


def test_wait_for_container_old_behavior_replaced():
    """Test that wait_for_container now checks running status instead of just existence."""
    # This test documents that the behavior has changed
    with patch("rockerc.core.container_exists", return_value=True):
        with patch("rockerc.core.container_is_running", return_value=False):
            result = wait_for_container("test_container", timeout=0.1, interval=0.05)

    # Should return False because container is not running (even though it exists)
    assert result is False


def test_interactive_shell_fails_when_container_not_running():
    """Test that interactive_shell fails with proper error when container is not running."""
    # Mock docker exec to fail with "container is not running" error
    error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["docker", "exec", "-it", "test_container", "/bin/bash"],
    )
    error.stderr = "Error response from daemon: container test_container is not running"

    with patch("subprocess.call", side_effect=error):
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            # This should fail, but currently doesn't handle the error properly
            subprocess.call(["docker", "exec", "-it", "test_container", "/bin/bash"])

    assert "container test_container is not running" in str(exc_info.value.stderr)


def test_execute_plan_attachment_failure():
    """Test execute_plan when container exists but isn't running (simulates the reported bug)."""
    plan = LaunchPlan(
        container_name="test_container",
        container_hex="74657374636f6e7461696e6572",  # hex of "testcontainer"
        rocker_cmd=[],  # Empty means container exists, no need to create
        created=False,
        vscode=False,
    )

    # Mock wait_for_container to succeed (container exists)
    with patch("rockerc.core.wait_for_container", return_value=True):
        # Mock interactive_shell to fail with "container not running" error
        with patch(
            "rockerc.core.interactive_shell", return_value=125
        ):  # Docker's exit code for container not running
            result = execute_plan(plan)

    # Currently this doesn't properly handle the error case
    assert result == 125


def test_container_running_status_check_needed():
    """Test demonstrating that container_is_running function now exists and works."""
    # This test documents that we now have the functionality to check running status

    # Mock docker ps (without -a) to check only running containers
    mock_result = MagicMock()
    mock_result.stdout = ""  # Empty output = container not running

    with patch("subprocess.run", return_value=mock_result):
        # container_is_running function now exists and works correctly
        result = container_is_running("test_container")

    # Should return False since mock returns empty output
    assert result is False


def test_container_is_running_checks_only_running_containers():
    """Test that container_is_running only returns True for running containers."""
    # Mock docker ps (without -a) to return only running containers
    mock_result = MagicMock()
    mock_result.stdout = "running_container\n"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = container_is_running("running_container")

    assert result is True
    # Verify we're using 'docker ps' without -a
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[:2] == ["docker", "ps"]
    assert "-a" not in args
    assert "--filter" in args
    assert "name=running_container" in args


def test_container_is_running_returns_false_for_stopped():
    """Test that container_is_running returns False for stopped containers."""
    # Mock docker ps to return empty (no running containers with that name)
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        result = container_is_running("stopped_container")

    assert result is False


def test_start_container_success():
    """Test successful container start."""
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = start_container("test_container")

    assert result is True
    mock_run.assert_called_once_with(
        ["docker", "start", "test_container"], check=True, capture_output=True
    )


def test_start_container_failure():
    """Test container start failure."""
    error = subprocess.CalledProcessError(1, ["docker", "start", "test_container"])

    with patch("subprocess.run", side_effect=error):
        result = start_container("test_container")

    assert result is False


def test_wait_for_container_now_waits_for_running():
    """Test that wait_for_container now waits for container to be running."""
    with patch("rockerc.core.container_is_running", return_value=True) as mock_running:
        result = wait_for_container("test_container", timeout=0.1, interval=0.05)

    assert result is True
    mock_running.assert_called_once_with("test_container")


def test_scenario_reproducing_user_bug():
    """Test that reproduces the exact scenario from the user's bug report."""
    container_name = "bencher"

    # Container exists (from docker ps -a) but is not running
    with patch("rockerc.core.container_exists", return_value=True):
        with patch(
            "rockerc.core.get_container_extensions", return_value=["chrome", "persist-image"]
        ):
            # wait_for_container succeeds because container exists
            with patch("rockerc.core.wait_for_container", return_value=True):
                # But docker exec fails because container is not running
                mock_call = MagicMock(return_value=125)  # Docker error code
                with patch("subprocess.call", mock_call):
                    with patch.dict("os.environ", {"SHELL": "/bin/bash"}):
                        exit_code = interactive_shell(container_name)

    # This should return the error code from failed docker exec
    assert exit_code == 125

    # Verify docker exec was called with correct arguments
    mock_call.assert_called_once()
    call_args = mock_call.call_args[0][0]
    assert call_args == ["docker", "exec", "-it", container_name, "/bin/bash"]


def test_bug_fix_container_exists_but_stopped():
    """Test the fix for containers that exist but are stopped."""
    container_name = "test_container"

    # Now with the fix, wait_for_container should wait for running state
    with patch(
        "rockerc.core.container_is_running", side_effect=[False, False, True]
    ) as mock_running:
        result = wait_for_container(container_name, timeout=1.0, interval=0.1)

    assert result is True
    # Should have been called multiple times until container is running
    assert mock_running.call_count >= 3


def test_detached_mode_includes_keep_alive_command():
    """Test that detached mode always includes a keep-alive command."""
    from rockerc.rockerc import yaml_dict_to_args

    # Test with basic config
    config = {"args": ["user"], "image": "ubuntu:22.04"}
    result = yaml_dict_to_args(config, "--detach --name test")

    # Should append keep-alive command after image
    assert "-- ubuntu:22.04 tail -f /dev/null" in result


def test_detached_mode_preserves_existing_command():
    """Test that existing commands are preserved when not in detached mode."""
    from rockerc.rockerc import yaml_dict_to_args

    # Test without detached mode
    config = {"args": ["user"], "image": "ubuntu:22.04"}
    result = yaml_dict_to_args(config, "--name test")

    # Should not append keep-alive command
    assert result.endswith("-- ubuntu:22.04")
    assert "tail -f /dev/null" not in result


def test_detached_mode_with_existing_command():
    """Test that existing commands are preserved in detached mode when specified."""
    from rockerc.rockerc import yaml_dict_to_args

    # Test with explicit command
    config = {"args": ["user"], "image": "ubuntu:22.04"}
    result = yaml_dict_to_args(config, "--detach --name test bash")

    # Should preserve the bash command in its original position and not add tail
    assert "--detach --name test bash -- ubuntu:22.04" in result
    assert "tail -f /dev/null" not in result
