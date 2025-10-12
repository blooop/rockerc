# Plan

1. Update spec to clarify installer-driven autocomplete (done).
2. Adjust implementation so `aid` reverts to simple CLI without autocomplete subcommand; rely on central installer.
3. Extend `rockerc --install` workflow to refresh completion scripts for rockerc, renv, renvvsc, and aid every run.
4. Ensure aid completion script still generated but via installer helper; refactor shared logic if necessary.
5. Update or add tests covering installer behaviour and aid arg parsing (flash flag retained).
6. Run `pixi run ci`, iterate until green.
