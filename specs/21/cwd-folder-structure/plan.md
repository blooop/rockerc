## Implementation Plan

1. Update `get_worktree_dir()` function:
   - Change from: `_get_repo_workspace_root(repo_spec) / f"{repo_spec.repo}-{safe_branch}"`
   - Change to: `_get_repo_workspace_root(repo_spec) / safe_branch / repo_spec.repo`
   - Returns: `~/renv/{owner}/{repo}/{branch}/{repo}`

2. Update `get_legacy_worktree_dir()` function:
   - Keep current logic for migration purposes
   - This returns the old structure: `~/renv/{owner}/{repo}-{branch}`

3. Update legacy migration logic in `setup_branch_copy()`:
   - Handle both old layouts:
     - Very old: `/renv/{owner}/{repo}-{branch}/`
     - Previous: `/renv/{owner}/{repo}/{repo}-{branch}/`
   - Migrate to new: `/renv/{owner}/{repo}/{branch}/{repo}/`

4. Update `build_rocker_config()`:
   - Keep `_renv_target_dir` pointing to the actual repo directory
   - This is used for cd'ing before calling rockerc

5. Update `manage_container()`:
   - No changes needed - it already uses `_restore_cwd_context()` to cd to `target_dir`
   - The cwd extension will automatically handle mounting

6. Update bash completion:
   - Update path references to match new structure
   - Change from: `$renv_root/$owner/$repo/${repo}-${safe_branch}`
   - Change to: `$renv_root/$owner/$repo/${safe_branch}/$repo`

7. Test thoroughly:
   - Ensure renv works in terminal mode
   - Ensure renvvsc works in VS Code mode
   - Verify legacy migration works
   - Run full CI suite
