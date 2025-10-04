# Implementation Plan

## 1. Add `parse_cli_extensions_and_image()` function

```python
def parse_cli_extensions_and_image(args: list[str]) -> tuple[list[str], str | None, list[str]]:
    """Parse CLI arguments into extensions, image, and command.

    Returns: (extensions, image, command)

    Examples:
        ['--claude', 'ubuntu:22.04'] -> (['claude'], 'ubuntu:22.04', [])
        ['--user', '--git', 'ubuntu:22.04', 'bash'] -> (['user', 'git'], 'ubuntu:22.04', ['bash'])
        ['ubuntu:22.04'] -> ([], 'ubuntu:22.04', [])
    """
```

Logic:
- Iterate through args
- If arg starts with `--`, extract extension name and add to extensions list
- First non-flag arg is the image
- Remaining args are command

## 2. Update `run_rockerc()` workflow

```python
# Parse CLI args
cli_extensions, cli_image, cli_command = parse_cli_extensions_and_image(filtered_cli)

# Merge CLI extensions with config extensions
if cli_extensions:
    merged_dict["args"] = deduplicate_extensions(merged_dict.get("args", []) + cli_extensions)

# Override image if provided
if cli_image:
    merged_dict["image"] = cli_image

# Pass command through as extra_cli for injection
extra_cli = " ".join(cli_command) if cli_command else ""
```

## 3. Testing approach
- Test with various CLI argument combinations
- Ensure backward compatibility (no args, flags only, etc.)
- Verify image override works
- Verify extension merging works
