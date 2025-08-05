import subprocess
import os

WORKFLOWS_DIR = os.path.dirname(__file__)


def run_workflow_script(script_name, allowed_returncodes=(0, 1)):
    script = os.path.join(WORKFLOWS_DIR, script_name)
    os.chmod(script, 0o755)
    result = subprocess.run([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    output = result.stdout.decode() + result.stderr.decode()
    assert result.returncode in allowed_returncodes, f"{script_name} failed: {output}"
    return output


def test_workflow_1_pwd():
    output = run_workflow_script("test_workflow_1_pwd.sh")
    assert (
        "/workspace/test_wtd" in output
    ), "Expected working directory '/workspace/test_wtd' not found in workflow 1 output"


def test_workflow_2_git():
    output = run_workflow_script("test_workflow_2_git.sh")
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 2 output"
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
    output = run_workflow_script("test_workflow_3_cmd.sh")
    assert "On branch" in output, "Expected git status 'On branch' not found in workflow 3 output"
    assert (
        "/tmp/test_wtd" in output or "test_wtd" in output
    ), "Expected working directory 'test_wtd' not found in workflow 3 output"


def test_workflow_4_persistent():
    output = run_workflow_script("test_workflow_4_persistent.sh")
    assert (
        "persistent.txt" in output
    ), "Expected persistent file 'persistent.txt' not found in workflow 4 persistent output"


def test_workflow_5_force_rebuild_cache():
    """Test cache performance and timing differences between different build modes"""
    output = run_workflow_script("test_workflow_5_force_rebuild_cache.sh")
    # Check that date commands executed successfully
    assert "UTC 202" in output, "Expected date output not found in workflow 5 output"
    # Check that all timing sections completed
    assert "=== INITIAL BUILD ===" in output, "Initial build section not found"
    assert "=== FORCE REBUILD TEST ===" in output, "Force rebuild section not found"
    assert "=== CONTAINER REUSE TEST ===" in output, "Container reuse section not found"
    assert "=== NO-CACHE REBUILD TEST ===" in output, "No-cache rebuild section not found"
    assert "=== TIMING SUMMARY ===" in output, "Timing summary not found"
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
    assert (
        reuse_time <= force_time
    ), f"Container reuse ({reuse_time}s) should be faster than force rebuild ({force_time}s)"
    if nocache_time > 5:
        assert (
            force_time <= nocache_time + 2
        ), f"Force rebuild with cache ({force_time}s) should be close to or faster than no-cache ({nocache_time}s)"
    if "Force rebuild: removing existing container" in output:
        assert (
            "Creating new persistent container" in output
        ), "Should create new container after force removal"
    print(
        f"Cache test performance: initial={initial_time}s, force={force_time}s, nocache={nocache_time}s, reuse={reuse_time}s"
    )


def test_workflow_6_clean_git():
    run_workflow_script("test_workflow_6_clean_git.sh", allowed_returncodes=(0,))


def test_workflow_7_wtd_recreation():
    output = run_workflow_script("test_workflow_7_wtd_recreation.sh", allowed_returncodes=(0,))
    assert "=== STEP 1: Normal wtd operation ===" in output, "Step 1 not found"
    assert "=== STEP 2: Deleting .wtd folder ===" in output, "Step 2 not found"
    assert "=== STEP 3: Testing wtd recreation ===" in output, "Step 3 not found"
    assert "=== STEP 4: Testing subsequent operations ===" in output, "Step 4 not found"
    assert "=== ALL TESTS PASSED ===" in output, "Final success message not found"
    assert "container breakout detected" not in output, "Container breakout error detected"
    assert "OCI runtime exec failed" not in output, "OCI runtime exec failure detected"


def test_workflow_8_prune():
    output = run_workflow_script("test_workflow_8_prune.sh", allowed_returncodes=(0,))
    assert "=== TEST 1: SETUP TEST ENVIRONMENT ===" in output, "Test 1 setup not found"
    assert "=== TEST 2: SELECTIVE PRUNE TEST ===" in output, "Test 2 selective prune not found"
    assert (
        "=== TEST 3: SETUP MULTIPLE ENVIRONMENTS ===" in output
    ), "Test 3 multiple setup not found"
    assert "=== TEST 4: FULL PRUNE TEST ===" in output, "Test 4 full prune not found"
    assert "=== ALL PRUNE TESTS PASSED ===" in output, "Final success message not found"
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
    output = run_workflow_script("test_workflow_9_container_reuse.sh", allowed_returncodes=(0,))
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
    assert (
        "✓ Container was reused (same ID:" in output
    ), "Container was not reused when it should have been"
    assert (
        "✓ Container was correctly recreated after being stopped" in output
    ), "Container was not recreated when stopped"
    assert (
        "✓ Recreated container was reused (same ID:" in output
    ), "Recreated container was not reused"
    lines = output.split("\n")
    container_reuse_found = False
    stale_removal_after_reuse = False
    for i, line in enumerate(lines):
        if "✓ Container was reused (same ID:" in line:
            container_reuse_found = True
            for j in range(max(0, i - 10), min(len(lines), i + 10)):
                if "Removing stale container" in lines[j]:
                    stale_removal_after_reuse = True
                    break
    assert container_reuse_found, "Container reuse confirmation not found"
    assert (
        not stale_removal_after_reuse
    ), "Stale container removal should not happen when reusing existing container"


def test_workflow_10_new_branch():
    output = run_workflow_script("test_workflow_10_new_branch.sh", allowed_returncodes=(0,))
    assert "=== TEST: NEW BRANCH WORKFLOW WITH PRUNE ===" in output, "Test start not found"
    assert (
        "=== NEW BRANCH WORKFLOW WITH PRUNE TEST PASSED ===" in output
    ), "Test completion not found"
    assert "=== STEP 1: INITIAL CLEANUP ===" in output, "Step 1 not found"
    assert "=== STEP 2: CREATE NEW BRANCH ENVIRONMENT ===" in output, "Step 2 not found"
    assert "=== STEP 3: VERIFY NEW BRANCH ENVIRONMENT ===" in output, "Step 3 not found"
    assert "=== STEP 4: VERIFY CONTAINER EXISTS ===" in output, "Step 4 not found"
    assert "=== STEP 5: TEST SELECTIVE PRUNE ===" in output, "Step 5 not found"
    assert "=== STEP 6: RECREATE ENVIRONMENT FOR FULL PRUNE TEST ===" in output, "Step 6 not found"
    assert "=== STEP 7: TEST FULL PRUNE ===" in output, "Step 7 not found"
    assert "=== STEP 8: VERIFY WORKFLOW WORKS AFTER FULL PRUNE ===" in output, "Step 8 not found"
    assert (
        "✓ Successfully created worktree for new branch and ran git status" in output
    ), "Worktree creation not confirmed"
    assert "✓ Confirmed on new branch 'new_branch'" in output, "Branch creation not confirmed"
    assert "✓ Workspace is clean as expected" in output, "Clean workspace not confirmed"
    assert (
        "✓ Container for new branch environment is running" in output
    ), "Container existence not confirmed"
    assert (
        "✓ Container correctly removed by selective prune" in output
    ), "Selective prune container removal not confirmed"
    assert (
        "✓ Worktree correctly removed by selective prune" in output
    ), "Selective prune worktree removal not confirmed"
    assert "✓ Selective prune completed" in output, "Selective prune not completed"
    assert "✓ Full prune completed" in output, "Full prune not completed"
    assert (
        "✓ All wtd containers correctly removed by full prune" in output
    ), "Full prune container removal not confirmed"
    assert (
        "✓ .wtd directory correctly removed by full prune" in output
    ), "Full prune directory removal not confirmed"
    assert (
        "✓ New branch workflow still works after full prune" in output
    ), "Workflow recovery not confirmed"
    assert "On branch new_branch" in output, "Git status doesn't show correct branch"
    assert (
        "nothing to commit, working tree clean" in output
    ), "Git status doesn't show clean workspace"


def test_workflow_11_install_completion():
    output = run_workflow_script("test_workflow_11_install_completion.sh", allowed_returncodes=(0,))
    assert "=== TEST: SHELL COMPLETION INSTALLATION ===" in output, "Test start not found"
    assert (
        "=== SHELL COMPLETION INSTALLATION TEST PASSED ===" in output
    ), "Test completion not found"
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
    assert "✓ Help shows --install option" in output, "Help install option not confirmed"
    assert (
        "✓ Handles unsupported shell gracefully" in output
    ), "Unsupported shell handling not confirmed"


def test_workflow_12_nocache():
    output = run_workflow_script("test_workflow_12_nocache.sh", allowed_returncodes=(0,))
    assert "=== TEST: NOCACHE FEATURE ===" in output, "Test start not found"
    assert "=== NOCACHE FEATURE TEST PASSED ===" in output, "Test completion not found"
    assert "✓ --nocache option appears in help" in output, "Nocache option in help not confirmed"
    assert (
        "✓ --no-cache flag passed to buildx bake command" in output
    ), "Nocache flag usage not confirmed"
    assert (
        "✓ Environment works correctly with --nocache" in output
    ), "Environment functionality not confirmed"
    assert "✓ Git status shows clean workspace" in output, "Clean workspace not confirmed"
    assert "✓ Global --nocache flag works" in output, "Global nocache flag not confirmed"


def test_workflow_13_uv():
    output = run_workflow_script("test_workflow_13_uv.sh", allowed_returncodes=(0,))
    assert "=== TEST: UV EXTENSION" in output, "Test start not found"
    assert "=== UV EXTENSION TEST PASSED ===" in output, "Test completion not found"
    assert "🎉 All tests passed for uv extension!" in output, "Final success message not found"
    assert (
        "✓ uv extension works with other extensions" in output
    ), "UV multi-extension compatibility not confirmed"
    assert (
        "✓ Multi-extension command executed successfully" in output
    ), "Multi-extension command execution not confirmed"


def test_workflow_14_pixi():
    output = run_workflow_script("test_workflow_14_pixi.sh", allowed_returncodes=(0,))
    assert "=== TEST: PIXI EXTENSION" in output, "Test start not found"
    assert "=== PIXI EXTENSION TEST PASSED ===" in output, "Test completion not found"
    assert "🎉 All tests passed for pixi extension!" in output, "Final success message not found"
    assert (
        "✓ pixi extension works with other extensions" in output
    ), "Pixi multi-extension compatibility not confirmed"
    assert (
        "✓ Multi-extension command executed successfully" in output
    ), "Multi-extension command execution not confirmed"
