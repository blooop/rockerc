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
import shlex
import subprocess
import time
import logging
import binascii
import os
from typing import List, Sequence, Tuple

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


def container_is_running(container_name: str) -> bool:
    """Return True if a container with this name is currently RUNNING.

    CRITICAL: This function distinguishes between existing containers (docker ps -a)
    and running containers (docker ps). This distinction is essential for proper
    container lifecycle management and preventing attachment errors.

    Use this instead of container_exists() when you need to verify the container
    can accept docker exec commands.
    """
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
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
        LOGGER.error("Failed to query docker for running container: %s", exc)
        return False
    return container_name in result.stdout.splitlines()


def get_container_extensions(container_name: str) -> list[str] | None:
    """Retrieve the stored extension list from a container's environment variables.

    Args:
        container_name: Name of the container to inspect

    Returns:
        Sorted list of extension names, or None if container doesn't exist or env var is missing
    """
    try:
        # Get environment variables from container config
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{range .Config.Env}}{{println .}}{{end}}",
                container_name,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # Parse environment variables to find ROCKERC_EXTENSIONS
        for line in result.stdout.splitlines():
            if line.startswith("ROCKERC_EXTENSIONS="):
                if ext_value := line.split("=", 1)[1]:
                    # Split and sort to match how we store them
                    return sorted(ext_value.split(","))
        return None
    except subprocess.CalledProcessError:
        return None
    except Exception as exc:  # pragma: no cover - unexpected system failure
        LOGGER.warning("Failed to retrieve extensions from container '%s': %s", container_name, exc)
        return None


def extensions_changed(current: list[str], stored: list[str] | None) -> bool:
    """Compare current extension configuration with stored configuration.

    Args:
        current: Current extension list from configuration
        stored: Extension list stored in container label (or None if not available)

    Returns:
        True if extensions have changed or stored is None, False if they match
    """
    # No stored extensions means old container or missing label - treat as changed
    return True if stored is None else sorted(current) != sorted(stored)


def render_extension_comparison_table(current: list[str], stored: list[str] | None) -> str:
    """Return a formatted comparison table showing current vs stored extensions.

    Args:
        current: Current extension list from configuration
        stored: Extension list stored in container (or None if not available)

    Returns:
        Formatted table string showing extension comparison
    """
    # Import here to avoid circular imports
    from .rockerc import _format_table, _colorizer

    col = _colorizer
    current_set = set(current)
    stored_set = set(stored) if stored else set()
    all_extensions = sorted(current_set | stored_set)

    rows = []
    for ext in all_extensions:
        in_current = ext in current_set
        in_stored = ext in stored_set

        # Determine status - use same colors as main extension table
        if in_current and in_stored:
            status = "unchanged"
            status_txt = col.style(status, "GREEN")  # like "loaded"
        elif in_current:
            status = "added"
            status_txt = col.style(status, "GREEN")  # like "loaded"
        else:  # in_stored and not in_current
            status = "removed"
            status_txt = col.style(status, "RED")  # like "blacklisted"

        # Format cells - extension names in CYAN (consistent with main table)
        current_cell = col.style(ext, "CYAN") if in_current else ""
        stored_cell = col.style(ext, "CYAN") if in_stored else ""

        rows.append([current_cell, stored_cell, status_txt])

    # Return formatted table
    if rows:
        headers = ["Current", "Stored", "Status"]
        if col.enabled:
            headers = [col.style(h, "CYAN", bold=True) for h in headers]
        return _format_table(rows, headers)
    return ""


def start_container(container_name: str) -> bool:
    """Start an existing stopped container.

    Returns True if container started successfully, False otherwise.
    """
    LOGGER.info("Starting existing container '%s'...", container_name)
    try:
        subprocess.run(["docker", "start", container_name], check=True, capture_output=True)
        LOGGER.info("Started existing container '%s'", container_name)
        return True
    except subprocess.CalledProcessError as exc:  # pragma: no cover (hard to simulate reliably)
        LOGGER.warning(
            "Failed to start existing container '%s': %s",
            container_name,
            exc,
        )
        return False


