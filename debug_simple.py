#!/usr/bin/env python3

import sys
import os
import subprocess
from pathlib import Path


# Simulate the list_branches function to debug
def debug_list_branches(owner: str, repo: str):
    repo_dir = Path.home() / "renv" / owner / repo
    if not repo_dir.exists():
        print(f"Repo dir does not exist: {repo_dir}")
        return []

    print(f"Debugging branches for {owner}/{repo} in {repo_dir}")

    try:
        result = subprocess.run(
            ["git", "--git-dir", str(repo_dir), "branch", "-a"],
            capture_output=True,
            text=True,
            check=True,
        )

        print("Raw git branch -a output:")
        raw_lines = result.stdout.splitlines()
        for i, line in enumerate(raw_lines):
            print(f"  [{i}] '{line}'")

        print("\nProcessing lines:")
        branches = []
        for line_num, line in enumerate(raw_lines):
            original_line = line
            line = line.strip()
            print(f"  Line {line_num}: '{original_line}' -> stripped: '{line}'")

            if not line:
                print(f"    SKIPPED: empty line")
                continue

            if line.startswith("*"):
                print(f"    SKIPPED: starts with *")
                continue

            # Remove 'remotes/origin/' prefix and clean up branch names
            if line.startswith("remotes/origin/"):
                branch = line.replace("remotes/origin/", "")
                if branch != "HEAD":  # Skip HEAD pointer
                    print(f"    ADDED remote branch: '{branch}'")
                    branches.append(branch)
                else:
                    print(f"    SKIPPED: HEAD pointer")
            else:
                print(f"    ADDED local branch: '{line}'")
                branches.append(line)

        print(f"\nFinal branches list: {branches}")
        return sorted(set(branches))

    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
        return []


# Test the function
if __name__ == "__main__":
    branches = debug_list_branches("blooop", "manifest_rocker")
    print(f"\nFinal result: {len(branches)} branches")
    for branch in branches:
        print(f"  - '{branch}'")
