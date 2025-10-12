# Renv Config Location Change

**Spec:**
- Remove automatic creation of `~/renv/rockerc.yaml` configuration file.
- Instead, install the default renv template to `~/.rockerc.yaml` if it doesn't exist.
- Simplify config loading to use only `~/.rockerc.yaml` as the global config.
- Maintain backward compatibility by continuing to read `~/renv/rockerc.yaml` if it exists.