def stop_and_remove_container(container_name: str) -> None:
    """Stop and remove an existing container.

    Failure to stop/remove is logged but not fatal; we proceed attempting to create a new container.
    """
    LOGGER.info("Stopping existing container '%s'...", container_name)
    try:
        subprocess.run(["docker", "stop", container_name], check=True, capture_output=True)
        LOGGER.info("Stopped existing container '%s'", container_name)
    except subprocess.CalledProcessError as exc:  # pragma: no cover (hard to simulate reliably)
        LOGGER.warning(
            "Failed to stop existing container '%s': %s. Attempting to continue.",
            container_name,
            exc,
        )

    try:
        subprocess.run(["docker", "rm", container_name], check=True, capture_output=True)
        LOGGER.info("Removed existing container '%s'", container_name)
    except subprocess.CalledProcessError as exc:  # pragma: no cover (hard to simulate reliably)
        LOGGER.warning(
            "Failed to remove existing container '%s': %s. Attempting to continue.",
            container_name,
            exc,
        )


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


def add_extension_env(base_args: str, extensions: list[str]) -> str:
    """Add an environment variable storing the extension list for later comparison.

    Args:
        base_args: Current rocker argument string
        extensions: List of extension names to store

    Returns:
        Updated argument string with environment variable

    Note:
        Extension names are validated to contain only alphanumeric, dash, and underscore
        characters to prevent shell injection issues.
    """
    if not extensions:
        return base_args

    # Validate extension names for safety (alphanumeric, dash, underscore only)
    import re

    for ext in extensions:
        if not re.match(r"^[a-zA-Z0-9_-]+$", ext):
            LOGGER.warning(
                "Extension name '%s' contains invalid characters. Skipping environment storage.",
                ext,
            )
            return base_args

    # Sort to normalize order for comparison
    ext_value = ",".join(sorted(extensions))
    env_arg = f"--env ROCKERC_EXTENSIONS={ext_value}"
    return f"{base_args} {env_arg}".strip()


def ensure_volume_binding(
    base_args: str, container_name: str, path: pathlib.Path, mount_target: str | None = None
) -> str:
    """Ensure a volume mount for the workspace folder.

    Args:
        base_args: Current rocker argument string
        container_name: Name of the container
        path: Host path to mount
        mount_target: Optional custom mount target (default: /workspaces/{container_name})

    Skip if user already provided a --volume referencing the target.
    """
    target = mount_target or f"/workspaces/{container_name}"
    if target in base_args:
        return base_args
    return f"{base_args} --volume {path}:{target}:Z".strip()


def append_volume_binding(base_args: str, host_path: pathlib.Path, target: str) -> str:
    """Append an additional volume mount if it's not already present."""
    # shlex is already imported at the module level

    volume_arg = f"--volume {host_path}:{target}:Z"

    # Parse base_args into tokens
    tokens = shlex.split(base_args)
    # Find all --volume arguments and extract their targets
    existing_targets = set()
    for i, token in enumerate(tokens):
        if token == "--volume" and i + 1 < len(tokens):
            volume_spec = tokens[i + 1]
            parts = volume_spec.split(":")
            if len(parts) >= 2:
                existing_targets.add(parts[1])
        elif token.startswith("--volume="):
            volume_spec = token[len("--volume=") :]
            parts = volume_spec.split(":")
            if len(parts) >= 2:
                existing_targets.add(parts[1])

    if target in existing_targets:
        return base_args
    return f"{base_args} {volume_arg}".strip()


def build_rocker_arg_injections(
    extra_cli: str,
    container_name: str,
    path: pathlib.Path,
    extensions: list[str],
    *,
    always_mount: bool = True,
    extra_volumes: Sequence[Tuple[pathlib.Path, str]] | None = None,
    mount_target: str | None = None,
) -> str:
    """Inject required arguments into the user-specified (or config) rocker args string.

    We always detach and ensure the container is named so we can later docker exec and VS Code attach.
    Additional host→container volume bindings can be supplied via extra_volumes.

    Args:
        extra_cli: Additional CLI arguments
        container_name: Name of the container
        path: Host path to mount
        extensions: List of extension names
        always_mount: Whether to add volume mount (default: True)
        extra_volumes: Additional volume bindings (host_path, target)
        mount_target: Optional custom mount target (default: /workspaces/{container_name})
    """
    argline = extra_cli or ""
    argline = ensure_detached_args(argline)
    argline = ensure_name_args(argline, container_name)
    argline = add_extension_env(argline, extensions)
    if always_mount:
        argline = ensure_volume_binding(argline, container_name, path, mount_target)
    if extra_volumes:
        for host_path, target in extra_volumes:
            argline = append_volume_binding(argline, host_path, target)
    return argline


