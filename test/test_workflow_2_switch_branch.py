import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

# 2. Switch Branches (Isolated Worktrees)
def test_switch_branch():
    run("renv blooop/manifest_rocker@feature/new-feature")

if __name__ == "__main__":
    test_switch_branch()
