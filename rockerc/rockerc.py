import sys
import subprocess
import pathlib
import yaml
import shlex
import os
import logging


def create_default_config(defaults_path: pathlib.Path) -> None:
    """Create a default rockerc.defaults.yaml file with sensible defaults
    
    Args:
        defaults_path: Path where the rockerc.defaults.yaml file should be created
    """
    try:
        # Create parent directory if it doesn't exist
        defaults_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write YAML content with proper formatting
        with open(defaults_path, "w", encoding="utf-8") as f:
            f.write("# rockerc.defaults.yaml - Default configuration for rockerc\n")
            f.write("# This file provides sensible defaults that work in most development environments.\n")
            f.write("# Local rockerc.yaml files can override these settings.\n\n")
            f.write("# Default base image\n")
            f.write("image: ubuntu:24.04\n\n")
            f.write("# Default extensions that are enabled by default\n")
            f.write("args:\n")
            f.write("  - user    # Enable user mapping for file permissions\n")
            f.write("  - pull    # Enable automatic image pulling\n") 
            f.write("  - deps    # Enable dependency installation\n")
            f.write("  - git     # Enable git integration\n")
            # cwd is now ignored by default
            # f.write("  - cwd     # Mount current working directory\n\n")
            f.write("\n")
            f.write("# Extensions that are disabled by default\n")
            f.write("disable_args:\n")
            f.write("  - nvidia  # Disable NVIDIA GPU support by default\n")
            f.write("  - create-dockerfile  # Disable automatic Dockerfile creation\n")
            f.write("  - cwd  # Disable automatic mounting of current working directory\n\n")
            f.write("# Common extensions you might want to add locally:\n")
            f.write("# - x11          # X11 forwarding for GUI applications\n")
            f.write("# - nvidia       # NVIDIA GPU support\n")
            f.write("# - ssh          # SSH agent forwarding\n")
            f.write("# - pixi         # Pixi package manager\n\n")
            f.write("# To override in your local rockerc.yaml:\n")
            f.write("# \n")
            f.write("# To change the base image:\n")
            f.write("# image: python:3.11\n")
            f.write("# \n")
            f.write("# To disable a default extension:\n")
            f.write("# disable_args:\n")
            f.write("#   - pull       # This would disable the pull extension\n")
            f.write("# \n")
            f.write("# To add additional extensions:\n")
            f.write("# args:\n")
            f.write("#   - nvidia     # This would add nvidia to the defaults\n")
        
        print(f"Created default rockerc.defaults.yaml file at {defaults_path}")
    except Exception as e:
        logging.warning(f"Failed to create default rockerc.defaults.yaml file: {e}")


