# Implementation Plan: Worktree VSCode Compatibility

## Problem Analysis

### Current State
- Worktree `.git` files use absolute container paths
- Written in `build_rocker_config()` at line 422-428
- Also rewritten in `_setup_git_in_container()` and `_try_attach_with_fallback()`
- Breaks VSCode, rockerc, and git on the host

### Root Cause
The code explicitly writes container paths to work around git worktree path issues, but this breaks host compatibility.

## Solution Design

### Approach: Relative Paths
Git natively supports relative paths in `.git` files. Structure:
```
~/renv/blooop/test_renv/           # bare repo
├── worktrees/
│   └── worktree-main/             # git metadata
└── worktree-main/                 # actual worktree
    └── .git -> ../../worktrees/worktree-main
```

Container mounts:
- `~/renv/blooop/test_renv` → `/workspace/test_renv.git`
- `~/renv/blooop/test_renv/worktree-main` → `/workspace/test_renv`

With relative path `gitdir: ../../worktrees/worktree-main`:
- Host: `~/renv/blooop/test_renv/worktree-main/../../worktrees/worktree-main` ✓
- Container: `/workspace/test_renv/../../worktrees/worktree-main` ✓

Wait, there's an issue. In container:
- Bare repo: `/workspace/test_renv.git`
- Worktree: `/workspace/test_renv`

So `/workspace/test_renv/../../worktrees/worktree-main` = `/worktrees/worktree-main` ✗

We need to adjust the relative path based on the mount structure.

### Corrected Approach
The `.git` file in the worktree should point to the metadata relative to the worktree location.

Actually, git worktree creates the `.git` file automatically with the correct path when using `git worktree add`. The problem is that we're **overwriting** it.

**Better solution**: Don't modify the `.git` file at all. Let git worktree create it correctly, and ensure our volume mounts preserve the structure.

### Alternative: Regular Clones
Instead of worktrees, use regular clones:
```
~/renv/blooop/test_renv/main/      # clone of main branch
~/renv/blooop/test_renv/feature/   # clone of feature branch
```

Pros:
- No `.git` file path issues
- Works with all tools out of the box
- Simpler to understand

Cons:
- More disk space (duplicates .git for each branch)
- Slower to create new branches

Given the goal of "checkout the repo in some appropriate way" and making it work with VSCode/rockerc, regular clones might be more appropriate.

## Validated Solution
Restructure folders so worktrees are siblings of bare repo, maintaining same relative paths in both host and container.

**Proof:** Tested with git - relative paths in `.git` files work correctly when directory structure is preserved.

## Implementation Steps

### 1. Update Directory Functions
- `get_repo_dir()`: Keep as `~/renv/{owner}/{repo}` (bare repo, no `.git` suffix)
- `get_worktree_dir()`: Change to return `~/renv/{owner}/{repo}-{safe_branch}` (sibling, not child)
- `get_container_name()`: Keep as `{repo}-{safe_branch}`

### 2. Update `setup_worktree()`
```python
def setup_worktree(repo_spec: RepoSpec) -> pathlib.Path:
    repo_dir = get_repo_dir(repo_spec)
    worktree_dir = get_worktree_dir(repo_spec)  # Now returns sibling path

    setup_bare_repo(repo_spec)

    if not worktree_dir.exists():
        # Create worktree as sibling (use relative path from parent dir)
        worktree_name = worktree_dir.name
        subprocess.run(
            ["git", "-C", str(repo_dir), "worktree", "add",
             f"../{worktree_name}", repo_spec.branch],
            check=True
        )

        # Convert absolute path to relative in .git file
        git_file = worktree_dir / ".git"
        relative_gitdir = f"../{repo_dir.name}/worktrees/{worktree_name}"
        git_file.write_text(f"gitdir: {relative_gitdir}\n")

    return worktree_dir
```

### 3. Update `build_rocker_config()` Volume Mounts
```python
# Old (3 mounts with renaming):
volumes = [
    f"{repo_dir}:{docker_bare_repo_mount}",  # → /workspace/test_renv.git
    f"{worktree_dir}:{docker_worktree_mount}",  # → /workspace/test_renv
    f"{worktree_git_dir}:{docker_worktree_git_mount}",  # metadata
]

# New (2 mounts preserving structure):
volumes = [
    f"{repo_dir}:/workspace/{repo_spec.repo}",  # bare repo
    f"{worktree_dir}:/workspace/{repo_spec.repo}-{safe_branch}",  # worktree
]
```

### 4. Remove `.git` File Rewriting
- Remove lines 422-428 in `build_rocker_config()` (git config file writing)
- Remove `_setup_git_in_container()` function
- Remove git fixup in `_try_attach_with_fallback()`

### 5. Update Container Working Directory
The cwd extension should target `/workspace/{repo}-{branch}` instead of `/workspace/{repo}`

### 6. Test Scenarios
1. Fresh setup: `renv blooop/test_renv@main`
2. Verify on host: `cd ~/renv/blooop/test_renv-main && git status`
3. Verify in container: enter and run `git status`
4. VSCode on host: open worktree folder, should detect git
5. rockerc from worktree: should detect branch
6. renvvsc: VSCode should attach with working git

## Files to Modify
- `rockerc/renv.py`:
  - `setup_worktree()` - either fix or replace with `setup_clone()`
  - `build_rocker_config()` - remove `.git` file writing
  - `_setup_git_in_container()` - remove or fix
  - `_try_attach_with_fallback()` - remove git fixup logic

## Testing
- Run existing renv tests
- Add test for git detection on host
- Manual test with VSCode
- Manual test with rockerc from worktree folder
