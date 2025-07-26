# renv Fuzzy Search Documentation

The `renv` tool now supports fuzzy search using `iterfzf` for improved user experience when selecting repositories and branches.

## Features

### Interactive Fuzzy Search
When you run `renv` without any arguments, it will launch an interactive fuzzy finder that allows you to search through all available repositories and branches.

```bash
# Launch interactive fuzzy search
renv
```

### Fuzzy Matching Examples
The fuzzy search supports intelligent matching where you can type partial strings separated by spaces:

- Type `bl ben ma` to quickly find `blooop/bencher@main`
- Type `ben fe1` to find `blooop/bencher@feature1`
- Type `mani` to find `blooop/manifest_rocker`

### Repository and Branch Organization
The fuzzy search presents options in a logical order:
1. Repository names without branches (defaults to main)
2. Repository@branch combinations, with main/master branches prioritized

### Enhanced Interface
The fuzzy search interface includes:
- Custom prompt with usage hints
- Keyboard shortcuts (Ctrl+C to cancel)
- Border and inline info display
- Height-optimized display (40% of terminal)

### Fallback Support
If fuzzy search fails for any reason, the tool gracefully falls back to a simple text input prompt.

## Bash Completion
The existing bash completion functionality remains unchanged and works alongside the fuzzy search:

```bash
# Tab completion for repository names
renv bl<TAB>
# Results: blooop/bencher  blooop/manifest_rocker

# Tab completion for branch names
renv blooop/bencher@<TAB>
# Results: all available branches for blooop/bencher
```

## Dependencies
The fuzzy search functionality requires:
- `iterfzf` Python package
- `fzf` binary (usually available via package managers)

## Installation
The `iterfzf` dependency is automatically installed with the project. If `fzf` is not available, the tool will fall back to simple text input.

## Usage Examples

### Interactive Fuzzy Search
```bash
# Start fuzzy search interface
renv
# Type to search: "bl ben ma"
# Select: blooop/bencher@main
```

### Direct Repository Specification
```bash
# Use directly without fuzzy search
renv blooop/bencher@main
renv osrf/rocker
```

### Bash Completion
```bash
# Use tab completion
renv bl<TAB>
renv blooop/bencher@<TAB>
```

## Technical Implementation

The fuzzy search is implemented using the following key functions:

- `get_all_repo_branch_combinations()`: Generates sorted list of all available repo@branch combinations
- `fuzzy_select_repo_spec()`: Launches the interactive fuzzy finder
- Existing bash completion functions remain unchanged for backward compatibility

The implementation prioritizes user experience with intelligent sorting, error handling, and graceful fallbacks.
