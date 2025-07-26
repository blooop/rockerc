#!/usr/bin/env python3

import subprocess
from pathlib import Path

def test_new_list_branches(owner: str, repo: str):
    repo_dir = Path.home() / "renv" / owner / repo
    if not repo_dir.exists():
        return []
    try:
        result = subprocess.run([
            "git", "--git-dir", str(repo_dir), "branch", "-a"
        ], capture_output=True, text=True, check=True)
        
        print("Raw output from git branch -a:")
        for i, line in enumerate(result.stdout.splitlines()):
            print(f"  [{i}] {repr(line)}")
        
        branches = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            
            print(f"Processing: {repr(line)}")
            
            # Remove git status prefixes: '*' (current), '+' (worktree)
            if line.startswith('*'):
                line = line[1:].strip()
                print(f"  Removed * prefix: {repr(line)}")
            elif line.startswith('+'):
                line = line[1:].strip()
                print(f"  Removed + prefix: {repr(line)}")
            
            # Skip if line becomes empty after prefix removal
            if not line:
                print("  Skipped: empty after prefix removal")
                continue
            
            # Remove 'remotes/origin/' prefix and clean up branch names
            if line.startswith('remotes/origin/'):
                branch = line.replace('remotes/origin/', '')
                if branch != 'HEAD':  # Skip HEAD pointer
                    print(f"  Added remote branch: {repr(branch)}")
                    branches.append(branch)
                else:
                    print("  Skipped: HEAD pointer")
            else:
                print(f"  Added local branch: {repr(line)}")
                branches.append(line)
        # Remove duplicates and sort
        return sorted(set(branches))
    except Exception as e:
        print(f"Error: {e}")
        return []

# Test the function
if __name__ == "__main__":
    branches = test_new_list_branches("blooop", "manifest_rocker")
    print(f"\nFinal result: {len(branches)} branches")
    for branch in branches:
        print(f"  - {repr(branch)}")
    
    # Check for + prefix
    plus_branches = [b for b in branches if b.startswith('+')]
    if plus_branches:
        print(f"\n❌ Still found {len(plus_branches)} branches with + prefix:")
        for branch in plus_branches:
            print(f"  {repr(branch)}")
    else:
        print("\n✅ No branches with + prefix found!")
