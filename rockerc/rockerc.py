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
    """Search for rocker-compose.yaml files and return a merged dictionary

    Args:
        path (str, optional): path to reach for files. Defaults to ".".

    Returns:
        dict: A dictionary of merged rocker-compose arguments
    """
    search_path = pathlib.Path(path)
    merged_dict = {}
    for p in search_path.rglob("rocker-compose.yaml"):
        print(f"loading {p}")

        with open(p.as_posix(), "r", encoding="utf-8") as f:
            merged_dict.update(yaml.safe_load(f))
    return merged_dict


def run_rockerc(path: str = "."):
    merged_dict = collect_arguments(path)
    cmd_args = yaml_dict_to_args(merged_dict)

    if len(cmd_args) > 0:
        cmd = f"rocker {cmd_args}"
        print(f"running cmd {cmd}")
        subprocess.call(f"{cmd}", shell=True)
    else:
        print(
            "no arguments found in rocker-compose.yaml. Please add rocker arguments as described in rocker -h:"
        )
        subprocess.call("rocker -h", shell=True)


def entrypoint():
    run_rockerc()


if __name__ == "__main__":
    entrypoint()
