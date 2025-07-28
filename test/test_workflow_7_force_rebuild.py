import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

# 7. Force Rebuild Container
def test_force_rebuild():
    run("renv blooop/manifest_rocker@main -f")

if __name__ == "__main__":
    test_force_rebuild()
