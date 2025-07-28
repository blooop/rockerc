import subprocess
import os

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "../scripts/run_renv.sh")


def test_run_renv_script():
    # Ensure the script is executable
    os.chmod(SCRIPT_PATH, 0o755)
    result = subprocess.run(
        [SCRIPT_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, (
        f"Script exited with {result.returncode}, stderr: {result.stderr.decode()}"
    )
    assert "[renv] ERROR:" not in output, f"renv error detected in output: {output}"


# def test_run_renv_script_force_build():
#     os.chmod(SCRIPT_PATH, 0o755)
#     result = subprocess.run(
#         [SCRIPT_PATH, "-f"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
#     )
#     assert result.returncode == 0, (
#         f"Script with -f exited with {result.returncode}, stderr: {result.stderr.decode()}"
#     )
#     # Check output for force build indication
#     output = result.stdout.decode() + result.stderr.decode()
#     assert "force" in output.lower() or "build" in output.lower(), (
#         "Expected force build indication in output"
#     )


# def test_run_renv_script_nocache():
#     os.chmod(SCRIPT_PATH, 0o755)
#     result = subprocess.run(
#         [SCRIPT_PATH, "--nocache"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
#     )
#     assert result.returncode == 0, (
#         f"Script with --nocache exited with {result.returncode}, stderr: {result.stderr.decode()}"
#     )
#     # Check output for nocache indication
#     output = result.stdout.decode() + result.stderr.decode()
#     assert "nocache" in output.lower(), "Expected nocache indication in output"
