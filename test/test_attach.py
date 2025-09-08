import json
from types import SimpleNamespace

import pytest

from rockerc.rockerc import (
    build_oyr_run_args_from_inspect,
    extract_docker_run_args_from_container,
)


@pytest.fixture
def sample_inspect_dict():
    return {
        "Name": "/myapp",
        "Config": {
            "Image": "ubuntu:22.04",
            "Env": [
                "FOO=bar",
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            ],
            "User": "1000:1000",
            "WorkingDir": "/work",
        },
        "HostConfig": {
            "NetworkMode": "bridge",
            "Binds": ["/host/a:/container/a:rw"],
            "PortBindings": {
                "80/tcp": [
                    {
                        "HostIp": "0.0.0.0",
                        "HostPort": "8080",
                    }
                ]
            },
            "Privileged": False,
            "CapAdd": ["SYS_PTRACE"],
            "SecurityOpt": ["seccomp=unconfined"],
            "Devices": [
                {
                    "PathOnHost": "/dev/dri",
                    "PathInContainer": "/dev/dri",
                    "CgroupPermissions": "rwm",
                }
            ],
            "ShmSize": 67108864,
            "Tmpfs": {"/tmp": "uid=1000,gid=1000,mode=1777"},
            "Sysctls": {"net.core.somaxconn": "1024"},
            "ReadonlyRootfs": False,
            "ExtraHosts": ["host.docker.internal:host-gateway"],
            "Runtime": "runc",
        },
    }


def test_build_oyr_run_args_from_inspect(sample_inspect_dict):
    args = build_oyr_run_args_from_inspect(sample_inspect_dict)

    # basic expectations
    assert "--network bridge" in args
    assert "-v /host/a:/container/a:rw" in args
    assert "-p 0.0.0.0:8080:80/tcp" in args
    assert "-e FOO=bar" in args
    assert "--user 1000:1000" in args
    assert "--workdir /work" in args
    assert "--cap-add SYS_PTRACE" in args
    assert "--security-opt seccomp=unconfined" in args
    assert "--device /dev/dri:/dev/dri:rwm" in args
    assert "--shm-size 67108864" in args
    assert "--tmpfs /tmp:uid=1000,gid=1000,mode=1777" in args
    assert "--sysctl net.core.somaxconn=1024" in args
    assert "--add-host host.docker.internal:host-gateway" in args


def test_extract_docker_run_args_from_container(monkeypatch, sample_inspect_dict):
    # monkeypatch inspect_container to return our sample
    from rockerc import rockerc as rr

    monkeypatch.setattr(rr, "inspect_container", lambda container: sample_inspect_dict)
    # ensure name isn't taken
    monkeypatch.setattr(rr, "_container_exists", lambda name: False)

    out = extract_docker_run_args_from_container("myapp")
    assert out["image"] == "ubuntu:22.04"
    # name is quoted for rocker consumption
    assert out["name"].strip('"') == "myapp-rockerc"
    assert "-v /host/a:/container/a:rw" in out.get("oyr-run-arg", "")


def test_run_rockerc_with_from_container(monkeypatch, tmp_path, sample_inspect_dict):
    from rockerc import rockerc as rr

    # write a minimal rockerc.yaml in temp dir
    (tmp_path / "rockerc.yaml").write_text(
        """
args:
  - x11
        """.strip()
    )

    # Inspect container returns our sample
    monkeypatch.setattr(rr, "inspect_container", lambda container: sample_inspect_dict)
    monkeypatch.setattr(rr, "_container_exists", lambda name: False)

    calls = {}

    def fake_run(cmd, check=False, capture_output=False, text=False):
        # capture the rocker command invocation
        if isinstance(cmd, list) and cmd and cmd[0] == "rocker":
            calls["rocker_cmd"] = cmd
            # simulate success
            return SimpleNamespace(returncode=0)
        # if any other commands accidentally reach here, raise to fail the test
        raise AssertionError(f"Unexpected subprocess.run call: {cmd}")

    monkeypatch.setattr(rr.subprocess, "run", fake_run)

    # Simulate CLI args
    saved_argv = rr.sys.argv.copy()
    try:
        rr.sys.argv = ["rockerc", "--from-container", "myapp"]
        rr.run_rockerc(path=tmp_path.as_posix())
    finally:
        rr.sys.argv = saved_argv

    rocker_cmd = calls.get("rocker_cmd")
    assert rocker_cmd is not None
    # Contains x11 extension and image
    assert "--x11" in rocker_cmd
    assert "ubuntu:22.04" in rocker_cmd
    # Contains our derived run args flag
    assert any("--oyr-run-arg" in x for x in rocker_cmd)