def load_defaults_config(path: str = ".") -> dict:
    """Load rockerc.defaults.yaml and return default configuration
    
    Looks for rockerc.defaults.yaml file in the following order:
    1. Current directory (for local overrides)
    2. ~/.renv/rockerc.defaults.yaml (global renv config)
    3. Home directory (fallback)
    
    If no defaults file is found, creates a default one in ~/.renv/rockerc.defaults.yaml

    Args:
        path (str, optional): Path to search for defaults file. Defaults to ".".

    Returns:
        dict: A dictionary with default configuration
    """
    # Search locations in order of preference
    search_paths = [
        pathlib.Path(path) / "rockerc.defaults.yaml",  # Local directory
        pathlib.Path.home() / "renv" / "rockerc.defaults.yaml",  # Global renv config
        pathlib.Path.home() / "rockerc.defaults.yaml"  # Home directory fallback
    ]
    
    defaults_found = False
    defaults_config = {"args": []}
    
    for defaults_path in search_paths:
        if defaults_path.exists():
            print(f"loading defaults file {defaults_path}")
            try:
                with open(defaults_path, "r", encoding="utf-8") as f:
                    defaults_config = yaml.safe_load(f) or {"args": []}
                defaults_found = True
                break  # Use first found file
            except Exception as e:
                logging.warning(f"Error reading rockerc.defaults.yaml file: {e}")
                continue
    
    # If no defaults file was found, create a default one in the global renv config location
    if not defaults_found:
        global_defaults_path = pathlib.Path.home() / "renv" / "rockerc.defaults.yaml"
        create_default_config(global_defaults_path)
        
        # Now read the newly created file
        try:
            with open(global_defaults_path, "r", encoding="utf-8") as f:
                defaults_config = yaml.safe_load(f) or {"args": []}
        except Exception as e:
            logging.warning(f"Error reading newly created rockerc.defaults.yaml file: {e}")
            # Fallback to hardcoded defaults
            defaults_config = {
                "image": "ubuntu:24.04",
                "args": ["user", "pull", "deps", "git", "cwd"],
                "disable_args": ["nvidia"]
            }

    return defaults_config


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
    
    # Start with defaults
    defaults = load_defaults_config(path)
    merged_dict = {"args": defaults.get("args", []).copy()}
    
    # Include default image if present
    if "image" in defaults:
        merged_dict["image"] = defaults["image"]
    
    # Load and merge local rockerc.yaml files
    local_configs_found = False
    for p in search_path.glob("rockerc.yaml"):
        print(f"loading {p}")
        local_configs_found = True
        
        with open(p.as_posix(), "r", encoding="utf-8") as f:
            local_config = yaml.safe_load(f) or {}
            
            # Handle disable_args - remove these from the current args
            if "disable_args" in local_config:
                disabled_args = local_config["disable_args"]
                if isinstance(disabled_args, list):
                    for arg in disabled_args:
                        if arg in merged_dict["args"]:
                            merged_dict["args"].remove(arg)
                    print(f"Local disabled extensions: {', '.join(disabled_args)}")
                
                # Remove disable_args so it doesn't get passed to rocker
                local_config.pop("disable_args")
            
            # Handle regular args - add these to existing args (avoiding duplicates)
            if "args" in local_config:
                local_args = local_config["args"]
                if isinstance(local_args, list):
                    for arg in local_args:
                        if arg not in merged_dict["args"]:
                            merged_dict["args"].append(arg)
                    print(f"Added extensions: {', '.join([arg for arg in local_args if arg not in defaults.get('args', [])])}")
                
                # Remove args from local_config since we handled it specially
                local_config.pop("args")
            
            # Merge other configuration options (image, dockerfile, etc.)
            for key, value in local_config.items():
                merged_dict[key] = value
    
    # Apply default disable_args at the end - these always override everything else
    if "disable_args" in defaults:
        default_disabled_args = defaults["disable_args"]
        if isinstance(default_disabled_args, list):
            removed_args = []
            for arg in default_disabled_args:
                if arg in merged_dict["args"]:
                    merged_dict["args"].remove(arg)
                    removed_args.append(arg)
            if removed_args:
                print(f"Default disabled extensions (final override): {', '.join(removed_args)}")
    
    # If no local config found, show what defaults are being used
    if not local_configs_found:
        if merged_dict["args"]:
            print(f"Using default extensions: {', '.join(merged_dict['args'])}")
        print("No local rockerc.yaml found - using defaults. Create rockerc.yaml to customize.")
    
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

        logging.info(
            f"Files have been saved:\n - Dockerfile.rocker\n - {bash_script_path} (executable)"
        )
    except subprocess.CalledProcessError as e:
        logging.error("[rockerc] Error: rocker dry-run failed.")
        logging.error(f"[rockerc] Command: {' '.join(dry_run)}")
        logging.error(f"[rockerc] Exit code: {e.returncode}")
        logging.error(f"[rockerc] Output:\n{e.stdout}")
        logging.error(f"[rockerc] Error output:\n{e.stderr}")
        logging.error(
            "[rockerc] This likely means rocker or one of its extensions failed to generate a Dockerfile. Please check your rockerc.yaml and rocker installation."
        )
        sys.exit(e.returncode)
    except ValueError as e:
        logging.error(f"[rockerc] Error processing the output from rocker dry-run: {e}")
        logging.error(
            "[rockerc] The output format may have changed or rocker failed to generate the expected output."
        )
        sys.exit(1)


