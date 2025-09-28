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
from typing import List, Optional, Dict, Any

from .rockerc import yaml_dict_to_args, collect_arguments, build_docker, save_rocker_cmd


def run_rockervsc(path: str = ".") -> int:
    """
    VSCode version of run_rockerc - same logic but calls rockervsc instead of rockerc

    This function replicates the core logic from rockerc.run_rockerc but calls
    rockervsc for VSCode integration instead of raw rocker commands.
    """

    # Collect and process arguments the same way as rockerc
    args_dict = collect_arguments(path)

    if not args_dict:
        logging.error("No rockerc.yaml files found")
        return 1

    # Handle dockerfile builds if needed
    if "dockerfile" in args_dict:
        build_result = build_docker(args_dict["dockerfile"])
        if build_result != 0:
            logging.error("Docker build failed")
            return build_result

        # Update image name and remove pull from args
        dockerfile_path = pathlib.Path(args_dict["dockerfile"])
        if dockerfile_path.is_absolute():
            image_name = dockerfile_path.parent.name
        else:
            image_name = pathlib.Path(path).resolve().name

        args_dict["image"] = image_name
        if "args" in args_dict and "pull" in args_dict["args"]:
            args_dict["args"].remove("pull")

    # Convert to rocker arguments
    rocker_args = yaml_dict_to_args(args_dict)

    # Handle --create-dockerfile option
    if "--create-dockerfile" in sys.argv:
        save_rocker_cmd(rocker_args)
        return 0

    # Use rockervsc instead of calling rocker directly
    cmd = ["rockervsc"] + rocker_args.split()

    logging.info(f"Running rockervsc: {' '.join(cmd)}")

    # Execute rockervsc with the same working directory logic as rockerc
    result = subprocess.run(cmd, cwd=path, check=False)
    return result.returncode


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
    command: Optional[List[str]] = None,
    force: bool = False,
    nocache: bool = False,
    no_container: bool = False,
) -> int:
    """
    VSCode version of manage_container that uses rockervsc

    This replicates the container management logic from renv but calls
    rockervsc instead of rockerc for VSCode integration.
    """
    from .renv import setup_worktree, get_worktree_dir, build_rocker_config

    if no_container:
        setup_worktree(repo_spec)
        logging.info(f"Worktree set up at: {get_worktree_dir(repo_spec)}")
        return 0

    # Set up worktree
    worktree_dir = setup_worktree(repo_spec)

    # Build configuration
    config = build_rocker_config(repo_spec, force=force, nocache=nocache)

    # Use rockervsc instead of the regular rocker command
    return run_rocker_command_vscode(config, command, worktree_dir)


def run_rocker_command_vscode(
    config: Dict[str, Any], command: Optional[List[str]] = None, worktree_dir: pathlib.Path = None
) -> int:
    """
    Execute VSCode container launch using rockervsc approach

    This uses the rockervsc logic directly instead of trying to convert renv config.
    """
    from .rockervsc import run_rockervsc

    # Extract container name and setup for VSCode
    container_name = config.get("name", "unknown")

    logging.info(f"Launching VSCode container: {container_name}")

    # Save current working directory and change to worktree
    original_cwd = os.getcwd()
    if worktree_dir:
        os.chdir(str(worktree_dir))

    try:
        # Use rockervsc's run_rockervsc function with the worktree directory
        # This will read the rockerc.yaml in the worktree and launch VSCode
        result = run_rockervsc(
            path=str(worktree_dir) if worktree_dir else ".",
            force=False,  # renv handles force logic
            extra_args=command if command else []
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
