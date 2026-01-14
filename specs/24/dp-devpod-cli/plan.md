# dp CLI Implementation Plan

## Architecture

```
rockerc/
├── dp.py              # Main CLI entry point
└── completions/
    └── dp.bash        # Bash completion script
```

## Phase 1: Core CLI

### Entry Point (dp.py)

1. **Argument Parsing**
   - Parse flags: `--ls`, `--stop`, `--rm`, `--code`, `--recreate`, `--reset`, `--install`
   - Parse workspace identifier (name or git URL with optional @branch)
   - Parse optional command to run

2. **Workspace Identifier Formats**
   - Existing workspace name: `myworkspace`
   - Git URL: `github.com/owner/repo` or `github.com/owner/repo@branch`
   - Local path: `./path` or `/absolute/path`

3. **Core Functions**
   - `list_workspaces()` - Parse `devpod list --output json`
   - `get_workspace_status(name)` - Get workspace state
   - `up_workspace(spec, ide=None)` - Start or create workspace
   - `ssh_workspace(name, command=None)` - Attach to workspace
   - `stop_workspace(name)` - Stop workspace
   - `delete_workspace(name)` - Delete workspace

### FZF Selector

1. `fuzzy_select_workspace()` - Interactive workspace selection
   - Show: workspace name, source type, last used
   - Use iterfzf for consistent UX with renv

### Command Flow

```python
def main():
    if no args:
        workspace = fuzzy_select_workspace()
        if workspace:
            up_workspace(workspace)
            ssh_workspace(workspace)
    elif --ls:
        list_workspaces()
    elif --stop:
        stop_workspace(args.workspace)
    elif --rm:
        delete_workspace(args.workspace)
    elif --code:
        up_workspace(args.workspace, ide="vscode")
    else:
        up_workspace(args.workspace)
        if command:
            ssh_workspace(args.workspace, command)
        else:
            ssh_workspace(args.workspace)
```

## Phase 2: Bash Completion

### Completion Script (dp.bash)

1. **Workspace Name Completion**
   - Query `devpod list --output json`
   - Extract workspace IDs
   - Cache results for performance

2. **Flag Completion**
   - Complete `--ls --stop --rm --code --recreate --reset --install`

3. **Git URL Completion**
   - After `github.com/`: list known repos from workspace sources
   - After `@`: list branches using `git ls-remote`

### Completion Registration

```bash
_dp_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Flag completion
    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "--ls --stop --rm --code --recreate --reset --install" -- "$cur"))
        return
    fi

    # Workspace completion for commands requiring workspace
    if [[ "$prev" == "--stop" || "$prev" == "--rm" || "$prev" == "--code" ]]; then
        local workspaces=$(devpod list --output json 2>/dev/null | jq -r '.[].id')
        COMPREPLY=($(compgen -W "$workspaces" -- "$cur"))
        return
    fi

    # Default: workspace names
    local workspaces=$(devpod list --output json 2>/dev/null | jq -r '.[].id')
    COMPREPLY=($(compgen -W "$workspaces" -- "$cur"))
}
complete -F _dp_completion dp
```

## Phase 3: Registration

1. Add entry point to pyproject.toml
2. Add completion to install_all_completions()
3. Test with `pixi run ci`

## DevPod Commands Mapping

| dp Command | devpod Command |
|------------|----------------|
| `dp ws` | `devpod up ws && devpod ssh ws` |
| `dp ws cmd` | `devpod up ws && devpod ssh ws --command "cmd"` |
| `dp --ls` | `devpod list` |
| `dp --stop ws` | `devpod stop ws` |
| `dp --rm ws` | `devpod delete ws` |
| `dp --code ws` | `devpod up ws --ide vscode` |
| `dp --recreate ws` | `devpod up ws --recreate` |
| `dp --reset ws` | `devpod up ws --reset` |

## Key Design Decisions

1. **Workspace-first**: Unlike renv's `owner/repo@branch` format, dp uses devpod workspace names directly
2. **Minimal wrapping**: Delegate heavy lifting to devpod, focus on UX
3. **Fast completion**: Use cached `devpod list` for instant completion
4. **fzf for discovery**: Easy workspace selection without remembering names
