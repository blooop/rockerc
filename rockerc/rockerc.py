import sys
import subprocess
import pathlib
import yaml
import shlex
import os
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
    # image = d.pop("create-dockerfile", None)  # special value

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

    tag = f"{pathlib.Path().absolute().name.lower()}:latest"
    dockerfile_dir = pathlib.Path(dockerfile_path).absolute().parent
    subprocess.call(["docker", "build", "-t", tag, str(dockerfile_dir)])
    return tag


def save_rocker_cmd(split_cmd: str):
    dry_run = split_cmd + ["--mode", "dry-run"]
    try:
        s = subprocess.run(dry_run, capture_output=True, text=True, check=True)
        output = s.stdout
        # Split by "vvvvvv" to discard the top section
        _, after_vvvvvv = output.split("vvvvvv", 1)
        # Split by "^^^^^^" to get the second section
        section_to_save, after_caret = after_vvvvvv.split("^^^^^^", 1)
        # Save the Dockerfile section
        with open("Dockerfile.rocker", "w", encoding="utf-8") as dockerfile:
            dockerfile.write("#This file was autogenerated by rockerc\n")  # Add the shebang
            dockerfile.write(section_to_save.strip())
        # Find the "run this command" section
        run_command_section = after_caret.split("Run this command: ", 1)[-1].strip()
        formatted_script_lines = []
        lines = run_command_section.split()
        formatted_script_lines.append("#!/bin/bash")
        formatted_script_lines.append("# This file was autogenerated by rockerc")
        formatted_script_lines.append("docker run \\")

        for i, line in enumerate(
            lines[2:], start=2
        ):  # Skip 'docker run' which is split in the first two items
            if i < len(lines) - 1:
                formatted_script_lines.append(f"  {line} \\")
            else:
                formatted_script_lines.append(f"  {line}")

        formatted_script_content = "\n".join(formatted_script_lines)

        bash_script_path = "run_dockerfile.sh"
        with open(bash_script_path, "w", encoding="utf-8") as bash_script:
            bash_script.write(formatted_script_content)

        # Make the bash script executable
        os.chmod(bash_script_path, 0o755)

        logging.info(f"Files have been saved:\n - Dockerfile.rocker\n - {bash_script_path} (executable)")
    except subprocess.CalledProcessError as e:
        logging.error("[rockerc] Error: rocker dry-run failed.")
        logging.error(f"[rockerc] Command: {' '.join(dry_run)}")
        logging.error(f"[rockerc] Exit code: {e.returncode}")
        logging.error(f"[rockerc] Output:\n{e.stdout}")
        logging.error(f"[rockerc] Error output:\n{e.stderr}")
        logging.error("[rockerc] This likely means rocker or one of its extensions failed to generate a Dockerfile. Please check your rockerc.yaml and rocker installation.")
        sys.exit(e.returncode)
    except ValueError as e:
        logging.error(f"[rockerc] Error processing the output from rocker dry-run: {e}")
        logging.error("[rockerc] The output format may have changed or rocker failed to generate the expected output.")
        sys.exit(1)


def run_rockerc(path: str = "."):
    """run rockerc by searching for rocker.yaml in the specified directory and passing those arguments to rocker

    Args:
        path (str, optional): Search path for rockerc.yaml files. Defaults to ".".
    """

    logging.basicConfig(level=logging.INFO)
    merged_dict = collect_arguments(path)

    if not merged_dict:
        logging.error("No rockerc.yaml found in the specified directory. Please create a rockerc.yaml file with rocker arguments. See 'rocker -h' for help.")
        sys.exit(1)

    if "args" not in merged_dict:
        logging.error("No 'args' key found in rockerc.yaml. Please add an 'args' list with rocker arguments. See 'rocker -h' for help.")
        sys.exit(1)

    if "dockerfile" in merged_dict:
        logging.info("Building dockerfile...")
        merged_dict["image"] = build_docker(merged_dict["dockerfile"])
        logging.info("disabling 'pull' extension as a Dockerfile is used instead")
        if "pull" in merged_dict["args"]:
            merged_dict["args"].remove("pull")  # can't pull as we just build image
        # remove the dockerfile command as it does not need to be passed onto rocker
        merged_dict.pop("dockerfile")

    create_dockerfile = False
    if "create-dockerfile" in merged_dict["args"]:
        merged_dict["args"].remove("create-dockerfile")
        create_dockerfile = True

    cmd_args = yaml_dict_to_args(merged_dict)
    if len(cmd_args) > 0:
        if len(sys.argv) > 1:
            # this is quite hacky but we only really want 1 argument and to keep the rest as minimal as possible so not using argparse
            dockerfile_arg = "--create-dockerfile"
            if dockerfile_arg in sys.argv:
                sys.argv.remove(dockerfile_arg)
                create_dockerfile = True
            cmd_args += " " + " ".join(sys.argv[1:])

        cmd = f"rocker {cmd_args}"
        logging.info(f"running cmd: {cmd}")
        split_cmd = shlex.split(cmd)
        if create_dockerfile:
            save_rocker_cmd(split_cmd)
        subprocess.run(split_cmd, check=True)
    else:
        logging.error("no arguments found in rockerc.yaml. Please add rocker arguments as described in rocker -h:")
        subprocess.call("rocker -h", shell=True)


if __name__ == "__main__":
    run_rockerc()
