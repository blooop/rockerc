import subprocess
import binascii
from pathlib import Path
from typing import Tuple


def folder_to_vscode_container(container_name: str, path: Path) -> Tuple[str, str, str]:

    container_hex = binascii.hexlify(container_name.encode()).decode()
    rocker_args = f'--image-name {container_name} --name {container_name} --volume {path}:/workspaces/{container_name}:Z --oyr-run-arg " --detach"'

    return container_hex, rocker_args


def launch_vscode(container_name: str, container_hex: str):
    subprocess.call(
        f"code --folder-uri vscode-remote://attached-container+{container_hex}/workspaces/{container_name}",
        shell=True,
    )
