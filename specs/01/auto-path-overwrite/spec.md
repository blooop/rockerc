# Auto Path Overwrite for renv and aid

If `auto` is present in `~/.rockerc.yaml` or any collected arguments for `renv` or `aid`, it should be overwritten with:

`auto=/renv/repo_owner/repo_name/branch_name/repo_name`

This ensures that `auto` loads from the correct repo directory, not from wherever `aid` or `renv` are run from.