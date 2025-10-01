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

## Recommendation
Explore both approaches:
1. **Test if removing `.git` file modifications works** (let git worktree handle it)
2. **Consider switching to regular clones** for better compatibility

Let's start with #1 as it requires minimal changes.

## Implementation Steps

### Phase 1: Remove `.git` File Modifications
1. Comment out lines 422-428 in `build_rocker_config()` (don't write container path)
2. Remove `_setup_git_in_container()` calls
3. Remove git fixup logic in `_try_attach_with_fallback()`
4. Test with:
   - `renv` command (git should work in container)
   - VSCode opening the worktree folder (should detect git)
   - rockerc from the worktree folder (should detect git branch)

### Phase 2: Verify Volume Mounts
1. Ensure bare repo and worktree git metadata are accessible in container
2. Current mounts in `build_rocker_config()`:
   - Bare repo: `{repo_dir}:{docker_bare_repo_mount}`
   - Worktree: `{worktree_dir}:{docker_worktree_mount}`
   - Git metadata: `{worktree_git_dir}:{docker_worktree_git_mount}`
3. Verify the worktree git metadata mount is correct

### Phase 3: Test Scenarios
1. Start renv on a repo/branch
2. Open worktree folder in VSCode on host → should see git status
3. Run rockerc in worktree folder → should detect branch
4. Inside container, run `git status` → should work
5. Test with renvvsc → VSCode should attach with git working

### Phase 4 (If Phase 1 fails): Regular Clones
1. Change `setup_worktree()` to `setup_clone()`
2. Use `git clone -b {branch}` instead of `git worktree add`
3. Adjust folder structure: `~/renv/{owner}/{repo}/{branch}/`
4. Simplify volume mounts (no separate git metadata mount needed)
5. Update tests

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
