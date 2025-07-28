import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

# 5. Debug or Manual Management
def test_debug_manual():
    run("renv blooop/manifest_rocker@main --no-container")

if __name__ == "__main__":
    test_debug_manual()
