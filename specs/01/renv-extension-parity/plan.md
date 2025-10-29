# Plan: renv Extension Argument Parity

1. **Audit current parsers**
   - Map extension-related options in `rockerc` (cli flags, defaults, validation).
   - Document how `renv` currently handles extension selection and where it diverges.

2. **Design shared argument definitions**
   - Extract extension-related parser setup into reusable helpers to avoid duplication.
   - Decide how wrappers (`rockervsc`, `renvvsc`) inject defaults while reusing shared logic.

3. **Add regression tests first**
   - Extend CLI parsing tests to cover extension-flag parity between `rockerc`/`renv` and wrappers.
   - Ensure new tests fail under current behavior to confirm coverage.

4. **Implement parser alignment**
   - Refactor parsers to use shared argument helpers and update `renv` to accept the full flag set.
   - Maintain existing code paths for extension resolution and defaults.

5. **Validate**
   - Run `pixi run ci`, resolve any issues, and confirm tests pass.
   - Review for unintended side effects in CLI help or defaults.
