# Worktree VSCode and Host Git Compatibility

## Problem
Git worktrees created by renv have `.git` files pointing to container paths (`/workspace/...`), making them incompatible with:
- VSCode on the host (can't detect git repository)
- rockerc on the host (can't detect git branch/status)
- Git commands on the host (invalid gitdir path)

Current `.git` file content:
```
gitdir: /workspace/test_renv.git/worktrees/worktree-main
```

This path only exists inside the container, not on the host where VSCode and rockerc run before container launch.

## Goal
Enable renv-managed worktrees to work seamlessly with both:
1. Host tools (VSCode, rockerc, git commands before container launch)
2. Container tools (git commands inside container)

## Solution
Use **relative paths** in worktree `.git` files instead of absolute container paths.

Git worktrees support relative paths. The `.git` file should contain:
```
gitdir: ../../worktrees/worktree-main
```

This works because:
- On host: `~/renv/blooop/test_renv/worktree-main/../../worktrees/worktree-main` resolves correctly
- In container: `/workspace/test_renv/../../worktrees/worktree-main` resolves correctly (when bare repo is mounted at `/workspace/test_renv.git`)

## Implementation
1. Update `setup_worktree()` in renv.py to use relative gitdir paths
2. Remove code that rewrites `.git` file with container paths
3. Ensure volume mounts align with relative path assumptions
4. Test with both VSCode and rockerc on host, and git commands in container
