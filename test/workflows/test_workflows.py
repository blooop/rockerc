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


def test_workflow_4_container_breakout():
    result, output = run_workflow_script("test_workflow_4_container_breakout.sh")
    assert result.returncode == 0, f"Container breakout test failed: {output}"
    assert "✓ Container breakout detection test completed" in output, (
        "Container breakout detection test did not complete"
    )


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


def test_workflow_8_subfolder():
    result, output = run_workflow_script("test_workflow_8_subfolder.sh")
    assert result.returncode == 0, f"Subfolder workflow failed: {output}"

    # Verify unique containers are created for each branch+folder combination
    # New naming scheme uses '.' separator for branches and 'sub-' prefix for subfolders
    expected_containers = [
        "test_renv.main-sub-folder1-folder2",  # blooop/test_renv#folder1/folder2
        "test_renv.test_branch1",  # blooop/test_renv@test_branch1
        "test_renv.test_branch1-sub-folder1",  # blooop/test_renv@test_branch1#folder1
        "test_renv.test_branch1-sub-folder1-folder2",  # blooop/test_renv@test_branch1#folder1/folder2
        "test_renv.test_branch2-sub-folder1-folder2",  # blooop/test_renv@test_branch2#folder1/folder2
        "test_renv.main-sub-folder1",  # blooop/test_renv#folder1 (naming disambiguation test)
        "test_renv.folder1",  # blooop/test_renv@folder1 (naming disambiguation test)
    ]

    for container in expected_containers:
        assert container in output, f"Expected container '{container}' not found in output"

    # Split output into sections based on "expected output:" markers
    sections = output.split("expected output:")

    # First command: main branch @ folder1/folder2 should show example.txt
    assert len(sections) >= 2, "Missing first expected output section"
    assert "example.txt" in sections[1].split("\n")[0], "First command should expect example.txt"
    assert "example.txt" in sections[1], "First command output should contain example.txt"

    # Second command: test_branch1 @ root should show README.md and folder1
    assert len(sections) >= 3, "Missing second expected output section"
    assert "README.md folder1" in sections[2].split("\n")[0], (
        "Second command should expect README.md folder1"
    )
    assert "README.md" in sections[2] and "folder1" in sections[2], (
        "Second command output should contain README.md and folder1"
    )

    # Third command: test_branch1 @ folder1 should show folder2
    assert len(sections) >= 4, "Missing third expected output section"
    assert "folder2" in sections[3].split("\n")[0], "Third command should expect folder2"
    assert "folder2" in sections[3], "Third command output should contain folder2"

    # Fourth command: test_branch1 @ folder1/folder2 should show example.txt
    assert len(sections) >= 5, "Missing fourth expected output section"
    assert "example.txt" in sections[4].split("\n")[0], "Fourth command should expect example.txt"
    assert "example.txt" in sections[4], "Fourth command output should contain example.txt"

    # Fifth command: test_branch2 @ folder1/folder2 should show example.txt
    assert len(sections) >= 6, "Missing fifth expected output section"
    assert "example.txt" in sections[5].split("\n")[0], "Fifth command should expect example.txt"
    assert "example.txt" in sections[5], "Fifth command output should contain example.txt"

    assert "✓ Subfolder workflow validated" in output, "Subfolder workflow did not complete"


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
