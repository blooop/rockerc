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
        "/workspace/test_wtd" in output
    ), "Expected working directory '/workspace/test_wtd' not found in workflow 1 output"


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
        "/tmp/test_wtd" in output or "test_wtd" in output
    ), "Expected working directory 'test_wtd' not found in workflow 3 output"


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


def test_workflow_7_wtd_recreation():
    """Test that wtd works correctly after deleting .wtd folder"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_7_wtd_recreation.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 7 wtd recreation failed: {output}"

    # Check that all test steps completed successfully
    assert "=== STEP 1: Normal wtd operation ===" in output, "Step 1 not found"
    assert "=== STEP 2: Deleting .wtd folder ===" in output, "Step 2 not found"
    assert "=== STEP 3: Testing wtd recreation ===" in output, "Step 3 not found"
    assert "=== STEP 4: Testing subsequent operations ===" in output, "Step 4 not found"
    assert "=== ALL TESTS PASSED ===" in output, "Final success message not found"

    # Check that no container breakout errors occurred
    assert "container breakout detected" not in output, "Container breakout error detected"
    assert "OCI runtime exec failed" not in output, "OCI runtime exec failure detected"


def test_workflow_8_prune():
    """Test wtd prune functionality for both selective and full cleanup"""
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
        "✓ All wtd containers correctly removed by full prune" in output
    ), "Full prune did not remove all wtd containers"
    assert (
        "✓ .wtd directory correctly removed by full prune" in output
    ), "Full prune did not remove .wtd directory"


def test_workflow_9_container_reuse():
    """Test wtd container reuse functionality"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_9_container_reuse.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 9 container reuse failed: {output}"

    # Check that all test steps completed successfully
    assert (
        "=== TEST 1: CREATE INITIAL ENVIRONMENT ===" in output
    ), "Test 1 create environment not found"
    assert "=== TEST 2: TEST CONTAINER REUSE ===" in output, "Test 2 container reuse not found"
    assert (
        "=== TEST 3: TEST CONTAINER RECREATION AFTER STOP ===" in output
    ), "Test 3 recreation after stop not found"
    assert (
        "=== TEST 4: TEST REUSE OF RECREATED CONTAINER ===" in output
    ), "Test 4 reuse of recreated not found"
    assert "=== ALL CONTAINER REUSE TESTS PASSED ===" in output, "Final success message not found"

    # Check that container reuse behavior is correct
    assert (
        "✓ Container was reused (same ID:" in output
    ), "Container was not reused when it should have been"
    assert (
        "✓ Container was correctly recreated after being stopped" in output
    ), "Container was not recreated when stopped"
    assert (
        "✓ Recreated container was reused (same ID:" in output
    ), "Recreated container was not reused"

    # Check that we don't see stale container removal message when reusing
    lines = output.split("\n")
    container_reuse_found = False
    stale_removal_after_reuse = False

    for i, line in enumerate(lines):
        if "✓ Container was reused (same ID:" in line:
            container_reuse_found = True
            # Check if there's a stale container message in the nearby lines (shouldn't be)
            for j in range(max(0, i - 10), min(len(lines), i + 10)):
                if "Removing stale container" in lines[j]:
                    stale_removal_after_reuse = True
                    break

    assert container_reuse_found, "Container reuse confirmation not found"
    assert (
        not stale_removal_after_reuse
    ), "Stale container removal should not happen when reusing existing container"


def test_workflow_10_new_branch():
    """Test wtd workflow for creating new branches that don't exist yet with prune functionality"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_10_new_branch.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 10 new branch failed: {output}"

    # Check that the test completed successfully
    assert "=== TEST: NEW BRANCH WORKFLOW WITH PRUNE ===" in output, "Test start not found"
    assert (
        "=== NEW BRANCH WORKFLOW WITH PRUNE TEST PASSED ===" in output
    ), "Test completion not found"

    # Check that all steps completed successfully
    assert "=== STEP 1: INITIAL CLEANUP ===" in output, "Step 1 not found"
    assert "=== STEP 2: CREATE NEW BRANCH ENVIRONMENT ===" in output, "Step 2 not found"
    assert "=== STEP 3: VERIFY NEW BRANCH ENVIRONMENT ===" in output, "Step 3 not found"
    assert "=== STEP 4: VERIFY CONTAINER EXISTS ===" in output, "Step 4 not found"
    assert "=== STEP 5: TEST SELECTIVE PRUNE ===" in output, "Step 5 not found"
    assert "=== STEP 6: RECREATE ENVIRONMENT FOR FULL PRUNE TEST ===" in output, "Step 6 not found"
    assert "=== STEP 7: TEST FULL PRUNE ===" in output, "Step 7 not found"
    assert "=== STEP 8: VERIFY WORKFLOW WORKS AFTER FULL PRUNE ===" in output, "Step 8 not found"

    # Check that the new branch was created correctly
    assert (
        "✓ Successfully created worktree for new branch and ran git status" in output
    ), "Worktree creation not confirmed"
    assert "✓ Confirmed on new branch 'new_branch'" in output, "Branch creation not confirmed"
    assert "✓ Workspace is clean as expected" in output, "Clean workspace not confirmed"

    # Check that container management works correctly
    assert (
        "✓ Container for new branch environment is running" in output
    ), "Container existence not confirmed"
    assert (
        "✓ Container correctly removed by selective prune" in output
    ), "Selective prune container removal not confirmed"
    assert (
        "✓ Worktree correctly removed by selective prune" in output
    ), "Selective prune worktree removal not confirmed"

    # Check that prune operations work correctly
    assert "✓ Selective prune completed" in output, "Selective prune not completed"
    assert "✓ Full prune completed" in output, "Full prune not completed"
    assert (
        "✓ All wtd containers correctly removed by full prune" in output
    ), "Full prune container removal not confirmed"
    assert (
        "✓ .wtd directory correctly removed by full prune" in output
    ), "Full prune directory removal not confirmed"

    # Check that workflow still works after full prune
    assert (
        "✓ New branch workflow still works after full prune" in output
    ), "Workflow recovery not confirmed"

    # Check that git status shows expected output
    assert "On branch new_branch" in output, "Git status doesn't show correct branch"
    assert (
        "nothing to commit, working tree clean" in output
    ), "Git status doesn't show clean workspace"


def test_workflow_11_install_completion():
    """Test wtd --install shell completion feature"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_11_install_completion.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 11 install completion failed: {output}"

    # Check that the test completed successfully
    assert "=== TEST: SHELL COMPLETION INSTALLATION ===" in output, "Test start not found"
    assert (
        "=== SHELL COMPLETION INSTALLATION TEST PASSED ===" in output
    ), "Test completion not found"

    # Check that bash completion was created and validated
    assert (
        "✓ Bash completion file created successfully" in output
    ), "Bash completion creation not confirmed"
    assert (
        "✓ Bash completion contains expected function" in output
    ), "Bash completion function not confirmed"
    assert (
        "✓ Bash completion contains correct commands (no destroy)" in output
    ), "Bash completion commands not confirmed"
    assert (
        "✓ Bash completion script syntax is valid" in output
    ), "Bash completion syntax not confirmed"

    # Check that help shows install option
    assert "✓ Help shows --install option" in output, "Help install option not confirmed"

    # Check that unsupported shell is handled gracefully
    assert (
        "✓ Handles unsupported shell gracefully" in output
    ), "Unsupported shell handling not confirmed"


