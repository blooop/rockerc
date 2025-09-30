import pathlib
from unittest.mock import patch
from rockerc.core import prepare_launch_plan, derive_container_name


def _base_args():
    return {"args": ["user"], "image": "ubuntu:22.04"}


def test_prepare_launch_plan_reuse_existing_container():
    name = derive_container_name("example")
    with patch("rockerc.core.container_exists", return_value=True):
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
