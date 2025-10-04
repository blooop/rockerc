# Parse CLI extensions and image arguments

## Problem
Running `rockerc --claude ubuntu:22.04` produces a broken rocker command:
```
rocker ... --cwd --claude ubuntu:22.04 --detach ... -- ubuntu:24.04
```

Issues:
1. Image appears twice (`ubuntu:22.04` from CLI, `ubuntu:24.04` from config)
2. CLI args are passed through unparsed, causing rocker to misinterpret them
3. No way to override config image via CLI

## Solution
Parse CLI arguments to separate:
- Extension flags: `--extension-name`
- Image: first non-flag argument
- Command: remaining arguments after image

## Behavior
```bash
rockerc --claude ubuntu:22.04           # Use claude extension, override image
rockerc --user --git                     # Add extensions to config
rockerc ubuntu:22.04                     # Override image only
rockerc ubuntu:22.04 bash -c "echo hi"   # Override image with command
```

## Implementation
- Add `parse_cli_extensions_and_image()` function
- Returns: (extensions: list[str], image: str|None, command: list[str])
- Merge CLI extensions with config extensions
- CLI image overrides config image if provided
