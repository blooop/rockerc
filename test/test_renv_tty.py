import pytest
from unittest.mock import patch
from rockerc.renv import manage_container, RepoSpec
from rockerc.core import LaunchPlan


@pytest.mark.parametrize(
    "stdin_tty, stdout_tty, expected_flags",
    [
        (True, True, ["-it"]),
        (False, True, []),
        (True, False, []),
        (False, False, []),
    ],
)
@patch("rockerc.renv.setup_branch_copy")
@patch("rockerc.renv.build_rocker_config")
@patch("rockerc.core.prepare_launch_plan")
@patch("rockerc.core.launch_rocker")
@patch("rockerc.core.wait_for_container")
@patch("subprocess.run")
@patch("sys.stdin.isatty")
@patch("sys.stdout.isatty")
@patch("os.chdir")
def test_docker_exec_interactive_flags(
    mock_chdir,
    mock_stdout_isatty,
    mock_stdin_isatty,
    mock_subprocess_run,
    mock_wait_container,
    mock_launch_rocker,
    mock_prepare_plan,
    mock_build_config,
    mock_setup_branch_copy,
    stdin_tty,
    stdout_tty,
    expected_flags,
):
    # pylint: disable=too-many-positional-arguments,unused-argument
    mock_stdin_isatty.return_value = stdin_tty
    mock_stdout_isatty.return_value = stdout_tty
    mock_subprocess_run.return_value.returncode = 0
    mock_setup_branch_copy.return_value = "dummy"
    mock_build_config.return_value = (
        {"args": [], "image": "ubuntu:22.04", "_renv_target_dir": "/test/branch"},
        {},
    )
    mock_plan = LaunchPlan(
        container_name="test_renv.main",
        container_hex="746573745f72656e762d6d61696e",
        rocker_cmd=["rocker", "--detach", "ubuntu:22.04"],
        created=True,
        vscode=False,
        mount_target="/workspaces/test_renv.main",
    )
    mock_prepare_plan.return_value = mock_plan
    mock_launch_rocker.return_value = 0
    mock_wait_container.return_value = True

    spec = RepoSpec("blooop", "test_renv", "main")
    result = manage_container(spec)
    assert result == 0

    # The mount target uses /home/{user}/repo format
    import getpass

    username = getpass.getuser()
    expected_command = (
        ["docker", "exec"]
        + expected_flags
        + [
            "-w",
            f"/home/{username}/test_renv",
            "test_renv.main",
            "/bin/bash",
        ]
    )
    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    assert call_args == expected_command
