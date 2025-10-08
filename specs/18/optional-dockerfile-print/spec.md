# Optional Dockerfile Printing

Make printing the generated dockerfile optional, only showing it when `--show-dockerfile` is passed.

## Current Behavior
The generated dockerfile is printed when `--verbose` is enabled and dockerfile generation occurs.

## Desired Behavior
The generated dockerfile should only be printed when `--show-dockerfile` flag is explicitly passed, independent of verbose mode.

## Implementation
1. Add `--show-dockerfile` flag to CLI argument parser
2. Update dockerfile printing condition to check for this flag instead of verbose mode
