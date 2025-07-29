import subprocess
import os

WORKFLOWS_DIR = os.path.dirname(__file__)


def test_workflow_1_clone_and_work():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_1_clone_and_work.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    # Add custom asserts for this workflow as needed
    assert result.returncode in (0, 1), f"Workflow 1 failed: {output}"
    assert "Running: renv osrf/rocker" in output, "Expected message not found in workflow 1 output"
    assert "finished work!" in output, "Expected 'finished work!' not found in workflow 1 output"


# def test_workflow_2_switch_branch():
#     script = os.path.join(WORKFLOWS_DIR, "test_workflow_2_switch_branch.sh")
#     os.chmod(script, 0o755)
#     result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
#     output = result.stdout.decode() + result.stderr.decode()
#     assert result.returncode in (0, 1), f"Workflow 2 failed: {output}"
#     # Check for the persistent message in the output
#     assert "contents of tmp.txt: persistent message" in output, "Expected persistent message not found in workflow 2 output"
