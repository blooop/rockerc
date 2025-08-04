# renv Extensions

This directory contains the built-in extensions for renv. Each extension is organized in its own directory with the following structure:

```
extension-name/
├── Dockerfile              # Docker build instructions for this extension
└── docker-compose.yml      # Docker Compose service overrides
```

## Built-in Extensions

- **base**: Provides the foundational Ubuntu image with essential development tools
- **user**: Sets up the renv user with proper permissions
- **git**: Configures Git and mounts host Git configuration
- **x11**: Enables GUI application support with X11 forwarding
- **nvidia**: Provides GPU acceleration support via NVIDIA runtime
- **uv**: Installs the uv Python package manager
- **pixi**: Installs the pixi package manager
- **fzf**: Installs the fuzzy finder tool

## Custom Extensions

You can create custom extensions in your repository by creating a `.renv/extensions/` directory:

```
your-repo/
└── .renv/
    └── extensions/
        └── custom-extension/
            ├── Dockerfile
            └── docker-compose.yml
```

### Extension Files

#### Dockerfile
Contains Docker instructions to install and configure the extension. This is a fragment that will be combined with other extensions.

#### docker-compose.yml  
Contains Docker Compose service overrides specific to this extension (volumes, environment variables, etc.). This should contain only the keys you want to override or add.

## Auto-detection

Extensions can be automatically loaded based on files detected in your repository:

- `pyproject.toml` → loads `uv` extension
- `pixi.toml` → loads `pixi` extension  
- `package.json` → loads `uv` extension
- `Cargo.toml` → loads `uv` extension
- Various Python files → loads `uv` extension

## Extension Loading Order

1. Built-in extensions from this directory
2. Repository-local extensions from `.renv/extensions/`
3. Auto-detected extensions based on repository files
4. Explicitly requested extensions via `-e` flag