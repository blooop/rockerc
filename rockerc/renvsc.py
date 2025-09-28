"""
renvsc - Rocker Environment Manager for VS Code
Same as renv but launches containers with VSCode integration
"""

import sys
import subprocess
import pathlib
import binascii
import logging
from rockerc.renv import run_renv
from rockerc.rockervsc import launch_vscode, container_exists


def launch_vscode_with_workdir(container_name: str, container_hex: str, workdir: str):
    """Launch VSCode attached to container with specific working directory"""
    try:
        vscode_uri = f"vscode-remote://attached-container+{container_hex}{workdir}"
        subprocess.run(
            f"code --folder-uri {vscode_uri}",
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to launch VSCode: {e}")
        # Fallback to default launch
        launch_vscode(container_name, container_hex)


def run_rockervsc_command(config, command=None, detached=False):  # pylint: disable=unused-argument
    """Execute rocker command with VSCode integration"""
    # Start with the base rocker command
    cmd_parts = ["rocker"]

    # Extract special values that need separate handling
    image = config.get("image", "")
    volumes = []
    if "volume" in config:
        volume_config = config["volume"]
        if isinstance(volume_config, list):
            volumes = volume_config
        else:
            volumes = volume_config.split()

    # Get container name from environment variables or volume mounts
    container_name = None
    worktree_path = None

    # Extract container name from environment variables
    if "env" in config:
        env_vars = config["env"]
        for env_var in env_vars:
            if env_var.startswith("REPO_NAME="):
                container_name = env_var.split("=", 1)[1]
                break

    # Find the worktree path from volume mounts
    for volume in volumes:
        if "/workspace/" in volume and not volume.endswith(".git"):
            host_path = volume.split(":")[0]
            if pathlib.Path(host_path).exists():
                worktree_path = host_path
                break

    if not container_name:
        # Fallback: derive from worktree path
        if worktree_path:
            container_name = pathlib.Path(worktree_path).parent.name
        else:
            container_name = "vscode-container"

    # Add basic extensions from args, but force detach mode for VSCode
    if "args" in config:
        for arg in config["args"]:
            if arg and arg != "persist-image":  # Skip persist-image for VSCode
                cmd_parts.append(f"--{arg}")

    # Add detach mode for VSCode
    cmd_parts.append("--detach")

    # Add name and hostname
    cmd_parts.extend(["--name", container_name])
    cmd_parts.extend(["--hostname", container_name])

    # Add environment variables
    if "env" in config:
        for env_var in config["env"]:
            cmd_parts.extend(["--env", env_var])

    # Add oyr-run-arg if present, but extract workdir for proper VSCode integration
    workdir = None
    if "oyr-run-arg" in config:
        oyr_run_arg = config["oyr-run-arg"]
        if oyr_run_arg:
            # Parse oyr-run-arg to extract workdir
            import shlex
            parsed_args = shlex.split(oyr_run_arg)
            filtered_args = []
            i = 0
            while i < len(parsed_args):
                arg = parsed_args[i]
                if arg.startswith("--workdir="):
                    workdir = arg.split("=", 1)[1]
                elif arg == "--workdir" and i + 1 < len(parsed_args):
                    workdir = parsed_args[i + 1]
                    i += 1  # Skip the next arg
                else:
                    filtered_args.append(arg)
                i += 1

            # Add the filtered oyr-run-arg (without workdir)
            if filtered_args:
                cmd_parts.extend(["--oyr-run-arg", " ".join(filtered_args)])

    # Add workdir separately if found
    if workdir:
        cmd_parts.extend(["--oyr-run-arg", f"--workdir={workdir}"])

    # Add volumes
    for volume in volumes:
        cmd_parts.extend(["--volume", volume])

    # Add -- separator if volumes are present (required by rocker)
    if volumes:
        cmd_parts.append("--")

    # Add image
    if image:
        cmd_parts.append(image)

    # Add command if specified
    if command:
        cmd_parts.extend(command)
    else:
        cmd_parts.append("bash")  # Default command

    # Log the full command for debugging
    cmd_str = " ".join(cmd_parts)
    print(f"INFO: Running rocker for VSCode: {cmd_str}")

    # Use worktree directory as working directory
    cwd = worktree_path

    # Check if container already exists
    if not container_exists(container_name):
        # Run rocker to create the container
        process = subprocess.run(cmd_parts, cwd=cwd, check=False)
        if process.returncode != 0:
            return process.returncode
    else:
        print(f"INFO: Container {container_name} already exists, skipping creation")

    # Launch VSCode with proper working directory
    container_hex = binascii.hexlify(container_name.encode()).decode()

    # Use the same workdir that was passed to the container
    if workdir:
        launch_vscode_with_workdir(container_name, container_hex, workdir)
    else:
        launch_vscode(container_name, container_hex)

    return 0


def run_renvsc(args=None):
    """Main entry point - replace rocker command with rockervsc"""
    import rockerc.renv

    original_func = rockerc.renv.run_rocker_command
    rockerc.renv.run_rocker_command = run_rockervsc_command

    try:
        return run_renv(args)
    finally:
        rockerc.renv.run_rocker_command = original_func


def main():
    """Entry point for the renvsc command"""
    sys.exit(run_renvsc())


if __name__ == "__main__":
    main()
