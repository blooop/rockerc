# Plan: Auto Path Overwrite for renv and aid

1. Identify where `auto` is read from `~/.rockerc.yaml` or arguments in `renv` and `aid`.
2. Implement logic to overwrite `auto` with `/renv/repo_owner/repo_name/branch_name/repo_name`.
3. Ensure correct repo_owner, repo_name, and branch_name are detected from the current repo context.
4. Update both `renv` and `aid` to use the new path when `auto` is detected.
5. Add/modify tests to verify correct path resolution and overwriting.
6. Run CI to validate changes.
7. Commit only if CI passes.