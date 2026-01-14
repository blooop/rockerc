# dp completion
_dp_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Command options
    opts="--ls --stop --rm --code --status --recreate --reset --install --help"

    # Flag completion
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    # Commands that need workspace completion
    if [[ "$prev" == "--stop" || "$prev" == "--rm" || "$prev" == "--code" || "$prev" == "--status" || "$prev" == "--recreate" || "$prev" == "--reset" ]]; then
        local workspaces=$(devpod list --output json 2>/dev/null | jq -r '.[].id' 2>/dev/null)
        if [[ -n "$workspaces" ]]; then
            COMPREPLY=( $(compgen -W "${workspaces}" -- ${cur}) )
        fi
        return 0
    fi

    # First positional argument: workspace or git URL
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        # Don't add space after completion to allow @branch suffix
        compopt -o nospace

        # Get existing workspace names
        local workspaces=$(devpod list --output json 2>/dev/null | jq -r '.[].id' 2>/dev/null)

        # If typing github.com/, offer owner/repo completion from existing workspaces
        if [[ "$cur" == github.com/* ]]; then
            # Extract git repos from existing workspaces
            local git_repos=$(devpod list --output json 2>/dev/null | jq -r '.[].source.gitRepository // empty' 2>/dev/null | grep -v "^$")
            if [[ -n "$git_repos" ]]; then
                COMPREPLY=( $(compgen -W "${git_repos}" -- ${cur}) )
            fi
        # If typing a path, complete files/directories
        elif [[ "$cur" == ./* || "$cur" == /* || "$cur" == ~/* ]]; then
            compopt +o nospace
            COMPREPLY=( $(compgen -d -- ${cur}) )
        else
            # Complete workspace names
            if [[ -n "$workspaces" ]]; then
                COMPREPLY=( $(compgen -W "${workspaces}" -- ${cur}) )
            fi
        fi
        return 0
    fi

    return 0
}

complete -F _dp_completion dp
# end dp completion
