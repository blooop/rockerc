# import subprocess
# import os

# WORKFLOW_PATH = os.path.join(
#     os.path.dirname(__file__), "workflows/test_workflow_1_clone_and_work.sh"
# )


# def test_run_renv_script():
#     # Ensure the workflow script is executable
#     os.chmod(WORKFLOW_PATH, 0o755)
#     result = subprocess.run(
#         [WORKFLOW_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
#     )
#     output = result.stdout.decode() + result.stderr.decode()
#     # The test should pass only if the error is detected
#     assert result.returncode != 0, f"Expected error exit code, but got 0. Output: {output}"
#     assert "[renv] ERROR:" in output, f"Expected renv error in output, but got: {output}"


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
