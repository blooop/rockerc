# wtd Extensions System

wtd now features a modular extension system where each extension is organized in its own directory with standardized files. This allows for better organization, easier maintenance, and simpler custom extension development.

## Architecture

### Built-in Extensions

Built-in extensions are located in the `extensions/` directory:

```
extensions/
├── base/                    # Foundation Ubuntu image with essential tools
├── user/                    # User setup and permissions
├── git/                     # Git configuration and SSH key mounting
├── x11/                     # GUI application support
├── nvidia/                  # GPU acceleration
├── uv/                      # Python package manager
├── pixi/                    # Conda-compatible package manager
└── fzf/                     # Fuzzy finder tool
```

### Extension Structure

Each extension directory contains:

```
extension-name/
├── Dockerfile              # Docker build instructions
└── docker-compose.yml      # Service configuration (volumes, environment, etc.)
```

#### Dockerfile
Contains Docker instructions to install and configure the extension. This is a fragment that gets combined with other extensions during the build process.

#### docker-compose.yml
Contains Docker Compose service overrides for the extension (volumes, environment variables, network settings, etc.). Only include the keys you want to override or add.

## Custom Extensions

### Repository-Local Extensions

You can create custom extensions in your repository:

```
your-repo/
└── .wtd/
    └── extensions/
        └── my-extension/
            ├── Dockerfile
            └── docker-compose.yml
```

### Example Custom Extension

Here's a simple example that installs a custom tool:

**`.wtd/extensions/my-tool/Dockerfile`:**
```dockerfile
RUN apt-get update && apt-get install -y my-custom-tool && \
    rm -rf /var/lib/apt/lists/*
```

**`.wtd/extensions/my-tool/docker-compose.yml`:**
```yaml
environment:
  MY_TOOL_CONFIG: "/workspace/config"
  MY_TOOL_VERSION: "1.0"
volumes:
  - "./config:/workspace/config:ro"
```

## Extension Loading

Extensions are loaded in the following order:

1. **Built-in extensions** - From the `extensions/` directory
2. **Repository-local extensions** - From `.wtd/extensions/` in your repo
3. **Auto-detected extensions** - Based on files in your repository
4. **Explicitly requested extensions** - Via `-e` flag

### Auto-Detection Rules

wtd automatically detects extensions based on files in your repository:

| File Pattern | Extension Loaded | Reason |
|-------------|-----------------|---------|
| `pyproject.toml` | `uv` | Python package management |
| `pixi.toml` | `pixi` | Pixi package management |
| `package.json` | `uv` | Node.js projects often benefit from uv |
| `Cargo.toml` | `uv` | Rust projects can use uv for Python tooling |
| `poetry.lock` | `uv` | Poetry projects can migrate to uv |
| `requirements*.txt` | `uv` | Python requirements files |
| `.python-version` | `uv` | Python version specification |
| `environment.yml` | `uv` | Conda environment files |

### Extension Discovery

Repository-local extensions are automatically discovered from:

- **New structure**: `.wtd/extensions/extension-name/`
- **Legacy structure**: `.wtd/exts/extension-name/` (backward compatibility)

## Migration from Hardcoded Extensions

The system maintains backward compatibility while providing the new modular structure:

### Before (Hardcoded)
Extensions were defined directly in Python code with hardcoded Dockerfile content and compose fragments.

### After (Modular)
Extensions are loaded from the filesystem, making them:
- Easier to maintain and modify
- Self-contained and organized
- Testable independently
- Extensible by users

## Best Practices

### Creating Custom Extensions

1. **Keep extensions focused** - Each extension should have a single responsibility
2. **Use descriptive names** - Extension names should clearly indicate their purpose
3. **Document your extensions** - Include README files for complex extensions
4. **Test thoroughly** - Ensure your extensions work in isolation and with others
5. **Consider dependencies** - Make sure required base extensions are available

### Extension Development

1. **Start with Dockerfile** - Define what needs to be installed
2. **Add compose configuration** - Define runtime requirements
3. **Test incrementally** - Test with minimal extension set first
4. **Check for conflicts** - Ensure your extension doesn't conflict with others

### Performance Considerations

1. **Layer caching** - Structure Dockerfile commands for optimal caching
2. **Minimal installs** - Only install what's necessary
3. **Cleanup** - Remove temporary files and caches in the same RUN layer

## Example Workflows

### Using Built-in Extensions
```bash
# Automatically loads base, user, and uv (from pyproject.toml)
wtd owner/repo@branch

# Explicitly load additional extensions
wtd -e git nvidia owner/repo@branch
```

### Using Custom Extensions
```bash
# Custom extensions are automatically discovered
cd my-project-with-custom-extensions
wtd owner/repo@branch  # Loads built-in + auto-detected + custom extensions
```

### Creating a Custom Extension
```bash
# 1. Create extension directory
mkdir -p .wtd/extensions/my-extension

# 2. Create Dockerfile
cat > .wtd/extensions/my-extension/Dockerfile << 'EOF'
RUN pip install my-custom-package
EOF

# 3. Create compose configuration
cat > .wtd/extensions/my-extension/docker-compose.yml << 'EOF'
environment:
  MY_VAR: "custom-value"
EOF

# 4. Test the extension
wtd owner/repo@branch
```

## Built-in Extension Details

### base
- **Purpose**: Provides Ubuntu 22.04 foundation with essential development tools
- **Includes**: git, curl, wget, unzip, build-essential, ca-certificates, gnupg, lsb-release
- **Required**: Always loaded first

### user  
- **Purpose**: Sets up the wtd user with proper permissions
- **Features**: Creates user, adds to sudoers, sets working directory
- **Required**: Always loaded (after base)

### git
- **Purpose**: Git configuration and credential access
- **Features**: Mounts ~/.gitconfig and ~/.ssh from host
- **Dependencies**: base (git already installed)

### x11
- **Purpose**: GUI application support with X11 forwarding
- **Features**: X11 forwarding, OpenGL support
- **Auto-disabled**: With `--no-gui` flag

### nvidia
- **Purpose**: GPU acceleration via NVIDIA Docker runtime
- **Features**: NVIDIA runtime, GPU device access
- **Auto-disabled**: With `--no-gpu` flag

### uv
- **Purpose**: Fast Python package manager
- **Installation**: Downloads and installs uv from official installer
- **Auto-detected**: From pyproject.toml and other Python files

### pixi
- **Purpose**: Conda-compatible package manager
- **Installation**: Downloads and installs pixi
- **Auto-detected**: From pixi.toml files

### fzf
- **Purpose**: Command-line fuzzy finder
- **Installation**: Clones from GitHub and installs for wtd user

## Troubleshooting

### Extension Not Loading
1. Check extension directory structure
2. Verify Dockerfile syntax
3. Check docker-compose.yml format
4. Look for error messages in wtd output

### Extension Conflicts
1. Check for conflicting environment variables
2. Review port mappings
3. Verify volume mount conflicts
4. Check if extensions modify the same files

### Build Failures
1. Review Dockerfile for syntax errors
2. Check if base dependencies are available
3. Verify network access for downloads
4. Look at Docker build logs for specific errors

## Contributing Extensions

We welcome contributions of useful extensions! To contribute:

1. Create the extension in the `extensions/` directory
2. Follow the established patterns and naming conventions
3. Include comprehensive documentation
4. Add tests if applicable
5. Submit a pull request

Extensions should be:
- Generally useful to the community
- Well-tested and documented
- Following security best practices
- Compatible with the existing extension ecosystem