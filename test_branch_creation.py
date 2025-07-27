#!/usr/bin/env python3
"""
Test script to verify the new branch creation functionality.
"""

import sys
from pathlib import Path

# Add the rockerc module to the path
sys.path.insert(0, str(Path(__file__).parent))

from rockerc.renv import setup_repo_environment, setup_logging


def test_new_branch_creation():
    """Test creating a new branch that doesn't exist."""
    setup_logging()

    # Test with a known repository and a non-existent branch
    owner = "blooop"
    repo = "manifest_rocker"
    branch = "test_new_branch_creation"

    print(f"Testing new branch creation for {owner}/{repo}@{branch}")

    try:
        worktree_dir = setup_repo_environment(owner, repo, branch)
        print(f"✓ Successfully created worktree at: {worktree_dir}")

        # Verify the worktree was created
        if worktree_dir.exists():
            print(f"✓ Worktree directory exists: {worktree_dir}")

            # Check if it's a valid git repository
            git_dir = worktree_dir / ".git"
            if git_dir.exists():
                print("✓ Valid git worktree created")
                return True
            else:
                print("✗ No .git directory found in worktree")
                return False
        else:
            print("✗ Worktree directory does not exist")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_new_branch_creation()
    sys.exit(0 if success else 1)
