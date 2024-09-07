import subprocess
import binascii
from pathlib import Path
from typing import Tuple
import logging


def folder_to_vscode_container(container_name: str, path: Path) -> Tuple[str, str]:
    """given a container name and path, generate the vscode container hex and rocker args needed to launch the container

    Args:
        container_name (str): name of the rocker container
        path (Path): path to load into the rocker container

    Returns:
        Tuple[str, str]: the container_hex and rocker arguments
    """

    container_hex = binascii.hexlify(container_name.encode()).decode()
    rocker_args = f'--image-name {container_name} --name {container_name} --volume {path}:/workspaces/{container_name}:Z --oyr-run-arg " --detach"'

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
