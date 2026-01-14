# dp - DevPod CLI Wrapper

## Overview

`dp` is a CLI tool providing an intuitive, autocomplete-friendly interface for devpod workspace management. It wraps devpod with fzf fuzzy selection and bash completion for seamless UX.

## Syntax

```bash
dp [workspace[@branch]] [command]
dp                           # fzf selector for existing workspaces
dp <workspace>               # open/create workspace, attach shell
dp <workspace> <command>     # run command in workspace
dp owner/repo                # create from git repo (github.com)
dp owner/repo@branch         # specific branch
dp ./path                    # create from local path
dp --ls                      # list workspaces
dp --stop <workspace>        # stop workspace
dp --rm <workspace>          # delete workspace
dp --code <workspace>        # open in VS Code
dp --install                 # install completions
```

## Commands

| Command | Action |
|---------|--------|
| (none)  | fzf selector if no args; start/attach workspace if given |
| `--ls`  | List all workspaces |
| `--stop` | Stop workspace |
| `--rm`  | Delete workspace |
| `--code` | Open workspace in VS Code |
| `--recreate` | Recreate workspace container |
| `--reset` | Reset workspace (clean slate) |
| `--install` | Install bash completions |

## Autocomplete

Tab completion provides:
- Existing workspace names
- Owner/repo format for git repos (auto-expands to github.com URL)
- Branch completion after `@`
- Flag completion

## FZF Selection

Running `dp` with no arguments launches fzf with:
- All existing workspaces
- Last used time
- Source type (local/git)

## Implementation

Uses devpod CLI as backend:
- `devpod up` for workspace creation/start
- `devpod ssh` for shell attachment
- `devpod list` for workspace enumeration
- `devpod stop/delete` for lifecycle management
