import subprocess
import binascii
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

    cwd = pathlib.Path().absolute()
    container_name = cwd.name.lower()

    cmd = "rockerc"
    if extra_args:
        cmd += " " + " ".join(extra_args)
    if path != ".":
        cmd += f" {path}"

    container_hex, rocker_args = folder_to_vscode_container(container_name, path)
    cmd += f" {rocker_args}"

    if not container_exists(container_name):
        print(f"running cmd: {cmd}")
        subprocess.run(cmd, shell=True, check=False, cwd=path)
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
            print(f"running cmd: {cmd}")
            subprocess.run(cmd, shell=True, check=False, cwd=path)
        else:
            print("container already running, attaching vscode to container")
    launch_vscode(container_name, container_hex)


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
