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
    assert "On branch renv_test" in output, (
        "Expected 'On branch renv_test' not found in workflow 1 output"
    )
    assert "On branch osrf_renv_test" in output, (
        "Expected 'On branch osrf_renv_test' not found in workflow 1 output"
    )


def test_workflow_2_echo():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_2_echo.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 2 echo failed: {output}"
    assert "I am in folder: echo_test" in output, (
        "Expected echo message not found in workflow 2 echo output"
    )
