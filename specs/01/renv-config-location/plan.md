# Plan: Renv Config Location Change

1. **Update `load_renv_rockerc_config()` function in `rockerc/renv.py`**:
   - Change config path from `renv_dir / "rockerc.yaml"` to `~/.rockerc.yaml`
   - Remove creation of renv_dir if it doesn't exist (no longer needed for config)
   - Keep template copying logic but change destination to `~/.rockerc.yaml`

2. **Update `build_rocker_config()` function in `rockerc/renv.py`**:
   - Update docstring to reflect new config location
   - Simplify config loading to use `~/.rockerc.yaml` for both standard and renv configs
   - Remove separate `renv` config loading since it's now the same as `standard`

3. **Test for backward compatibility**:
   - Ensure existing `~/renv/rockerc.yaml` files are still read if they exist
   - Test that new installations create `~/.rockerc.yaml`

4. **Update tests**:
   - Update any tests that reference `~/renv/rockerc.yaml`
   - Add tests for new behavior

5. **Run CI and fix errors**

6. **Commit spec and plan first, then implementation**
