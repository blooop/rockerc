"""Core shared functionality for rockerc and rockervsc.

This module implements a unified, always-detached container launch flow. It provides:

* Config + argument collection helpers (re-export / wrap existing functions)
* Container lifecycle helpers (exists, rename, wait for up)
* VS Code attachment utilities
* Command synthesis for rocker (ensuring --detach and --name consistency)
* Execution helpers for launching rocker and attaching an interactive shell via docker exec

Design goals:
1. Avoid TTY interference by never letting the foreground rocker process own stdin.
2. Allow optional VS Code attach (--vsc flag) without impacting base container startup.
3. Provide idempotent behavior when container already exists (skip recreate unless --force).
4. Offer simple environmental tunables for wait timing.
"""

from __future__ import annotations

from dataclasses import dataclass
import pathlib
import subprocess
import time
import logging
import binascii
import datetime
import os
from typing import List

# NOTE: Avoid importing from rockerc at module import time to prevent circular imports.
# We will lazily import yaml_dict_to_args inside functions that need it.

LOGGER = logging.getLogger(__name__)


DEFAULT_WAIT_TIMEOUT = float(os.getenv("ROCKERC_WAIT_TIMEOUT", "20"))  # seconds
DEFAULT_WAIT_INTERVAL = float(os.getenv("ROCKERC_WAIT_INTERVAL", "0.25"))  # seconds


@dataclass
class LaunchPlan:
    """Represents the decisions required to launch (or reuse) a rocker container."""

    container_name: str
    container_hex: str
    rocker_cmd: List[str]
    created: bool  # whether we launched a new container this run
    vscode: bool  # whether to attempt VS Code attach


def derive_container_name(explicit: str | None = None) -> str:
    """Derive a stable container name.

    Precedence:
    1. Explicit value (if provided)
    2. Current working directory basename (lowercased)
    """

    if explicit:
        return explicit.lower()
    return pathlib.Path().absolute().name.lower()


def container_hex_name(container_name: str) -> str:
    return binascii.hexlify(container_name.encode()).decode()


def container_exists(container_name: str) -> bool:
    """Return True if a container with this name exists (any state)."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as exc:  # pragma: no cover - unexpected system failure
        LOGGER.error("Failed to query docker for container existence: %s", exc)
        return False
    return container_name in result.stdout.splitlines()


def rename_existing_container(container_name: str) -> str:
    """Rename an existing container to <name>_YYYYmmdd_HHMMSS and return new name.

    Failure to rename is logged but not fatal; we proceed attempting to create a new container.
    """
    new_name = f"{container_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        subprocess.run(
            ["docker", "rename", container_name, new_name], check=True, capture_output=True
        )
        LOGGER.info("Renamed existing container '%s' -> '%s'", container_name, new_name)
    except subprocess.CalledProcessError as exc:  # pragma: no cover (hard to simulate reliably)
        LOGGER.warning(
            "Failed to rename existing container '%s': %s. Attempting to continue.",
            container_name,
            exc,
        )
    return new_name


def ensure_detached_args(base_args: str) -> str:
    """Ensure the rocker argument string contains --detach. (String form injection.)"""
    if "--detach" in base_args:
        return base_args
    return f"{base_args} --detach".strip()


def ensure_name_args(base_args: str, container_name: str) -> str:
    """Ensure rocker args contain --name <container_name> and --image-name <container_name>.

    If user already supplied one or both, we do not duplicate.
    """
    segments = base_args.split()
    if "--name" not in segments:
        segments.extend(["--name", container_name])
    if "--image-name" not in segments:
        segments.extend(["--image-name", container_name])
    return " ".join(segments)


def ensure_volume_binding(base_args: str, container_name: str, path: pathlib.Path) -> str:
    """Ensure a volume mount for the workspace folder to /workspaces/<container_name>.

    Skip if user already provided a --volume referencing /workspaces/<container_name>.
    """
    target = f"/workspaces/{container_name}"
    if target in base_args:
        return base_args
    return f"{base_args} --volume {path}:{target}:Z".strip()


def build_rocker_arg_injections(
    extra_cli: str, container_name: str, path: pathlib.Path, always_mount: bool = True
) -> str:
    """Inject required arguments into the user-specified (or config) rocker args string.

    We always detach and ensure the container is named so we can later docker exec and VS Code attach.
    """
    argline = extra_cli or ""
    argline = ensure_detached_args(argline)
    argline = ensure_name_args(argline, container_name)
    if always_mount:
        argline = ensure_volume_binding(argline, container_name, path)
    return argline


def launch_rocker(rocker_cmd: list[str]) -> int:
    """Launch rocker command returning exit code.

    We do NOT capture output intentionally; any build logs stream to user.
    """
    LOGGER.info("Running rocker detached: %s", " ".join(rocker_cmd))
    proc = subprocess.run(rocker_cmd, check=False)
    return proc.returncode


def wait_for_container(
    container_name: str,
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    interval: float = DEFAULT_WAIT_INTERVAL,
) -> bool:
    """Poll until container exists or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if container_exists(container_name):
            return True
        time.sleep(interval)
    return False