def test_workflow_12_nocache():
    """Test wtd --nocache feature for disabling build cache"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_12_nocache.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 12 nocache failed: {output}"

    # Check that the test completed successfully
    assert "=== TEST: NOCACHE FEATURE ===" in output, "Test start not found"
    assert "=== NOCACHE FEATURE TEST PASSED ===" in output, "Test completion not found"

    # Check that nocache appears in help
    assert "✓ --nocache option appears in help" in output, "Nocache option in help not confirmed"

    # Check that --no-cache flag is passed to buildx
    assert (
        "✓ --no-cache flag passed to buildx bake command" in output
    ), "Nocache flag usage not confirmed"

    # Check that environment still works with nocache
    assert (
        "✓ Environment works correctly with --nocache" in output
    ), "Environment functionality not confirmed"
    assert "✓ Git status shows clean workspace" in output, "Clean workspace not confirmed"

    # Check backward compatibility
    assert "✓ Global --nocache flag works" in output, "Global nocache flag not confirmed"


def test_workflow_13_uv():
    """Test wtd uv extension for Python package management"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_13_uv.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 13 uv extension failed: {output}"

    # Check that the test completed successfully
    assert "=== TEST: UV EXTENSION ===" in output, "Test start not found"
    assert "=== UV EXTENSION TEST PASSED ===" in output, "Test completion not found"

    # Check that uv extension appears in extension list
    assert (
        "✓ uv extension appears in extension list" in output
    ), "UV extension in list not confirmed"

    # Check that uv extension loads correctly
    assert "✓ uv extension loaded successfully" in output, "UV extension loading not confirmed"

    # Check that command executes with uv extension
    assert (
        "✓ Command executed successfully with uv extension" in output
    ), "UV command execution not confirmed"

    # Check that uv is available in container
    assert (
        "✓ uv is available in container and shows version" in output
    ), "UV availability not confirmed"

    # Check that uv help works
    assert "✓ uv help command works correctly" in output, "UV help functionality not confirmed"

    # Check that uv works with other extensions
    assert (
        "✓ uv extension works with other extensions" in output
    ), "UV multi-extension compatibility not confirmed"
    assert (
        "✓ Multi-extension command executed successfully" in output
    ), "Multi-extension command execution not confirmed"


def test_workflow_14_pixi():
    """Test wtd pixi extension for package management"""
    script = os.path.join(WORKFLOWS_DIR, "test_workflow_14_pixi.sh")
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode == 0, f"Workflow 14 pixi extension failed: {output}"

    # Check that the test completed successfully
    assert "=== TEST: PIXI EXTENSION ===" in output, "Test start not found"
    assert "=== PIXI EXTENSION TEST PASSED ===" in output, "Test completion not found"

    # Check that pixi extension appears in extension list
    assert (
        "✓ pixi extension appears in extension list" in output
    ), "Pixi extension in list not confirmed"

    # Check that pixi extension loads correctly
    assert "✓ pixi extension loaded successfully" in output, "Pixi extension loading not confirmed"

    # Check that command executes with pixi extension
    assert (
        "✓ Command executed successfully with pixi extension" in output
    ), "Pixi command execution not confirmed"

    # Check that pixi is available in container
    assert (
        "✓ pixi is available in container and shows version" in output
    ), "Pixi availability not confirmed"

    # Check that pixi help works
    assert "✓ pixi help command works correctly" in output, "Pixi help functionality not confirmed"

    # Check that pixi works with other extensions
    assert (
        "✓ pixi extension works with other extensions" in output
    ), "Pixi multi-extension compatibility not confirmed"
    assert (
        "✓ Multi-extension command executed successfully" in output
    ), "Multi-extension command execution not confirmed"
