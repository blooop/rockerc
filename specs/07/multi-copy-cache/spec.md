# Multi-Copy Repo with Cache

**Status**: ✅ Implemented and Tested

## Problem
Worktree-based renv implementation (spec 06) has compatibility issues with renvvsc and adds complexity with:
- Worktree-specific git metadata structure
- Complex relative path handling for host/container compatibility
- Non-standard `.git` file pointing to worktree metadata

## Goal
Simplify renv by using multiple full repo copies instead of worktrees, while avoiding repeated full clones.

## Solution
Use a cached repo copy that gets fetched before each branch checkout:

**Directory structure:**
```
~/renv/blooop/
├── test_renv-cache/      # cache copy (always fetched)
├── test_renv-main/       # branch copy (normal .git)
└── test_renv-feature/    # branch copy (normal .git)
```

**Workflow:**
1. First time: Clone full repo as `{repo}-cache`
2. Every time: Fetch updates in cache copy
3. Create/update branch copy by:
   - Copy entire cache directory to `{repo}-{branch}`
   - Checkout the requested branch
   - Pull latest changes

**Benefits:**
- Standard git directories work with all tools (VSCode, renvvsc, host git)
- No worktree complexity
- No path translation needed
- Fast: avoids full clones by copying from cache

**Trade-offs:**
- Uses more disk space (full copy per branch vs worktree's lightweight refs)
- Copy operation takes time (mitigated by being local)

## Implementation
1. Replace `setup_bare_repo()` with `setup_cache_repo()` - maintains a full repo as cache
2. Replace `setup_worktree()` with `setup_branch_copy()` - copies cache and checks out branch
3. Update `get_repo_dir()` to return cache directory path
4. Update `get_worktree_dir()` to return branch copy path
5. Remove all worktree-specific logic (relative path conversion, etc.)
6. Simplify volume mounts - only mount the branch copy directory

## Testing
All tests pass:
- **Python tests**: 33/33 renv tests passing
- **Bash integration tests**: All 9 test scenarios passing (`test_multi_copy.sh`)
  - Cache has standard git directory (not bare)
  - Branch copies are full, independent git repos
  - All git operations work correctly
  - Multiple branches can coexist
  - Directory structure matches spec
