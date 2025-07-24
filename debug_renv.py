#!/usr/bin/env python3
"""Debug script for renv."""

import sys

sys.path.insert(0, "/workspaces/rockerc")

from rockerc.renv import repo_exists, get_repo_dir

owner = "blooop"
repo = "bencher"

print(f"Checking repo_exists for {owner}/{repo}")
print(f"Repo directory: {get_repo_dir(owner, repo)}")
print(f"Repo exists: {repo_exists(owner, repo)}")

# Check what files are in the repo directory
repo_dir = get_repo_dir(owner, repo)
if repo_dir.exists():
    print(f"Files in {repo_dir}:")
    for item in repo_dir.iterdir():
        print(f"  {item.name}")
else:
    print(f"Directory {repo_dir} does not exist")
