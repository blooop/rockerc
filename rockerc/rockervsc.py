import subprocess
import binascii
import shlex
from pathlib import Path
from typing import Tuple
import logging
import pathlib
import datetime
import argparse


def folder_to_vscode_container(container_name: str, path: Path) -> Tuple[str, str]:
    """given a container name and path, generate the vscode container hex and rocker args needed to launch the container

    Args:
        container_name (str): name of the rocker container
        path (Path): path to load into the rocker container

    Returns:
        Tuple[str, str]: the container_hex and rocker arguments
    """

    container_hex = binascii.hexlify(container_name.encode()).decode()
    rocker_args = f"--image-name {container_name} --name {container_name} --volume {path}:/workspaces/{container_name}:Z --detach"

    return container_hex, rocker_args


def launch_vscode(container_name: str, container_hex: str):
    """launches vscode and attached it to a specified container name (using a container hex)

    Args:
        container_name (str): name of container to attach to
        container_hex (str): hex of the container for vscode uri
    """
    try:
        subprocess.run(
            f"code --folder-uri vscode-remote://attached-container+{container_hex}/workspaces/{container_name}",
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to launch VSCode: {e}")
        raise


def container_exists(container_name: str) -> bool:
    """
    Check if a Docker container with the specified name exists.

    Args:
        container_name (str): The name of the Docker container to check.

    Returns:
        bool: True if the container exists, False otherwise.

    Raises:
        RuntimeError: If an error occurs while executing the Docker command.
    """
    # Run the Docker command to filter containers by name
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    )

    # Check if the container name appears in the output
    return container_name in result.stdout.splitlines()


def run_rockervsc(path: str = ".", force: bool = False, extra_args: list = None):
    """run rockerc by searching for rocker.yaml in the specified directory and passing those arguments to rocker

    Args:
        path (str, optional): Search path for rockerc.yaml files. Defaults to ".".
        force (bool, optional): Force rename of existing container. Defaults to False.
        extra_args (list, optional): Additional arguments to pass to rockerc. Defaults to None.
    """
    from .rockerc import collect_arguments, yaml_dict_to_args, build_docker

    cwd = pathlib.Path().absolute()
    container_name = cwd.name.lower()

    # Use rockerc functions directly instead of subprocess
    merged_dict = collect_arguments(path)

    if not merged_dict:
        logging.error(
            "No rockerc.yaml found in the specified directory. Please create a rockerc.yaml file with rocker arguments. See 'rocker -h' for help."
        )
        return 1

    if "args" not in merged_dict:
        logging.error(
            "No 'args' key found in rockerc.yaml. Please add an 'args' list with rocker arguments. See 'rocker -h' for help."
        )
        return 1

    if "dockerfile" in merged_dict:
        logging.info("Building dockerfile...")
        merged_dict["image"] = build_docker(merged_dict["dockerfile"])
        logging.info("disabling 'pull' extension as a Dockerfile is used instead")
        if "pull" in merged_dict["args"]:
            merged_dict["args"].remove("pull")
        merged_dict.pop("dockerfile")

    # Build extra arguments for rocker
    container_hex, rocker_args = folder_to_vscode_container(container_name, pathlib.Path(path))

    # Add extra arguments if provided
    extra_args_str = ""
    if extra_args:
        extra_args_str = " ".join(extra_args)

    # Combine all arguments
    combined_extra_args = f"{extra_args_str} {rocker_args}".strip()

    cmd_args = yaml_dict_to_args(merged_dict, combined_extra_args)

    if not container_exists(container_name):
        if len(cmd_args) > 0:
            cmd = f"rocker {cmd_args}"
            print(f"running cmd: {cmd}")
            split_cmd = shlex.split(cmd)
            subprocess.run(split_cmd, check=False, cwd=path)
        else:
            logging.error("no arguments found in rockerc.yaml")
            return 1
    else:
        if force:
            print(f"Force option enabled. Renaming existing container '{container_name}'")
            subprocess.run(
                [
                    "docker",
                    "rename",
                    container_name,
                    f"{container_name}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}",
                ],
                check=False,
            )
            if len(cmd_args) > 0:
                cmd = f"rocker {cmd_args}"
                print(f"running cmd: {cmd}")
                split_cmd = shlex.split(cmd)
                subprocess.run(split_cmd, check=False, cwd=path)
            else:
                logging.error("no arguments found in rockerc.yaml")
                return 1
        else:
            print("container already running, attaching vscode to container")

    launch_vscode(container_name, container_hex)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Run rockervsc with specified options")
    parser.add_argument(
        "--force", "-f", action="store_true", help="Force rename of existing container"
    )
    parser.add_argument("path", nargs="?", default=".", help="Search path for rockerc.yaml files")

    # Parse known args and pass the rest to rockerc
    args, unknown_args = parser.parse_known_args()
    run_rockervsc(path=args.path, force=args.force, extra_args=unknown_args)


if __name__ == "__main__":
    main()
