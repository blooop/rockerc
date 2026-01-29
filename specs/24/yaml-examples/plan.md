# Implementation Plan for rockerc.yaml Examples

## Files to Create

### 1. examples/ Directory Structure
Create a new `examples/` directory at the project root containing:

- `examples/basic.yaml` - Simple configuration with image and common extensions
- `examples/advanced.yaml` - Complex configuration with multiple features
- `examples/dockerfile.yaml` - Using a Dockerfile instead of an image
- `examples/global-config.yaml` - Example for ~/.rockerc.yaml
- `examples/vscode.yaml` - VS Code specific configuration
- `examples/blacklist.yaml` - Demonstrating extension-blacklist feature
- `examples/README.md` - Comprehensive documentation of syntax and options

### 2. Documentation Updates
- Update main README.md to reference examples
- Add detailed configuration reference to examples/README.md

## Configuration Options to Document

### Required Fields
- `image`: Docker image to use (e.g., `ubuntu:24.04`)
- `dockerfile`: Alternative to image - path to Dockerfile

### Args Field
- List of rocker extensions to enable
- Common extensions: x11, user, pull, git, cwd, nvidia, cuda, etc.
- Custom extensions available through rocker plugins

### Optional Fields
- `name`: Container name
- `image-name`: Image name for the built image
- `volume`: Custom volume mounts (format: `HOST:CONTAINER:OPTIONS`)
- `extension-blacklist`: List of extensions to exclude

### CLI Integration
- How CLI arguments merge with YAML config
- CLI extensions append to config extensions
- CLI image overrides config image

## Examples to Create

### Basic Example
Simple dev container with common tools

### Advanced Example
Full-featured setup with:
- GPU support (nvidia)
- X11 forwarding
- Custom volume mounts
- Git integration
- Multiple dev tools

### Dockerfile Example
Using a custom Dockerfile instead of a base image

### Global Config Example
System-wide defaults in ~/.rockerc.yaml

### VS Code Example
Configuration optimized for VS Code devcontainer workflow

### Blacklist Example
Show how to exclude unwanted extensions from global config

## Implementation Steps
1. Create examples/ directory
2. Write each example YAML file with inline comments
3. Create examples/README.md with comprehensive documentation
4. Update main README.md to reference examples
5. Test each example to ensure they work
6. Run CI to validate
