# Implementation Plan: Submodule Support

## Context
The reference cache repo pattern (`.cache/{owner}/{repo}`) currently doesn't handle git submodules. When a repo contains submodules:
- They're not cloned during initial cache setup
- They're not updated when the cache is refreshed
- Branch copies inherit incomplete submodule state

## Implementation Steps

### 1. Update Initial Clone
In `setup_cache_repo()` line ~450:
```python
subprocess.run(
    ["git", "clone", "--recurse-submodules", repo_url, str(repo_dir)],
    check=True,
    cwd=str(repo_dir.parent)
)
```

### 2. Update Cache Refresh Logic
Currently uses `fetch --all` which only updates refs, not the working tree. Change to:
```python
# Pull to update working tree
subprocess.run(["git", "-C", str(repo_dir), "pull"], check=True)
# Update submodules recursively
subprocess.run(
    ["git", "-C", str(repo_dir), "submodule", "update", "--recursive", "--init"],
    check=True
)
```

### 3. Considerations
- The cache repo is a full clone (not bare), so `pull` is appropriate
- `--recursive` ensures nested submodules are handled
- `--init` initializes any newly added submodules
- Branch copies inherit submodule state from cache via `shutil.copytree`
- No changes needed to `setup_branch_copy()` since it copies `.git` directory

## Testing
- Test with repo containing submodules
- Verify initial clone includes submodules
- Verify cache updates pull submodule changes
- Verify branch copies have initialized submodules
