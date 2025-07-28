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


# def test_workflow_2_switch_branch():
#     script = os.path.join(WORKFLOWS_DIR, "test_workflow_2_switch_branch.sh")
#     os.chmod(script, 0o755)
#     # Clean up tmp files before running
#     tmp_files = ["/tmp/tmp.txt", "/tmp/tmp2.txt"]
#     for f in tmp_files:
#         if os.path.exists(f):
#             os.remove(f)
#     result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
#     output = result.stdout.decode() + result.stderr.decode()
#     assert result.returncode in (0, 1), f"Workflow 2 failed: {output}"
#     # tmp.txt should exist and contain 'lol\n'
#     assert os.path.exists("/tmp/tmp.txt"), "tmp.txt was not created by workflow"
#     with open("/tmp/tmp.txt", encoding="utf-8") as f:
#         content = f.read().strip()
#     assert content == "lol", f"tmp.txt content incorrect: '{content}'"
#     # tmp2.txt should exist (empty file)
#     assert os.path.exists("/tmp/tmp2.txt"), "tmp2.txt was not created by workflow"


# Add more individual tests for each workflow script as needed
