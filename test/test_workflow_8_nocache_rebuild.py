import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

# 8. Rebuild Container With No Cache
def test_nocache_rebuild():
    run("renv blooop/manifest_rocker@main --nocache")

if __name__ == "__main__":
    test_nocache_rebuild()
