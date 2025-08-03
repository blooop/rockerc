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
    assert (
        "/workspace/test_renv" in output
    ), "Expected working directory '/workspace/test_renv' not found in workflow 1 output"


def test_workflow_2_git():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_2_git.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 2 git failed: {output}"
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 2 output"
    # Fail if workspace is dirty
    dirty_indicators = [
        "Changes not staged for commit",
        "Untracked files",
        "modified:",
        "deleted:",
        "added:",
    ]
    for indicator in dirty_indicators:
        assert (
            indicator not in output
        ), f"Workspace is dirty: found '{indicator}' in git status output: {output}"


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
    """Test cache performance and timing differences between different build modes"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_5_force_rebuild_cache.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in (0, 1), f"Workflow 5 force rebuild cache failed: {output}"

    # Check that date commands executed successfully
    assert "UTC 202" in output, "Expected date output not found in workflow 5 output"

    # Check that all timing sections completed
    assert "=== INITIAL BUILD ===" in output, "Initial build section not found"
    assert "=== FORCE REBUILD TEST ===" in output, "Force rebuild section not found"
    assert "=== CONTAINER REUSE TEST ===" in output, "Container reuse section not found"
    assert "=== NO-CACHE REBUILD TEST ===" in output, "No-cache rebuild section not found"
    assert "=== TIMING SUMMARY ===" in output, "Timing summary not found"

    # Extract timing information
    import re

    initial_match = re.search(r"Initial build:\s+(\d+)s", output)
    force_match = re.search(r"Force rebuild:\s+(\d+)s", output)
    reuse_match = re.search(r"Container reuse:\s+(\d+)s", output)
    nocache_match = re.search(r"No-cache rebuild:\s+(\d+)s", output)

    assert initial_match, "Could not find initial build timing"
    assert force_match, "Could not find force rebuild timing"
    assert nocache_match, "Could not find no-cache rebuild timing"
    assert reuse_match, "Could not find container reuse timing"

    initial_time = int(initial_match.group(1))
    force_time = int(force_match.group(1))
    reuse_time = int(reuse_match.group(1))
    nocache_time = int(nocache_match.group(1))

    # Performance assertions - container reuse should be fastest
    assert (
        reuse_time <= force_time
    ), f"Container reuse ({reuse_time}s) should be faster than force rebuild ({force_time}s)"

    # Force rebuild should be faster than no-cache (due to image caching)
    # Allow some tolerance for timing variations
    if nocache_time > 5:  # Only check if builds take meaningful time
        assert (
            force_time <= nocache_time + 2
        ), f"Force rebuild with cache ({force_time}s) should be close to or faster than no-cache ({nocache_time}s)"

    # Check that force rebuild message appears when container exists
    if "Force rebuild: removing existing container" in output:
        assert (
            "Creating new persistent container" in output
        ), "Should create new container after force removal"

    print(
        f"Cache test performance: initial={initial_time}s, force={force_time}s, nocache={nocache_time}s, reuse={reuse_time}s"
    )


def test_workflow_6_clean_git():
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_6_clean_git.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 6 clean git failed: {output}"


def test_workflow_7_renv_recreation():
    """Test that renv works correctly after deleting .renv folder"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_7_renv_recreation.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 7 renv recreation failed: {output}"

    # Check that all test steps completed successfully
    assert "=== STEP 1: Normal renv operation ===" in output, "Step 1 not found"
    assert "=== STEP 2: Deleting .renv folder ===" in output, "Step 2 not found"
    assert "=== STEP 3: Testing renv recreation ===" in output, "Step 3 not found"
    assert "=== STEP 4: Testing subsequent operations ===" in output, "Step 4 not found"
    assert "=== ALL TESTS PASSED ===" in output, "Final success message not found"

    # Check that no container breakout errors occurred
    assert "container breakout detected" not in output, "Container breakout error detected"
    assert "OCI runtime exec failed" not in output, "OCI runtime exec failure detected"


def test_workflow_8_prune():
    """Test renv prune functionality for both selective and full cleanup"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_8_prune.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 8 prune failed: {output}"

    # Check that all test steps completed successfully
    assert "=== TEST 1: SETUP TEST ENVIRONMENT ===" in output, "Test 1 setup not found"
    assert "=== TEST 2: SELECTIVE PRUNE TEST ===" in output, "Test 2 selective prune not found"
    assert (
        "=== TEST 3: SETUP MULTIPLE ENVIRONMENTS ===" in output
    ), "Test 3 multiple setup not found"
    assert "=== TEST 4: FULL PRUNE TEST ===" in output, "Test 4 full prune not found"
    assert "=== ALL PRUNE TESTS PASSED ===" in output, "Final success message not found"

    # Check that prune operations completed successfully
    assert "✓ Selective prune completed" in output, "Selective prune did not complete"
    assert "✓ Full prune completed" in output, "Full prune did not complete"
    assert (
        "✓ Container correctly removed by selective prune" in output
    ), "Selective prune did not remove container"
    assert (
        "✓ Worktree correctly removed by selective prune" in output
    ), "Selective prune did not remove worktree"
    assert (
        "✓ All containers correctly removed by full prune" in output
    ), "Full prune did not remove all containers"
    assert (
        "✓ .renv directory correctly removed by full prune" in output
    ), "Full prune did not remove .renv directory"
