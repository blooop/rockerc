# Aid autocomplete refresh

- ship shell completion via existing rockerc installer instead of new aid CLI subcommands
- `rockerc --install` updates completion scripts for rockerc/renv/renvvsc/aid on every run
- `aid` command line stays minimal; `aid` no longer exposes `autocomplete` subcommand but can be complemented by installer
- `aid autocomplete --install` behaviour handled through rockerc installer
- `aid -f/--flash` flag adds Gemini flash mode (`--model gemini-2.5-flash`)
