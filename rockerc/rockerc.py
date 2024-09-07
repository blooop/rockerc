import subprocess
import pathlib
import yaml


def yaml_dict_to_args(d: dict) -> str:
    """Given a dictionary of arguments turn it into an argument string to pass to rocker

    Args:
        d (dict): rocker arguments dictionary

    Returns:
        str: rocker arguments string
    """

    cmd_str = ""

    image = d.pop("image", None)  # special value

    if "args" in d:
        args = d.pop("args")
        for a in args:
            cmd_str += f"--{a} "

    # the rest of the named arguments
    for k, v in d.items():
        cmd_str += f"--{k} {v} "

    # last argument is the image name
    if image is not None:
        cmd_str += image

    return cmd_str


def collect_arguments(path: str = ".") -> dict:
    """Search for rockerc.yaml files and return a merged dictionary

    Args:
        path (str, optional): path to reach for files. Defaults to ".".

    Returns:
        dict: A dictionary of merged rockerc arguments
    """
    search_path = pathlib.Path(path)
    merged_dict = {}
    for p in search_path.rglob("rockerc.yaml"):
        print(f"loading {p}")

        with open(p.as_posix(), "r", encoding="utf-8") as f:
            merged_dict.update(yaml.safe_load(f))
    return merged_dict


import binascii


def container_to_hex(container_name):
    # Get absolute path of the container
    abs_path = os.path.abspath(container_name)

    # Convert the absolute path to a hex value
    hex_value = binascii.hexlify(abs_path.encode()).decode()

    # Get the basename of the container
    base_name = os.path.basename(abs_path)

    # Return the formatted vscode-remote URI
    vscode_uri = f"vscode-remote://dev-container%2B{hex_value}/workspaces/{base_name}"
    return vscode_uri


def run_rockerc(path: str = "."):
    """run rockerc by searching for rocker.yaml in the specified directory and passing those arguments to rocker

    Args:
        path (str, optional): Search path for rockerc.yaml files. Defaults to ".".
    """

    import os
    import pathlib

    # print("cwd", os.getcwd())
    cwd = pathlib.Path()

    folder_name = cwd.absolute().name
    print(folder_name)

    hex_value = binascii.hexlify(folder_name).decode()

    print("hex", hex_value)

    merged_dict = collect_arguments(path)
    cmd_args = yaml_dict_to_args(merged_dict)

    if len(cmd_args) > 0:
        cmd = f"rocker {cmd_args}"
        print(f"running cmd {cmd}")
        subprocess.call(f"{cmd}", shell=True)
    else:
        print(
            "no arguments found in rockerc.yaml. Please add rocker arguments as described in rocker -h:"
        )
        subprocess.call("rocker -h", shell=True)


def entrypoint():
    run_rockerc()


if __name__ == "__main__":
    entrypoint()
