"""
renvvsc - Rocker Environment Manager for VS Code

This module implements the VSCode version of renv following the layered architecture:
- renv collects configuration arguments and passes them to rockerc
- renvvsc functions the same as renv, but passes arguments to rockervsc instead of rockerc

This ensures maximum code reuse while providing VSCode integration.
"""

import sys
import subprocess
import pathlib
import logging
import os
import shlex
import yaml
from typing import List, Optional, Dict, Any

from .rockerc import yaml_dict_to_args, collect_arguments, build_docker, save_rocker_cmd


def launch_vscode_with_workspace(container_name: str, container_hex: str, workspace_folder: str):
    """Launch VSCode attached to a specific workspace folder in the container

    Args:
        container_name (str): name of container to attach to
        container_hex (str): hex of the container for vscode uri
        workspace_folder (str): workspace folder path inside container
    """
    try:
        vscode_uri = f"vscode-remote://attached-container+{container_hex}{workspace_folder}"
        # Launch VSCode in background so it doesn't block the terminal
        subprocess.Popen(
            f"code --folder-uri {vscode_uri}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logging.info(f"Launched VSCode attached to {container_name} at {workspace_folder}")
    except Exception as e:
        logging.error(f"Failed to launch VSCode: {e}")
        raise


def run_rockervsc(path: str = ".") -> int:
    """
    VSCode version of run_rockerc - same logic but calls rockervsc instead of rockerc

    This function replicates the core logic from rockerc.run_rockerc but calls
    rockervsc for VSCode integration instead of raw rocker commands.
    """
    from .rockervsc import run_rockervsc as rockervsc_run

    # Collect and process arguments the same way as rockerc
    args_dict = collect_arguments(path)

    if not args_dict:
        logging.error("No rockerc.yaml files found")
        return 1

    # Handle dockerfile builds if needed
    if "dockerfile" in args_dict:
        image_tag = build_docker(args_dict["dockerfile"])
        args_dict["image"] = image_tag
        logging.info("disabling 'pull' extension as a Dockerfile is used instead")
        if "args" in args_dict and "pull" in args_dict["args"]:
            args_dict["args"].remove("pull")
        args_dict.pop("dockerfile")

    # Handle --create-dockerfile option
    if "--create-dockerfile" in sys.argv:
        # Convert args_dict to command format for save_rocker_cmd
        rocker_args = yaml_dict_to_args(args_dict)
        if rocker_args:
            cmd = f"rocker {rocker_args}"
            split_cmd = shlex.split(cmd)
            save_rocker_cmd(split_cmd)
        return 0

    # Use rockervsc function directly instead of subprocess
    logging.info(f"Using rockervsc function with path: {path}")

    # Extract extra args from sys.argv if needed (excluding --create-dockerfile)
    extra_args = []
    if len(sys.argv) > 1:
        excluded_args = {"--create-dockerfile", path}
        extra_args = [arg for arg in sys.argv[1:] if arg not in excluded_args]

    # Call rockervsc function directly
    return rockervsc_run(path=path, force=False, extra_args=extra_args)


def run_renvvsc(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for renvvsc - same as renv but uses rockervsc

    This function replicates the renv workflow but calls run_rockervsc
    instead of the regular rockerc workflow.
    """
    # Import here to avoid circular imports
    from .renv import (
        RepoSpec,
        fuzzy_select_repo,
        install_shell_completion,
    )
    import argparse

    if args is None:
        args = sys.argv[1:]

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Rocker Environment Manager for VSCode - Seamless multi-repo development with git worktrees and VSCode integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "repo_spec", nargs="?", help="Repository specification: owner/repo[@branch][#subfolder]"
    )

    parser.add_argument("command", nargs="*", help="Command to execute in container")

    parser.add_argument(
        "--no-container", action="store_true", help="Set up worktree only, do not launch container"
    )

    parser.add_argument("--force", "-f", action="store_true", help="Force rebuild container")

    parser.add_argument("--nocache", action="store_true", help="Rebuild container with no cache")

    parser.add_argument("--install", action="store_true", help="Install shell autocompletion")

    parsed_args = parser.parse_args(args)

    if parsed_args.install:
        return install_shell_completion()

    # Interactive fuzzy finder if no repo_spec provided
    if not parsed_args.repo_spec:
        selected = fuzzy_select_repo()
        if not selected:
            logging.error("No repository selected. Usage: renvvsc owner/repo[@branch]")
            parser.print_help()
            return 1
        parsed_args.repo_spec = selected

    try:
        repo_spec = RepoSpec.parse(parsed_args.repo_spec)
        logging.info(f"Working with: {repo_spec}")

        # Use the same container management logic as renv, but with VSCode integration
        return manage_container_vscode(
            repo_spec=repo_spec,
            command=parsed_args.command if parsed_args.command else None,
            force=parsed_args.force,
            nocache=parsed_args.nocache,
            no_container=parsed_args.no_container,
        )

    except ValueError as e:
        logging.error(f"Invalid repository specification: {e}")
        return 1
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e}")
        return e.returncode
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1


def manage_container_vscode(
    repo_spec,
    command: Optional[List[str]] = None,  # pylint: disable=unused-argument
    force: bool = False,
    nocache: bool = False,
    no_container: bool = False,
) -> int:
    """
    VSCode version of manage_container that launches container in detached mode + attaches VSCode

    This launches the container in detached mode and attaches VSCode to it, but does NOT
    enter the container interactively to avoid keystroke dropping issues.
    """
    from .renv import (
        setup_worktree,
        get_worktree_dir,
        get_container_name,
        container_exists,
        container_running,
        build_rocker_config,
        run_rocker_command,
    )

    if no_container:
        setup_worktree(repo_spec)
        logging.info(f"Worktree set up at: {get_worktree_dir(repo_spec)}")
        return 0

    # Set up worktree and get container info
    setup_worktree(repo_spec)
    container_name = get_container_name(repo_spec)

    # Handle force rebuild by removing existing container
    if force and container_exists(container_name):
        logging.info(f"Force rebuild: removing existing container {container_name}")
        subprocess.run(["docker", "rm", "-f", container_name], check=True)

    # Launch or ensure container is running
    if force or not container_exists(container_name) or not container_running(container_name):
        if container_exists(container_name) and not force:
            # Remove stopped container and recreate
            logging.info(f"Removing stopped container {container_name} to recreate with rocker")
            subprocess.run(["docker", "rm", "-f", container_name], check=False)

        # Launch container in detached mode
        logging.info(f"Using rocker to launch container {container_name} in detached mode")
        config = build_rocker_config(repo_spec, force=force, nocache=nocache)
        result = run_rocker_command(config, ["bash"], detached=True)
        if result != 0:
            return result

        # Give container a moment to start up
        import time

        time.sleep(2)
    else:
        logging.info(f"Container {container_name} is already running")

    # Now launch VSCode attached to the workspace folder
    workspace_folder = f"/workspace/{repo_spec.repo}"
    import binascii

    container_hex = binascii.hexlify(container_name.encode()).decode()

    logging.info(f"Launching VSCode attached to container {container_name} at {workspace_folder}")
    try:
        launch_vscode_with_workspace(container_name, container_hex, workspace_folder)
        logging.info("VSCode launched successfully")
        logging.info(f"Container {container_name} is running in detached mode")
        logging.info(
            f"Use 'docker exec -it {container_name} /bin/bash' to enter the container manually"
        )
    except Exception as e:
        logging.warning(f"Failed to launch VSCode: {e}")
        return 1

    return 0


def run_rocker_command_vscode(
    config: Dict[str, Any], command: Optional[List[str]] = None, worktree_dir: pathlib.Path = None
) -> int:
    """
    Execute VSCode container launch using rockervsc approach

    This writes the renv config to a rockerc.yaml in the worktree and uses rockervsc.
    """
    from .rockervsc import run_rockervsc as rockervsc_run_func

    # Extract container name and setup for VSCode
    container_name = config.get("name", "unknown")

    logging.info(f"Launching VSCode container: {container_name}")

    # Save current working directory and change to worktree
    original_cwd = os.getcwd()
    if worktree_dir:
        os.chdir(str(worktree_dir))

    try:
        # Create a rockerc.yaml file in the worktree with the full renv configuration
        # This ensures rockervsc has all the volume mounts, git setup, etc.
        rockerc_path = (
            worktree_dir / "rockerc.yaml" if worktree_dir else pathlib.Path("rockerc.yaml")
        )

        # Convert config to rockerc.yaml format
        rockerc_config = {
            "image": config.get("image", "ubuntu:22.04"),
            "args": config.get("args", ["user", "pull", "git-clone", "git", "persist-image"]),
        }

        # Add volume mounts
        if "volume" in config:
            volumes = config["volume"]
            if isinstance(volumes, list):
                for volume in volumes:
                    rockerc_config.setdefault("volume", []).append(volume)
            else:
                rockerc_config["volume"] = volumes

        # Add other rocker arguments
        for key, value in config.items():
            if key not in ["image", "args", "volume", "name", "hostname"]:
                rockerc_config[key] = value

        # Add container-specific arguments that rockervsc needs
        if "name" in config:
            rockerc_config["name"] = config["name"]
        if "hostname" in config:
            rockerc_config["hostname"] = config["hostname"]

        # Write the rockerc.yaml file
        with open(rockerc_path, "w", encoding="utf-8") as f:
            yaml.dump(rockerc_config, f, default_flow_style=False)

        logging.info(f"Created rockerc.yaml for VSCode in {rockerc_path}")
        logging.info(f"Config: {rockerc_config}")

        # Use rockervsc's run_rockervsc function with the worktree directory
        # This will read the rockerc.yaml we just created and launch VSCode
        result = rockervsc_run_func(
            path=str(worktree_dir) if worktree_dir else ".",
            force=False,  # renv handles force logic
            extra_args=command if command else [],
        )
        return result
    finally:
        # Restore original working directory
        if original_cwd:
            os.chdir(original_cwd)


def main():
    """Entry point for the renvvsc command"""
    sys.exit(run_renvvsc())


if __name__ == "__main__":
    main()
