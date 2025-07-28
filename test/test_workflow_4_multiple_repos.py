import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

# 4. Work on Multiple Repos
def test_multiple_repos():
    run("renv osrf/rocker@main")

if __name__ == "__main__":
    test_multiple_repos()
