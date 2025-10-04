# Configurable RENV home

- Add a helper that returns the renv home, reading `RENV_DIR` when set and defaulting to `~/renv`.
- Update runtime code to use the helper instead of hardcoding paths.
- Ensure tests isolate state by setting `RENV_DIR` to `/tmp/renv`.
