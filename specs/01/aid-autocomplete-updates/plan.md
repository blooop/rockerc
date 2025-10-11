# Plan

1. Inspect existing `aid` CLI (entry point, args) and autocomplete support to understand current state and extension points.
2. Design and implement shell completion generation/installation for `aid`, likely leveraging Typer/Rich integration or custom script; ensure pixi task hooks if needed.
3. Update `aid autocomplete --install` logic to reinstall/overwrite scripts to guarantee latest version even if files exist.
4. Add `-f`/`--flash` flag mapping to `--model gemini-2.5-flash` or equivalent internal configuration; adjust parsing and downstream usage.
5. Update tests or add new ones covering new flag behaviour and autocomplete reinstall logic.
6. Run `pixi run ci`, fix issues, and document any relevant notes.
