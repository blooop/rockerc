import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

# 6. Run a Command Directly in the Container
def test_run_command_in_container():
    run("renv osrf/rocker git status")

if __name__ == "__main__":
    test_run_command_in_container()
