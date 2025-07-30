import subprocess
import os

WORKFLOWS_DIR = os.path.dirname(__file__)


def test_workflow_1_pwd():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_1_pwd.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    # Add custom asserts for this workflow as needed
    assert result.returncode in (0, 1), f"Workflow 1 pwd failed: {output}"
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 1 output"


def test_workflow_2_git():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_2_git.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 2 git failed: {output}"
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 2 output"


def test_workflow_3_cmd():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_3_cmd.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 3 cmd failed: {output}"
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 3 output"
    assert (
        "/tmp/test_renv" in output or "test_renv" in output
    ), "Expected working directory 'test_renv' not found in workflow 3 output"


def test_workflow_4_persistent():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_4_persistent.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 4 persistent failed: {output}"
    assert (
        "persistent.txt" in output
    ), "Expected persistent file 'persistent.txt' not found in workflow 4 persistent output"


def test_workflow_5_force_rebuild_cache():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_5_force_rebuild_cache.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 5 force rebuild cache failed: {output}"
    assert (
        "SUCCESS" in output or "WARNING" in output
    ), "Expected result message not found in workflow 5 output"
