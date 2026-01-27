# rockerc.yaml Configuration Guide

This directory contains example `rockerc.yaml` configuration files that demonstrate how to use rockerc with various setups and features.

## Quick Start

1. Copy one of the example files to your project directory as `rockerc.yaml`
2. Customize the `image` and `args` to match your needs
3. Run `rockerc` in that directory

```bash
# Copy basic example
cp examples/basic.yaml ./rockerc.yaml

# Run rockerc
rockerc
```

## Available Examples

- **[basic.yaml](basic.yaml)** - Simple configuration with common extensions
- **[advanced.yaml](advanced.yaml)** - Complex setup with multiple features
- **[dockerfile.yaml](dockerfile.yaml)** - Using a custom Dockerfile instead of an image
- **[global-config.yaml](global-config.yaml)** - System-wide defaults for `~/.rockerc.yaml`
- **[intel-gpu.yaml](intel-gpu.yaml)** - Mounting Intel GPU for hardware acceleration
- **[blacklist.yaml](blacklist.yaml)** - Excluding unwanted extensions

## Configuration Syntax

### Basic Structure

```yaml
# Required: Specify either 'image' or 'dockerfile'
image: ubuntu:24.04

# Required: List of rocker extensions to enable
args:
  - x11
  - user
  - git
```

### Configuration Fields

#### `image` (string, required unless using `dockerfile`)
The base Docker image to use.

```yaml
image: ubuntu:24.04
image: nvidia/cuda:12.0.0-base-ubuntu22.04
image: ros:jazzy
```

#### `dockerfile` (string, alternative to `image`)
Path to a Dockerfile to build instead of using a pre-built image. Path is relative to the location of `rockerc.yaml`.

```yaml
dockerfile: ./Dockerfile
dockerfile: ./docker/Dockerfile.dev
```

**Note:** When using `dockerfile`, the `pull` extension is automatically removed since you're building locally.

#### `args` (list, required)
List of rocker extensions to enable. Each extension adds functionality to your container.

```yaml
args:
  - x11      # X11 forwarding for GUI apps
  - user     # Match host user/group IDs
  - nvidia   # NVIDIA GPU support
```

