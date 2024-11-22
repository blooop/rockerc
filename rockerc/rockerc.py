import sys
import subprocess
import pathlib
import yaml
import logging


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
    for p in search_path.glob("rockerc.yaml"):
        print(f"loading {p}")

        with open(p.as_posix(), "r", encoding="utf-8") as f:
            merged_dict.update(yaml.safe_load(f))
    return merged_dict


def build_docker(dockerfile_path: str = ".") -> str:
    """Build a Docker image from a Dockerfile and return an autogenerated image tag based on where rocker was run.

    Args:
        dockerfile_path (str, optional): Path to the Dockerfile. Defaults to ".".

    Returns:
        str: The tag of the built Docker image.
    """

    tag = f"{pathlib.Path().absolute().name}:latest"
    dockerfile_dir = pathlib.Path(dockerfile_path).absolute().parent
    subprocess.call(f"docker build -t {tag} {dockerfile_dir} ", shell=True)
    return tag


def run_rockerc(path: str = "."):
    """run rockerc by searching for rocker.yaml in the specified directory and passing those arguments to rocker

    Args:
        path (str, optional): Search path for rockerc.yaml files. Defaults to ".".
    """

    merged_dict = collect_arguments(path)

    if "dockerfile" in merged_dict:
        print("Building dockerfile...")
        merged_dict["image"] = build_docker(merged_dict["dockerfile"])
        print("disabling 'pull' extension as a Dockerfile is used instead")
        if "pull" in merged_dict["args"]: 
            merged_dict["args"].remove("pull")  # can't pull as we just build image
        # remove the dockerfile command as it does not need to be passed onto rocker
        merged_dict.pop("dockerfile")

    cmd_args = yaml_dict_to_args(merged_dict)
    if len(cmd_args) > 0:
        if len(sys.argv) > 1:
            cmd_args += " " + " ".join(sys.argv[1:])

        cmd = f"rocker {cmd_args}"
        print(f"running cmd: {cmd}")
        subprocess.call(cmd, shell=True)
    else:
        print(
            "no arguments found in rockerc.yaml. Please add rocker arguments as described in rocker -h:"
        )
        subprocess.call("rocker -h", shell=True)


if __name__ == "__main__":
    run_rockerc()
