#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rockerc.renv import list_branches
import subprocess
from pathlib import Path

# Test the current list_branches function
owner = "blooop"
repo = "manifest_rocker"

print("Testing list_branches function:")
branches = list_branches(owner, repo)
print(f"Found {len(branches)} branches:")
for branch in branches:
    print(f"  '{branch}'")

# Also test the raw git command to see what it outputs
repo_dir = Path.home() / "renv" / owner / repo
print(f"\nRaw git command output from {repo_dir}:")
try:
    result = subprocess.run(
        ["git", "--git-dir", str(repo_dir), "branch", "-a"],
        capture_output=True,
        text=True,
        check=True,
    )
    print("Raw output:")
    for i, line in enumerate(result.stdout.splitlines()):
        print(f"  Line {i}: '{line}'")
except Exception as e:
    print(f"Error: {e}")

# Try alternative git commands
print(f"\nTrying 'git branch -r' (remote branches only):")
try:
    result = subprocess.run(
        ["git", "--git-dir", str(repo_dir), "branch", "-r"],
        capture_output=True,
        text=True,
        check=True,
    )
    print("Remote branches output:")
    for i, line in enumerate(result.stdout.splitlines()):
        print(f"  Line {i}: '{line}'")
except Exception as e:
    print(f"Error: {e}")