See [Available Extensions](#available-extensions) below for a complete list.

#### `name` (string, optional)
Custom container name. If not specified, rockerc generates a name based on the project directory.

```yaml
name: my-dev-container
```

#### `image-name` (string, optional)
Custom name for the built image (when using rocker).

```yaml
image-name: my-custom-image
```

#### `volume` (string, optional)
Additional volume mounts in Docker format: `HOST_PATH:CONTAINER_PATH[:OPTIONS]`

```yaml
volume: ~/.ssh:/root/.ssh:ro
volume: /data:/workspace/data
```

For multiple volumes, you can use YAML multi-line:
```yaml
volume: |
  ~/.ssh:/root/.ssh:ro
  /data:/workspace/data
```

Or pass via CLI: `rockerc --volume ~/.ssh:/root/.ssh:ro --volume /data:/workspace/data`

#### `devices` (string, optional)
Device paths to mount into the container for hardware access (e.g., GPU, cameras).

```yaml
devices: /dev/dri              # Intel GPU
devices: /dev/video0           # Webcam
devices: /dev/snd              # Audio devices
```

Common use cases:
- `/dev/dri` - Intel integrated GPU for hardware acceleration
- `/dev/video*` - Webcams and video capture devices
- `/dev/snd` - Audio devices
- `/dev/ttyUSB*` - Serial devices

#### `extension-blacklist` (list, optional)
List of extensions to exclude, even if they appear in global config or merged args.

```yaml
extension-blacklist:
  - nvidia    # Disable GPU support
  - x11       # Disable X11 for headless container
```

## Available Extensions

Common rocker extensions you can use in `args`:

### Display & GUI
- `x11` - X11 forwarding for GUI applications
- `nvidia` - NVIDIA GPU support with display capabilities

### User & Permissions
- `user` - Create a user matching your host user/group ID
- `user-preserve-home` - Preserve home directory structure
- `privileged` - Run container in privileged mode (use with caution)

### Development Tools
- `git` - Install and configure git with host credentials
- `ssh` - SSH integration
- `dev-helpers` - Development tools (emacs, byobu)
- `deps` - Common system dependencies
- `deps-devtools` - Developer productivity tools (ripgrep, fd-find, fzf)
- `curl` - Install curl
- `nvim` - Install Neovim

### Package Managers
- `pixi` - Install pixi package manager
- `uv` - Install uv Python package manager
- `conda` - Install Miniconda
- `npm` - Install Node.js and npm
- `cargo` - Install Rust and Cargo
- `homebrew` - Install Homebrew

### Container Features
- `pull` - Pull latest image before running
- `detach` - Run container in detached mode
- `cwd` - Mount current working directory at ~/project_name
- `auto` - Automatically discover and mount workspace

### GPU & Compute
- `nvidia` - NVIDIA GPU support
- `cuda` - Install CUDA and nvidia-cuda-dev

### AI Development Tools
- `claude` - Install Claude Code CLI
- `codex` - Install OpenAI Codex CLI
- `gemini` - Install Gemini CLI

### Other Extensions
- `ccache` - Install ccache and share cache with host
- `locales` - Configure locales
- `tzdata` - Configure timezone
- `pulse` - PulseAudio support
- `home` - Mount home directory

For a complete and up-to-date list, run:
```bash
rocker --help
```

## Configuration Hierarchy

rockerc supports two configuration locations that are merged:

1. **Global config**: `~/.rockerc.yaml` - System-wide defaults
2. **Project config**: `./rockerc.yaml` - Project-specific settings

### Merge Behavior

- **`args` field**: Lists are merged and deduplicated (global + project)
- **Other fields**: Project config overrides global config
- **`extension-blacklist`**: Lists are merged to exclude extensions from either source

### Example: Global + Project Config

**~/.rockerc.yaml** (global):
```yaml
args:
  - pull
  - persist-image
  - x11
  - user
  - cwd
  - git
  - git-clone
  - ssh
  - ssh-client
  - dev-helpers
```

**./rockerc.yaml** (project):
```yaml
image: ubuntu:24.04
args:
  - nvidia
  - cuda
  - pixi
```

**Result**: Final args are `[pull, persist-image, x11, user, cwd, git, git-clone, ssh, ssh-client, dev-helpers, nvidia, cuda, pixi]`

### Using Blacklist

**~/.rockerc.yaml** (global):
```yaml
args:
  - pull
  - persist-image
  - x11
  - user
  - cwd
  - git
  - git-clone
  - ssh
  - ssh-client
  - nvidia
```

**./rockerc.yaml** (project):
```yaml
image: ubuntu:24.04
args:
  - pixi
extension-blacklist:
  - nvidia      # Don't need GPU for this project
  - x11         # Headless container
  - ssh         # No SSH server needed
  - ssh-client  # No SSH client needed
```

**Result**: Final args are `[pull, persist-image, user, cwd, git, git-clone, pixi]`

## CLI Integration

rockerc accepts additional arguments that merge with or override the YAML config:

### Adding Extensions via CLI
```bash
# Add nvidia extension to config args
rockerc nvidia

# Add multiple extensions
rockerc nvidia cuda
```

### Overriding Image
```bash
# Override the image specified in rockerc.yaml
rockerc -- ubuntu:22.04
```

### Passing Additional Options
```bash
# Pass arbitrary rocker/docker options
rockerc --env MY_VAR=value --port 8080:8080

# With image override
rockerc --env MY_VAR=value -- ubuntu:24.04
```

### VS Code Integration
```bash
# Launch container and attach VS Code
rockerc --vsc

# Or use the alias
rockervsc

# Force recreate container
rockerc --vsc --force
```

## Common Patterns

### Minimal Dev Container (Basic)
```yaml
image: ubuntu:24.04
args:
  - pull
  - persist-image
  - x11
  - user
  - cwd
  - git
  - git-clone
  - ssh
  - ssh-client
```

### Python Development
```yaml
image: python:3.12
args:
  # Core extensions
  - pull
  - persist-image
  - x11
  - user
  - cwd
  - git
  - git-clone
  - ssh
  - ssh-client
  # Python-specific
  - uv
  - pixi
```

### NVIDIA GPU Development
```yaml
image: nvidia/cuda:12.0.0-base-ubuntu22.04
args:
  # Core extensions
  - pull
  - persist-image
  - x11
  - user
  - cwd
  - git
  - git-clone
  - ssh
  - ssh-client
  # GPU support
  - nvidia
```

### ROS Development
```yaml
image: ros:jazzy
args:
  # Core extensions
  - pull
  - persist-image
  - x11
  - user
  - cwd
  - git
  - git-clone
  - ssh
  - ssh-client
  # ROS-specific
  - nvidia
  - dev-helpers
```

### AI/ML Development with Claude Code
```yaml
image: ubuntu:24.04
args:
  # Core extensions
  - pull
  - persist-image
  - x11
  - user
  - cwd
  - git
  - git-clone
  - ssh
  - ssh-client
  # AI/ML tools
  - nvidia
  - cuda
  - claude
  - pixi
  - uv
```

## Quirks and Limitations

### 1. Extension Order
Most extensions are order-independent, but some have requirements:
- `cache-perms` must run before extensions that mount subdirectories under `.cache` (like `claude`)

### 2. Dockerfile + Pull
When using `dockerfile`, the `pull` extension is automatically removed since you're building locally.

### 3. Detached Mode
rockerc always runs containers in detached mode and attaches via `docker exec` for better reliability.

### 4. Container Naming
If you don't specify a `name`, rockerc generates one based on your project directory. This ensures consistent container names across runs.

### 5. Workspace Mounting
With `--vsc` or `rockervsc`, the workspace is always mounted at `/workspaces/<container-name>` to match VS Code's expectations.

### 6. Environment Variables in Config
You can use environment variables in the YAML:
```yaml
name: '"$CONTAINER_NAME"'
volume: '"${PWD}":/workspaces/"${CONTAINER_NAME}":Z'
```

### 7. YAML Indentation
Ensure consistent indentation for list items:

❌ **Incorrect**:
```yaml
args:
 - x11
  - user  # Inconsistent indentation
```

✅ **Correct**:
```yaml
args:
  - x11
  - user
```

## Troubleshooting

### "No rockerc.yaml found"
Make sure you have a `rockerc.yaml` file in the current directory or set up a global `~/.rockerc.yaml`.

### "No 'args' key found"
The `args` field is required. Add at least one extension:
```yaml
args:
  - user
```

### Extensions Not Working
- Check that the extension name is spelled correctly
- Run `rocker --help` to see all available extensions
- Some extensions require specific base images (e.g., `nvidia` needs NVIDIA drivers)

### YAML Parsing Errors
- Check for consistent indentation (use spaces, not tabs)
- Ensure list items start with `- `
- Validate your YAML syntax with a YAML validator

### Container Already Exists
If you want to recreate a container:
```bash
rockerc --force
```

Or manually remove it:
```bash
docker rm -f <container-name>
rockerc
```

## Additional Resources

- [rockerc README](../README.md) - Main project documentation
- [rocker GitHub](https://github.com/osrf/rocker) - Underlying rocker tool
- [rocker extensions](https://github.com/osrf/rocker) - Extension documentation
- [Issue #120](https://github.com/blooop/rockerc/issues/120) - Original feature request

## Contributing

Found an issue or want to add more examples? Please [open an issue](https://github.com/blooop/rockerc/issues) or submit a pull request!
