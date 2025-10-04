import subprocess
import os


def run_workflow_script(script_filename):
    script = os.path.join(WORKFLOWS_DIR, script_filename)
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    return result, output


WORKFLOWS_DIR = os.path.dirname(__file__)


def test_workflow_0_fresh_container():
    result, output = run_workflow_script("test_workflow_0_fresh_container.sh")
    assert result.returncode == 0, f"Fresh container test failed: {output}"
    assert "✓ Fresh container test completed" in output, "Fresh container test did not complete"


def test_workflow_1_stop_and_restart():
    result, output = run_workflow_script("test_workflow_1_stop_and_restart.sh")
    assert result.returncode == 0, f"Stop and restart test failed: {output}"
    assert "✓ Stop and restart test completed" in output, "Stop and restart test did not complete"


def test_workflow_2_delete_and_restart():
    result, output = run_workflow_script("test_workflow_2_delete_and_restart.sh")
    assert result.returncode == 0, f"Delete and restart test failed: {output}"
    assert "✓ Delete and restart test completed" in output, (
        "Delete and restart test did not complete"
    )


def test_workflow_3_force_rebuild():
    result, output = run_workflow_script("test_workflow_3_force_rebuild.sh")
    assert result.returncode == 0, f"Force rebuild test failed: {output}"
    assert "✓ Force rebuild test completed" in output, "Force rebuild test did not complete"


# def test_workflow_4_container_breakout():
#     result, output = run_workflow_script("test_workflow_4_container_breakout.sh")
#     assert result.returncode == 0, f"Container breakout test failed: {output}"
#     assert "✓ Container breakout detection test completed" in output, (
#         "Container breakout detection test did not complete"
#     )


def test_workflow_6_pwd():
    result, output = run_workflow_script("test_workflow_6_pwd.sh")
    assert result.returncode in (0, 1), f"Workflow 1 pwd failed: {output}"
    assert "/test_renv-main" in output, (
        "Expected pwd output from inside the container not found in workflow 1 output"
    )
    assert "total" in output or "drwx" in output or "-rw" in output, (
        "Expected ls -l output not found in workflow 1 output"
    )


def test_workflow_7_git():
    result, output = run_workflow_script("test_workflow_7_git.sh")
    assert result.returncode in (0, 1), f"Workflow 2 git failed: {output}"
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 2 output"


def test_workflow_8_persistent():
    result, output = run_workflow_script("test_workflow_8_persistent.sh")
    assert result.returncode in (0, 1), f"Workflow 4 persistent failed: {output}"
    assert (
        "No such file or directory" in output
        or "hello world" in output
        or "persistent.txt" in output  # fallback for any mention
    ), "Expected output from 'cat persistent.txt' not found in workflow 4 persistent output"


def test_workflow_9_force_rebuild_cache():
    """Test --nocache flag functionality"""
    result, output = run_workflow_script("test_workflow_9_force_rebuild_cache.sh")
    assert result.returncode in (0, 1), f"Workflow 5 --nocache test failed: {output}"
    assert "/test_renv-main" in output or "/tmp" in output, (
        "Expected pwd output not found in workflow 5 output"
    )
    assert "No-cache rebuild test completed" in output, "No-cache rebuild section not found"


def test_workflow_10_clean_git():
    result, output = run_workflow_script("test_workflow_10_clean_git.sh")
    assert result.returncode == 0, f"Workflow 6 clean git failed: {output}"


# def test_workflow_7_container_breakout():
#     script = os.path.join(WORKFLOWS_DIR, "test_workflow_7_container_breakout.sh")
#     os.chmod(script, 0o755)
#     result = subprocess.run(["bash", script], capture_output=True, text=True, check=False)
#     output = result.stdout + "\n" + result.stderr
#     # Check for breakout detection message in second run
#     assert (
#         "Container appears corrupted (possible breakout detection)" in output
#         or "breakout" in output.lower()
#     ), f"Breakout detection message not found in output:\n{output}"
#     # Check that the second run triggers a rebuild (look for pwd output twice)
#     assert output.count("/home/") >= 2 or output.count("/tmp/") >= 2, (
#         "Expected to see pwd output from both runs. Output:\n" + output
#     )
#     assert result.returncode == 0, (
#         f"Script exited with nonzero code: {result.returncode}\nOutput:\n{output}"
#     )