def launch_vscode(container_name: str, container_hex: str) -> bool:
    """Attempt to launch VS Code attached to a running container.

    Returns True on success, False on failure.
    """
    vscode_uri = f"vscode-remote://attached-container+{container_hex}/workspaces/{container_name}"
    cmd = ["code", "--folder-uri", vscode_uri]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        LOGGER.info("Launched VS Code on container '%s'", container_name)
        return True
    except FileNotFoundError:
        LOGGER.warning("VS Code 'code' command not found in PATH; skipping attach.")
    except subprocess.CalledProcessError as exc:
        LOGGER.warning("VS Code attach failed: %s", exc)
    return False


def interactive_shell(container_name: str, shell: str | None = None) -> int:
    """Open an interactive shell into the running container via docker exec.

    Returns the exit code of the docker exec.
    """
    if not shell:
        shell = os.environ.get("SHELL", "/bin/bash")
    exec_cmd = ["docker", "exec", "-it", container_name, shell]
    LOGGER.info("Attaching interactive shell: %s", " ".join(exec_cmd))
    return subprocess.call(exec_cmd)


def prepare_launch_plan(  # pylint: disable=too-many-positional-arguments
    args_dict: dict,
    extra_cli: str,
    container_name: str,
    vscode: bool,
    force: bool,
    path: pathlib.Path,
) -> LaunchPlan:
    """Prepare rocker command & rename existing container if forced.

    If container exists and not force: we skip rocker run (rocker_cmd will be empty list).
    """
    container_hex = container_hex_name(container_name)

    # If container exists
    exists = container_exists(container_name)
    created = False

    if exists and force:
        rename_existing_container(container_name)
        exists = False  # treat as not existing for creation phase

    injections = build_rocker_arg_injections(extra_cli, container_name, path)
    # Build base rocker args from config dictionary (copy because yaml_dict_to_args mutates)
    from .rockerc import yaml_dict_to_args  # type: ignore

    args_copy = dict(args_dict)
    rocker_argline = yaml_dict_to_args(args_copy, injections)
    rocker_cmd = []
    if not exists:
        # Build full command list for subprocess
        rocker_cmd = ["rocker"] + rocker_argline.split()
        created = True
    else:
        LOGGER.info("Container '%s' already exists; reusing.", container_name)

    return LaunchPlan(
        container_name=container_name,
        container_hex=container_hex,
        rocker_cmd=rocker_cmd,
        created=created,
        vscode=vscode,
    )


def execute_plan(plan: LaunchPlan) -> int:
    """Execute a prepared LaunchPlan.

    Steps:
    1. If rocker_cmd present: run it and ensure container appears.
    2. Wait/poll for container.
    3. Optionally attach VS Code.
    4. Open interactive shell.
    """

    if plan.rocker_cmd:
        rc = launch_rocker(plan.rocker_cmd)
        if rc != 0:
            LOGGER.error("rocker failed with exit code %s", rc)
            return rc

    if not wait_for_container(plan.container_name):
        LOGGER.error(
            "Timed out waiting for container '%s' to become available.", plan.container_name
        )
        return 1

    if plan.vscode:
        launch_vscode(plan.container_name, plan.container_hex)

    # open interactive shell (exit code of shell becomes our exit)
    return interactive_shell(plan.container_name)


__all__ = [
    "derive_container_name",
    "container_exists",
    "prepare_launch_plan",
    "execute_plan",
    "LaunchPlan",
]
