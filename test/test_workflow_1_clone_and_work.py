import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

# 1. Clone and Work on a Repo
def test_clone_and_work():
    run("renv blooop/manifest_rocker@main")

if __name__ == "__main__":
    test_clone_and_work()
