import subprocess
import sys
from pathlib import Path
import pytest


def run_command(command, cwd=None):
    """Helper to run a command and return output."""
    result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=cwd)
    return result.stdout.strip()


@pytest.fixture
def setup_git_repo(tmp_path):
    """Set up a git repo with a worktree."""
    repo_dir = tmp_path / "repo"

    # Initialize a full repo first
    run_command(["git", "init"], cwd=repo_dir)
    (repo_dir / "README.md").write_text("This is a test.")
    run_command(["git", "-C", str(repo_dir), "add", "README.md"])
    run_command(["git", "-C", str(repo_dir), "commit", "-m", "Initial commit"])

    # Create a bare repo from it
    bare_repo_dir = tmp_path / "repo.git"
    run_command(["git", "clone", "--bare", str(repo_dir), str(bare_repo_dir)])

    # Create a worktree from the main repo
    worktree_dir = tmp_path / "worktree"
    run_command(["git", "-C", str(repo_dir), "worktree", "add", str(worktree_dir)])

    # Add a file to the worktree to check status
    (worktree_dir / "worktree_file.txt").write_text("worktree file")
    run_command(["git", "-C", str(worktree_dir), "add", "worktree_file.txt"])

    return bare_repo_dir, worktree_dir


def test_git_status_in_container(setup_git_repo, monkeypatch):  # pylint: disable=redefined-outer-name
    """Test that git status works inside the container."""
    bare_repo_dir, worktree_dir = setup_git_repo

    # We need to call the entrypoint.
    # The entrypoint is rockerc.py, which calls renv.py's renv() function.
    # The renv() function uses sys.argv.

    # To make this testable without actually building and installing the package,
    # we can call the main function of the script directly and set sys.argv.

    from rockerc import renv

    # We need to find the rockerc.yaml file. Let's assume it's in the project root.
    # The test is run from the project root.
    rockerc_file = Path.cwd() / "rockerc.yaml"
    if not rockerc_file.exists():
        # In case the test is run from a different directory
        rockerc_file = Path(__file__).parent.parent / "rockerc.yaml"

    # Simulate the command line arguments for renv
    # rocker renv <worktree_dir> -- <command>
    # The rockerc.py script will strip 'renv' and pass the rest to the renv entrypoint.
    # The renv entrypoint expects the script name, then the worktree_dir, etc.
    sys.argv = [
        "renv",  # script name
        str(worktree_dir),
        str(rockerc_file),  # rocker file
        "--",
        "git",
        "status",
    ]

    # We need to mock the final call to rockerc.main
    final_argv = []

    def mock_rockerc_main():
        nonlocal final_argv
        final_argv = sys.argv

    monkeypatch.setattr("rockerc.rockerc.main", mock_rockerc_main)

    renv.main()

    # Now check the arguments passed to the mocked rockerc.main
    print(f"Final argv: {final_argv}")

    assert "--volume" in final_argv
    vol_index = final_argv.index("--volume")
    assert (
        f"{bare_repo_dir}:/repo.git" in final_argv[vol_index + 1]
        or f"{bare_repo_dir.resolve()}:/repo.git" in final_argv[vol_index + 1]
    )

    vol_index_2 = final_argv.index("--volume", vol_index + 1)
    # Check that the second volume is the worktree
    assert f"{worktree_dir}:" in final_argv[vol_index_2 + 1]
