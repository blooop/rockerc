import pathlib
from unittest.mock import patch
from rockerc.core import prepare_launch_plan, derive_container_name


def _base_args():
    return {"args": ["user"], "image": "ubuntu:22.04"}


def test_prepare_launch_plan_reuse_existing_container():
    name = derive_container_name("example")
    with patch("rockerc.core.container_exists", return_value=True):
        # Mock get_container_extensions to return matching extensions
        with patch("rockerc.core.get_container_extensions", return_value=["user"]):
            # Mock container is already running
            with patch("rockerc.core.container_is_running", return_value=True):
                plan = prepare_launch_plan(
                    _base_args(), "", name, vscode=False, force=False, path=pathlib.Path(".")
                )
    assert plan.container_name == name
    assert plan.rocker_cmd == []  # reuse means no rocker invocation
    assert plan.created is False


def test_prepare_launch_plan_force_stops_removes_and_recreates():
    name = derive_container_name("example")
    # Simulate exists -> stop/remove -> not exists path
    with patch("rockerc.core.container_exists", side_effect=[True, False]):
        with patch("subprocess.run") as mock_run:
            plan = prepare_launch_plan(
                _base_args(), "", name, vscode=True, force=True, path=pathlib.Path(".")
            )
    # Should have docker stop and docker rm calls
    stop_calls = [c for c in mock_run.call_args_list if c.args[0][:2] == ["docker", "stop"]]
    rm_calls = [c for c in mock_run.call_args_list if c.args[0][:2] == ["docker", "rm"]]
    assert stop_calls, "Expected a docker stop call when force=True and container exists"
    assert rm_calls, "Expected a docker rm call when force=True and container exists"
    assert plan.created is True
    assert plan.rocker_cmd and plan.rocker_cmd[0] == "rocker"


def test_prepare_launch_plan_injects_required_flags():
    name = derive_container_name("example")
    with patch("rockerc.core.container_exists", return_value=False):
        plan = prepare_launch_plan(
            _base_args(), "--env FOO=bar", name, vscode=False, force=False, path=pathlib.Path(".")
        )
    # rocker command should contain detach, name, image-name and volume mount
    joined = " ".join(plan.rocker_cmd)
    assert "--detach" in joined
    assert f"--name {name}" in joined
    assert f"--image-name {name}" in joined
    assert f"/workspaces/{name}" in joined


def test_prepare_launch_plan_adds_extra_volumes():
    name = derive_container_name("example")
    extra_host = pathlib.Path("/repo/.git")
    extra_target = f"/workspaces/{name}/.git"
    with patch("rockerc.core.container_exists", return_value=False):
        plan = prepare_launch_plan(
            _base_args(),
            "",
            name,
            vscode=False,
            force=False,
            path=pathlib.Path("/repo/src"),
            extra_volumes=[(extra_host, extra_target)],
        )
    joined = " ".join(plan.rocker_cmd)
    assert f"--volume /repo/src:/workspaces/{name}:Z" in joined
    assert f"--volume {extra_host}:{extra_target}:Z" in joined


def test_prepare_launch_plan_rebuild_on_extension_change():
    """Test that prepare_launch_plan triggers rebuild when extensions have changed."""
    name = derive_container_name("example")
    with patch("rockerc.core.container_exists", return_value=True):
        # Mock get_container_extensions to return different extensions
        with patch("rockerc.core.get_container_extensions", return_value=["nvidia", "x11"]):
            with patch("rockerc.core.stop_and_remove_container") as mock_stop:
                plan = prepare_launch_plan(
                    _base_args(), "", name, vscode=False, force=False, path=pathlib.Path(".")
                )

    # Should trigger rebuild (stop/remove container)
    mock_stop.assert_called_once_with(name)
    assert plan.created is True
    assert plan.rocker_cmd  # Should have rocker command (not empty)


def test_prepare_launch_plan_starts_stopped_container():
    """Test that prepare_launch_plan starts a stopped container with matching extensions."""
    name = derive_container_name("example")
    with patch("rockerc.core.container_exists", return_value=True):
        # Mock get_container_extensions to return matching extensions
        with patch("rockerc.core.get_container_extensions", return_value=["user"]):
            # Mock container is not running
            with patch("rockerc.core.container_is_running", return_value=False):
                # Mock successful start
                with patch("rockerc.core.start_container", return_value=True) as mock_start:
                    plan = prepare_launch_plan(
                        _base_args(), "", name, vscode=False, force=False, path=pathlib.Path(".")
                    )

    # Should attempt to start the existing container
    mock_start.assert_called_once_with(name)
    assert plan.created is False  # Not created, just started
    assert plan.rocker_cmd == []  # No rocker command needed


def test_prepare_launch_plan_rebuilds_when_start_fails():
    """Test that prepare_launch_plan rebuilds container when start fails."""
    name = derive_container_name("example")
    with patch("rockerc.core.container_exists", side_effect=[True, False]):  # exists, then removed
        # Mock get_container_extensions to return matching extensions
        with patch("rockerc.core.get_container_extensions", return_value=["user"]):
            # Mock container is not running
            with patch("rockerc.core.container_is_running", return_value=False):
                # Mock failed start
                with patch("rockerc.core.start_container", return_value=False):
                    with patch("rockerc.core.stop_and_remove_container") as mock_remove:
                        plan = prepare_launch_plan(
                            _base_args(),
                            "",
                            name,
                            vscode=False,
                            force=False,
                            path=pathlib.Path("."),
                        )

    # Should remove container when start fails
    mock_remove.assert_called_once_with(name)
    assert plan.created is True  # Should create new container
    assert plan.rocker_cmd  # Should have rocker command
