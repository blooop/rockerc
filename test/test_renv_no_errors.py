import subprocess
import os
import sys
from pathlib import Path
import shutil


def test_renv_no_errors():
    home = str(Path.home())
    renv_dir = os.path.join(home, "renv")
    # Remove renv directory if it exists
    if os.path.exists(renv_dir):
        shutil.rmtree(renv_dir)
    # Run renv command
    result = subprocess.run(
        [sys.executable, "-m", "rockerc.renv", "osrf/rocker"],
        capture_output=True,
        text=True,
        check=True,
    )
    print(result.stdout)
    print(result.stderr)
    # Check that renv directory exists and contains expected repo
    repo_dir = os.path.join(renv_dir, "osrf", "rocker")
    assert os.path.exists(repo_dir), f"Repo dir not found: {repo_dir}"
    assert os.path.exists(os.path.join(repo_dir, "HEAD")), "Bare repo HEAD not found"
    # Check that worktree for main exists
    worktree_dir = os.path.join(repo_dir, "worktree-main")
    assert os.path.exists(worktree_dir), f"Worktree dir not found: {worktree_dir}"
    assert os.path.exists(os.path.join(worktree_dir, ".git")), "Worktree .git not found"