def container_exists(container_name: str) -> bool:
    """Check if a Docker container with the given name exists.
    
    Args:
        container_name: Name of the container to check
        
    Returns:
        bool: True if container exists, False otherwise
    """
    try:
        result = subprocess.run([
            "docker", "ps", "-a", "--filter", f"name=^/{container_name}$", "--format", "{{.Names}}"
        ], capture_output=True, text=True, check=True)
        return container_name in result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return False


def container_is_running(container_name: str) -> bool:
    """Check if a Docker container is currently running.
    
    Args:
        container_name: Name of the container to check
        
    Returns:
        bool: True if container is running, False otherwise
    """
    try:
        result = subprocess.run([
            "docker", "ps", "--filter", f"name=^/{container_name}$", "--format", "{{.Names}}"
        ], capture_output=True, text=True, check=True)
        return container_name in result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return False


def attach_to_container(container_name: str) -> None:
    """Attach to an existing Docker container.
    
    Args:
        container_name: Name of the container to attach to
    """
    try:
        if not container_is_running(container_name):
            logging.info(f"Container '{container_name}' exists but is not running. Starting it...")
            subprocess.run(["docker", "start", container_name], check=True)
        
        logging.info(f"Attaching to existing container '{container_name}'...")
        # Always start in /workspaces (where the repo is mounted)
        workdir = "/workspaces"
        subprocess.run([
            "docker", "exec", "-it", "-w", workdir, container_name, "/bin/bash"
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to attach to container '{container_name}': {e}")
        # If we can't attach, suggest removing the conflicting container
        logging.error("You may need to remove the existing container:")
        logging.error(f"  docker rm {container_name}")
        logging.error("Or remove it forcefully if it's running:")
        logging.error(f"  docker rm -f {container_name}")
        raise


def extract_container_name_from_args(split_cmd: list) -> str:
    """Extract container name from rocker command arguments.
    
    Args:
        split_cmd: List of command arguments
        
    Returns:
        str: Container name or empty string if not found
    """
    try:
        # Look for --name argument
        name_index = split_cmd.index("--name")
        if name_index + 1 < len(split_cmd):
            return split_cmd[name_index + 1]
    except ValueError:
        pass
    return ""


def run_rockerc(path: str = "."):
    """run rockerc by searching for rocker.yaml in the specified directory and passing those arguments to rocker

    Args:
        path (str, optional): Search path for rockerc.yaml files. Defaults to ".".
    """

    logging.basicConfig(level=logging.INFO)
    merged_dict = collect_arguments(path)

    if not merged_dict:
        logging.error(
            "No rockerc.yaml found in the specified directory. Please create a rockerc.yaml file with rocker arguments. See 'rocker -h' for help."
        )
        sys.exit(1)

    if "args" not in merged_dict:
        logging.error(
            "No 'args' key found in rockerc.yaml. Please add an 'args' list with rocker arguments. See 'rocker -h' for help."
        )
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
    # Do not forcibly set --workdir /workspaces; let caller decide if needed
    if len(cmd_args) > 0:
        if len(sys.argv) > 1:
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
        else:
            container_name = extract_container_name_from_args(split_cmd)
            if container_name and container_exists(container_name):
                logging.info(f"Container '{container_name}' already exists. Attaching to it instead of creating a new one.")
                attach_to_container(container_name)
                return

            try:
                subprocess.run(split_cmd, check=True)
            except subprocess.CalledProcessError as e:
                error_output = str(e)
                if container_name and ("already in use" in error_output or "Conflict" in error_output):
                    logging.info(f"Container name conflict detected. Attempting to attach to existing container '{container_name}'...")
                    if container_exists(container_name):
                        attach_to_container(container_name)
                        return
                    else:
                        logging.error(f"Container '{container_name}' was reported as conflicting but doesn't exist. This is unexpected.")
                raise
    else:
        logging.error(
            "no arguments found in rockerc.yaml. Please add rocker arguments as described in rocker -h:"
        )
        subprocess.call("rocker -h", shell=True)


if __name__ == "__main__":
    run_rockerc()
