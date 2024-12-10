import sys
import subprocess
import pathlib
import yaml
import shlex
import os
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
    subprocess.call(["docker", "build", "-t", tag, str(dockerfile_dir)])
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

        split_cmd =shlex.split(cmd)

        dry_run = split_cmd +["--mode","dry-run"]
        # subprocess.call(cmd, shell=True)
        s =subprocess.run(dry_run, capture_output=True,text=True)
        output = s.stdout
        try:
            # Split by "vvvvvv" to discard the top section
            _, after_vvvvvv = output.split("vvvvvv", 1)
            
            # Split by "^^^^^^" to get the second section
            section_to_save, after_caret = after_vvvvvv.split("^^^^^^", 1)
            
            
            # Save the Dockerfile section
            with open("Dockerfile.rocker", "w") as dockerfile:
                dockerfile.write("#This file was autogenerated by rockerc\n")  # Add the shebang
                dockerfile.write(section_to_save.strip())
            

            # Find the "run this command" section
            run_command_section = after_caret.split("Run this command: ", 1)[-1].strip()

            formatted_script_lines = []
            lines = run_command_section.split()
            formatted_script_lines.append("#!/bin/bash")
            formatted_script_lines.append("# This file was autogenerated by rockerc")
            formatted_script_lines.append("docker run \\")
            
            for i, line in enumerate(lines[2:], start=2):  # Skip 'docker run' which is split in the first two items
                if i < len(lines) - 1:
                    formatted_script_lines.append(f"  {line} \\")
                else:
                    formatted_script_lines.append(f"  {line}")
            
            formatted_script_content = "\n".join(formatted_script_lines)

            bash_script_path = "run_dockerfile.sh"
            with open(bash_script_path, "w") as bash_script:
                bash_script.write(formatted_script_content)
            
            # Make the bash script executable
            os.chmod(bash_script_path, 0o755)
            
            print(f"Files have been saved:\n - Dockerfile.rocker\n - {bash_script_path} (executable)")
        except ValueError as e:
            print("Error processing the output:", e)

        subprocess.run(split_cmd, shell=True,capture_output=True,text=True)
    else:
        print(
            "no arguments found in rockerc.yaml. Please add rocker arguments as described in rocker -h:"
        )
        subprocess.call("rocker -h", shell=True)


if __name__ == "__main__":
    run_rockerc()
