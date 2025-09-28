"""
renvsc - Rocker Environment Manager for VS Code
Same as renv but launches containers with VSCode integration
"""

import sys
import subprocess
import binascii
import logging
from rockerc.renv import run_renv, run_rocker_command
from rockerc.rockervsc import launch_vscode


def extract_workdir_from_config(config):
    """Extract workdir from oyr-run-arg in config"""
    if "oyr-run-arg" not in config:
        return None

    oyr_run_arg = config["oyr-run-arg"]
    if "--workdir=" not in oyr_run_arg:
        return None

    # Parse workdir from oyr-run-arg
    import shlex

    try:
        parsed_args = shlex.split(oyr_run_arg)
        for arg in parsed_args:
            if arg.startswith("--workdir="):
                return arg.split("=", 1)[1]
    except ValueError:
        pass  # shlex parsing failed
    return None


def run_rocker_command_vscode(config, command=None, detached=False):  # pylint: disable=unused-argument
    """Execute rocker command in detached mode for VSCode integration"""
    # Get container name from the config
    container_name = config.get("name", "unknown")

    # Modify config for VSCode: force detached mode and remove persist-image
    vscode_config = config.copy()

    # Remove persist-image from args (incompatible with detached mode)
    if "args" in vscode_config:
        vscode_config["args"] = [arg for arg in vscode_config["args"] if arg != "persist-image"]

    # Run rocker in detached mode
    result = run_rocker_command(vscode_config, command, detached=True)

    # If successful, launch VSCode
    if result == 0:
        container_hex = binascii.hexlify(container_name.encode()).decode()

        # Extract workdir from oyr-run-arg if present
        workdir = extract_workdir_from_config(config)

        # Launch VSCode with workdir if available
        if workdir:
            launch_vscode_with_workdir(container_name, container_hex, workdir)
        else:
            launch_vscode(container_name, container_hex)

    return result


def launch_vscode_with_workdir(container_name: str, container_hex: str, workdir: str):
    """Launch VSCode attached to container with specific working directory"""
    try:
        vscode_uri = f"vscode-remote://attached-container+{container_hex}{workdir}"
        subprocess.run(
            f"code --folder-uri {vscode_uri}",
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to launch VSCode with workdir: {e}")
        # Fallback to default launch
        launch_vscode(container_name, container_hex)


def run_renvsc(args=None):
    """Main entry point - use renv but with VSCode integration"""
    import rockerc.renv

    # Replace the rocker command function with our VSCode version
    original_func = rockerc.renv.run_rocker_command
    rockerc.renv.run_rocker_command = run_rocker_command_vscode

    try:
        return run_renv(args)
    finally:
        rockerc.renv.run_rocker_command = original_func


def main():
    """Entry point for the renvsc command"""
    sys.exit(run_renvsc())


if __name__ == "__main__":
    main()
