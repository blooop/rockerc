"""
renvsc - Rocker Environment Manager for VS Code
Same as renv but uses rockervsc instead of rocker
"""
import sys
import subprocess
from rockerc.renv import run_rocker_command, run_renv


def run_rockervsc_command(config, command=None, detached=False):
    """Execute rockervsc command - just replace 'rocker' with 'rockervsc'"""
    original_run = subprocess.run
    original_popen = subprocess.Popen

    def patched_run(cmd_parts, **kwargs):
        if cmd_parts and cmd_parts[0] == "rocker":
            cmd_parts[0] = "rockervsc"
        return original_run(cmd_parts, **kwargs)

    def patched_popen(cmd_parts, **kwargs):
        if cmd_parts and cmd_parts[0] == "rocker":
            cmd_parts[0] = "rockervsc"
        return original_popen(cmd_parts, **kwargs)

    subprocess.run = patched_run
    subprocess.Popen = patched_popen

    try:
        return run_rocker_command(config, command, detached)
    finally:
        subprocess.run = original_run
        subprocess.Popen = original_popen


def run_renvsc(args=None):
    """Main entry point - monkey patch and call renv"""
    import rockerc.renv
    original_func = rockerc.renv.run_rocker_command
    rockerc.renv.run_rocker_command = run_rockervsc_command

    try:
        return run_renv(args)
    finally:
        rockerc.renv.run_rocker_command = original_func


def main():
    """Entry point for the renvsc command"""
    sys.exit(run_renvsc())


if __name__ == "__main__":
    main()