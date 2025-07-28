# import subprocess
# import os
# import sys


# def test_renv_no_errors():
#     import shutil
#     import tempfile

#     tmp_dir = tempfile.mkdtemp(dir="/tmp")
#     renv_dir = os.path.join(tmp_dir, "renv")
#     # Remove renv directory if it exists
#     if os.path.exists(renv_dir):
#         shutil.rmtree(renv_dir)
#     # Run renv command in /tmp
#     result = subprocess.run(
#         [sys.executable, "-m", "rockerc.renv", "osrf/rocker"],
#         cwd=tmp_dir,
#         capture_output=True,
#         text=True,
#         check=True,
#     )
#     print(result.stdout)
#     print(result.stderr)
#     # Check that renv directory exists and contains expected repo
#     repo_dir = os.path.join(renv_dir, "osrf", "rocker")
#     assert os.path.exists(repo_dir), f"Repo dir not found: {repo_dir}"
#     assert os.path.exists(os.path.join(repo_dir, "HEAD")), "Bare repo HEAD not found"
#     # Check that worktree for main exists
#     worktree_dir = os.path.join(repo_dir, "worktree-main")
#     assert os.path.exists(worktree_dir), f"Worktree dir not found: {worktree_dir}"
#     assert os.path.exists(os.path.join(worktree_dir, ".git")), "Worktree .git not found"
