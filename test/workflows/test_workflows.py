import subprocess
import os

WORKFLOWS_DIR = os.path.dirname(__file__)


def test_workflow_0_caching():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_0_caching.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    # Add custom asserts for this workflow as needed
    assert result.returncode in (0, 1), f"Workflow 0 caching failed: {output}"
    assert "First build complete" in output, (
        "Expected 'First build complete' not found in workflow 0 output"
    )
    assert "Second build complete" in output, (
        "Expected 'Second build complete' not found in workflow 0 output"
    )
    assert "Container attachment complete" in output, (
        "Expected 'Container attachment complete' not found in workflow 0 output"
    )
    assert "Timing comparison:" in output, (
        "Expected timing comparison not found in workflow 0 output"
    )


def test_workflow_1_cmd():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_1_cmd.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    # Add custom asserts for this workflow as needed
    assert result.returncode in (0, 1), f"Workflow 1 cmd failed: {output}"
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 1 output"


def test_workflow_2_clone_and_work():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_2_clone_and_work.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 2 failed: {output}"
    assert "On branch renv_test" in output, (
        "Expected 'On branch renv_test' not found in workflow 2 output"
    )
    assert "On branch osrf_renv_test" in output, (
        "Expected 'On branch osrf_renv_test' not found in workflow 2 output"
    )
