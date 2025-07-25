# Enhanced renv Tool - Autocompletion and Version Display

This document describes the enhancements made to the `renv` tool to support autocompletion and version display.

## New Features

### 1. Version Display

When called without arguments or with the `-v`/`--version` flag, `renv` now displays the version number from `pyproject.toml`:

```bash
# Display version when no arguments provided
renv
# Output: renv version 0.7.2.4

# Display version with explicit flag
renv -v
renv --version
# Output: renv version 0.7.2.4
```

### 2. Intelligent Autocompletion

The tool now includes comprehensive autocompletion support using `argcomplete`:

#### User Completion
When typing a partial username, it completes based on existing directories in `~/renv/`:
```bash
renv blo<TAB>    # Completes to blooop/ if ~/renv/blooop/ exists
```

#### Repository Completion
When typing after a username with `/`, it completes repository names:
```bash
renv blooop/ben<TAB>    # Completes to blooop/bencher if ~/renv/blooop/bencher exists
```

#### Branch Completion
When typing after a repository with `@`, it completes branch names using git commands:
```bash
renv blooop/bencher@fea<TAB>    # Completes to available branches like feature/xyz
```

### 3. Automated Installation Commands

New built-in commands for easy setup and removal:

#### Install Command
```bash
renv --install
```
Automatically detects available global package managers (uv tool, pipx, pip --user) and installs argcomplete globally. Falls back to virtual environment installation if needed.

#### Uninstall Command
```bash
renv --uninstall
```
Removes autocompletion configuration from your shell and optionally uninstalls argcomplete.

## Implementation Details

### Version Reading
The version is read from `pyproject.toml` using the following priority:
1. `tomllib` (Python 3.11+)
2. `tomli` (fallback for older Python versions)
3. Basic string parsing (ultimate fallback)

### Autocompletion Logic
- **Filesystem-aware**: Looks at actual directory structure in `~/renv/`
- **Git-aware**: Uses `git branch -r` to get available branches
- **Graceful degradation**: Works even if `argcomplete` is not installed
- **Safe error handling**: Continues working even if git commands fail

### Dependencies
- `argcomplete>=3.0` added to project dependencies
- Graceful fallback when argcomplete is not available
- Global installation support via:
  - `uv tool` (preferred)
  - `pipx`
  - `pip --user`
  - Virtual environment (fallback)

## Setup Instructions

### Enable Autocompletion
To enable autocompletion in your shell:

```bash
# For bash/zsh
eval "$(register-python-argcomplete renv)"

# Make it permanent by adding to ~/.bashrc or ~/.zshrc
echo 'eval "$(register-python-argcomplete renv)"' >> ~/.bashrc
```

### Install Global Argcomplete Support (Optional)
For system-wide argcomplete support using global package managers:

```bash
# Option 1: Using uv tool (recommended)
uv tool install argcomplete

# Option 2: Using pipx
pipx install argcomplete

# Option 3: Using pip --user
pip install --user argcomplete

# Activate global argcomplete (optional)
activate-global-python-argcomplete
```

### Automated Setup with renv --install
The easiest way to setup autocompletion is using the built-in install command:

```bash
# No virtual environment required - installs globally!
renv --install
```

This command will:
1. Detect available global package managers (uv tool, pipx, pip --user)
2. Install argcomplete globally using the best available method
3. Add autocompletion setup to your shell configuration (.bashrc/.zshrc)
4. Attempt to activate global argcomplete
5. Fall back to virtual environment installation if needed

**Priority order:**
1. `uv tool install argcomplete` (preferred)
2. `pipx install argcomplete`
3. `pip install --user argcomplete`
4. Virtual environment installation (if active)

### Remove Setup with renv --uninstall
To remove the autocompletion setup:

```bash
renv --uninstall
```

This will:
1. Remove autocompletion configuration from your shell
2. Optionally uninstall the argcomplete package

## Usage Examples

### Basic Usage
```bash
# Show version
renv

# Show version explicitly
renv -v

# Install autocompletion setup (globally)
renv --install

# Remove autocompletion setup
renv --uninstall

# Use repository with autocompletion
renv blooop/bencher@main

# Setup without entering container
renv --no-container blooop/bencher@feature
```

### Autocompletion Examples
Assuming you have repositories set up in `~/renv/`:

```bash
# Complete usernames
renv <TAB>
# Shows: blooop/ osrf/ myuser/ ...

# Complete repositories for a user
renv blooop/<TAB>
# Shows: blooop/bencher blooop/another-repo ...

# Complete branches for a repository
renv blooop/bencher@<TAB>
# Shows: main develop feature/xyz ...
```

## Code Structure

### New Functions Added
- `get_version()`: Reads version from pyproject.toml
- `get_existing_repos()`: Scans ~/renv for existing repositories
- `get_branches_for_repo()`: Gets branches for a specific repository
- `repo_completer()`: Argcomplete completer function
- `detect_global_package_manager()`: Detects uv tool, pipx, pip --user availability
- `detect_virtual_env()`: Detects uv/pip virtual environment type (now optional)
- `install_argcomplete()`: Installs and configures argcomplete globally
- `uninstall_argcomplete()`: Removes argcomplete configuration with multiple options

### Modified Functions
- `main()`: Enhanced argument parsing with optional repo_spec and version flags
- Imports: Added argcomplete with safe fallback

## Testing

The implementation includes comprehensive error handling and graceful degradation:
- Continues working if argcomplete is not installed
- Handles permission errors when scanning directories
- Gracefully handles git command failures
- Provides meaningful fallbacks for version reading

## Migration Notes

This is a backward-compatible enhancement. All existing `renv` commands continue to work exactly as before. The only change is that calling `renv` without arguments now shows the version instead of showing an error.

## Future Enhancements

Potential future improvements:
- Cache branch information for faster completion
- Support for custom completion based on recent usage
- Integration with GitHub API for remote repository discovery
- Support for multiple git remotes
