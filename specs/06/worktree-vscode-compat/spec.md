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

Root cause: Current folder structure places worktrees as children of bare repo, and container mounts rename directories:
```
Host: ~/renv/blooop/test_renv/worktree-main/
Container: /workspace/test_renv.git (bare) + /workspace/test_renv (worktree)
```

## Goal
Enable renv-managed worktrees to work seamlessly with both host and container tools using relative paths.

## Solution
Restructure folders so worktrees are **siblings** of bare repo, maintaining identical relative structure in both host and container.

**New structure:**
```
~/renv/blooop/
├── test_renv/              # bare repo (no .git suffix)
│   └── worktrees/
└── test_renv-main/         # worktree (sibling, not child)
    └── .git → ../test_renv/worktrees/test_renv-main
```

**Container mounts:**
```
/workspace/test_renv/       # bare repo
/workspace/test_renv-main/  # worktree
```

Relative path `../test_renv/worktrees/test_renv-main` resolves correctly in both locations.

## Implementation
1. Change `get_worktree_dir()` to return sibling directory: `{owner}/{repo}-{branch}`
2. Update `setup_worktree()` to create worktree as sibling
3. Convert absolute path to relative in `.git` file after creation
4. Update volume mounts in `build_rocker_config()` (no separate git metadata mount needed)
5. Remove all code that rewrites `.git` files with container paths
6. Update container naming and workspace paths
7. Make sure rocker launches from the worktree mount so the `cwd` extension resolves to `/workspace/{repo}-{branch}`