def launch_rocker(rocker_cmd: list[str]) -> int:
    """Launch rocker command returning exit code.

    We do NOT capture output intentionally; any build logs stream to user.
    """
    LOGGER.info("Running rocker detached: %s", " ".join(rocker_cmd))
    # Enable Docker BuildKit for improved build performance
    env = {**os.environ, "DOCKER_BUILDKIT": "1"}
    proc = subprocess.run(rocker_cmd, check=False, env=env)
    return proc.returncode


def wait_for_container(
    container_name: str,
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    interval: float = DEFAULT_WAIT_INTERVAL,
) -> bool:
    """Poll until container is RUNNING (not just existing) or timeout expires.

    CRITICAL: This function waits for containers to be in RUNNING state, which is
    essential for docker exec attachment. Containers that exist but are stopped
    will cause "container is not running" errors.

    This change fixes a core architectural issue where wait_for_container() was
    checking existence (docker ps -a) instead of running state (docker ps).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if container_is_running(container_name):
            return True
        time.sleep(interval)
    return False


def launch_vscode(container_name: str, container_hex: str, folder_path: str | None = None) -> bool:
    """Attempt to launch VS Code attached to a running container.

    Args:
        container_name: Name of the container
        container_hex: Hex-encoded container name for VSCode URI
        folder_path: Optional container path to open (default: /workspaces/{container_name})

    Returns True on success, False on failure.
    """
    if folder_path is None:
        folder_path = f"/workspaces/{container_name}"
    vscode_uri = f"vscode-remote://attached-container+{container_hex}{folder_path}"
    cmd = ["code", "--folder-uri", vscode_uri]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        LOGGER.info("Launched VS Code on container '%s' at '%s'", container_name, folder_path)
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
    extensions: list[str] | None = None,
    extra_volumes: Sequence[Tuple[pathlib.Path, str]] | None = None,
    mount_target: str | None = None,
) -> LaunchPlan:
    """Prepare rocker command & stop/remove existing container if forced.

    Args:
        args_dict: Configuration dictionary (must contain 'args' key with extension list)
        extra_cli: Additional CLI arguments to pass to rocker
        container_name: Name for the container
        vscode: Whether to attach VS Code
        force: Whether to force rebuild
        path: Working directory path
        extensions: Optional explicit extension list; if None, extracted from args_dict["args"]
        extra_volumes: Additional host→container volume bindings (host path, target path)
        mount_target: Optional custom mount target (default: /workspaces/{container_name})

    Returns:
        LaunchPlan with container configuration and rocker command

    Notes:
        - If container exists and not force: we skip rocker run (rocker_cmd will be empty list)
        - If container exists but extensions changed: require rebuild
    """
    container_hex = container_hex_name(container_name)

    # Extract current extensions from config or use provided list
    current_extensions = extensions if extensions is not None else args_dict.get("args", [])

    # If container exists
    exists = container_exists(container_name)
    created = False

    if exists and not force:
        # Check if extensions have changed
        stored_extensions = get_container_extensions(container_name)
        if extensions_changed(current_extensions, stored_extensions):
            LOGGER.warning(
                "Container '%s' exists but extensions have changed. Stopping and rebuilding...",
                container_name,
            )
            comparison_table = render_extension_comparison_table(
                current_extensions, stored_extensions
            )
            if comparison_table:
                print(comparison_table)
            stop_and_remove_container(container_name)
            exists = False
        elif not container_is_running(container_name):
            # Container exists with correct extensions but is not running - try to start it
            LOGGER.info(
                "Container '%s' exists but is not running. Attempting to start...", container_name
            )
            if not start_container(container_name):
                LOGGER.warning(
                    "Failed to start existing container '%s'. Rebuilding...", container_name
                )
                stop_and_remove_container(container_name)
                exists = False

    if exists and force:
        stop_and_remove_container(container_name)
        exists = False  # treat as not existing for creation phase

    injections = build_rocker_arg_injections(
        extra_cli,
        container_name,
        path,
        current_extensions,
        extra_volumes=extra_volumes,
        mount_target=mount_target,
    )
    # Build base rocker args from config dictionary (copy because yaml_dict_to_args mutates)
    from .rockerc import yaml_dict_to_args  # type: ignore

    args_copy = dict(args_dict)
    rocker_argline = yaml_dict_to_args(args_copy, injections)
    rocker_cmd = []
    if not exists:
        # Build full command list for subprocess (preserve quoted arguments correctly)
        rocker_cmd = ["rocker"] + shlex.split(rocker_argline)
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
    "container_is_running",
    "start_container",
    "prepare_launch_plan",
    "execute_plan",
    "LaunchPlan",
]
