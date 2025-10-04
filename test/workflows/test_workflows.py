import subprocess
import os

WORKFLOWS_DIR = os.path.dirname(__file__)


def test_workflow_0_basic_lifecycle():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_0_basic_lifecycle.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 0 basic lifecycle failed: {output}"
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 0 output"
    assert "✓ Fresh container test completed" in output, "Fresh container test did not complete"
    assert "✓ Stop and restart test completed" in output, "Stop and restart test did not complete"
    assert "✓ Delete and restart test completed" in output, (
        "Delete and restart test did not complete"
    )
    assert "✓ Force rebuild test completed" in output, "Force rebuild test did not complete"
    assert "✓ Container breakout detection test completed" in output, (
        "Container breakout detection test did not complete"
    )
    assert "✓ Basic lifecycle test completed successfully" in output, (
        "Basic lifecycle test did not complete"
    )


def test_workflow_1_pwd():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_1_pwd.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    # Add custom asserts for this workflow as needed
    assert result.returncode in (0, 1), f"Workflow 1 pwd failed: {output}"
    # Check for pwd output (should be from inside the container)
    assert "/test_renv-main" in output(
        "Expected pwd output from inside the container not found in workflow 1 output"
    )
    # Check for ls -l output (should list files)
    assert "total" in output or "drwx" in output or "-rw" in output, (
        "Expected ls -l output not found in workflow 1 output"
    )


def test_workflow_2_git():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_2_git.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 2 git failed: {output}"
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 2 output"


def test_workflow_4_persistent():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_4_persistent.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 4 persistent failed: {output}"
    assert "persistent.txt" in output, (
        "Expected persistent file 'persistent.txt' not found in workflow 4 persistent output"
    )


def test_workflow_5_force_rebuild_cache():
    """Test --nocache flag functionality"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_5_force_rebuild_cache.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 5 --nocache test failed: {output}"

    # Check that date commands executed successfully
    import re

    assert re.search(r"\b20\d{2}\b", output), "Expected date output not found in workflow 5 output"
    assert "=== NO-CACHE REBUILD TEST ===" in output, "No-cache rebuild section not found"


def test_workflow_6_clean_git():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_6_clean_git.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
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
