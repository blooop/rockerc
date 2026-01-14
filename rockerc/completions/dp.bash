# dp completion
_dp_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Command options
    opts="--ls --repos --stop --rm --code --status --recreate --reset --install --help"

    # Flag completion
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    # Commands that need workspace completion
    if [[ "$prev" == "--stop" || "$prev" == "--rm" || "$prev" == "--code" || "$prev" == "--status" || "$prev" == "--recreate" || "$prev" == "--reset" ]]; then
        local workspaces
        workspaces=$(devpod list --output json 2>/dev/null | jq -r '.[].id' 2>/dev/null)
        if [[ -n "$workspaces" ]]; then
            COMPREPLY=( $(compgen -W "${workspaces}" -- ${cur}) )
        fi
        return 0
    fi

    # First positional argument: workspace, owner/repo, or path
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        # Don't add space after completion to allow @branch suffix
        compopt -o nospace

        # Get existing workspace names
        local workspaces
        workspaces=$(devpod list --output json 2>/dev/null | jq -r '.[].id' 2>/dev/null)

        # If typing a path, complete files/directories
        if [[ "$cur" == ./* || "$cur" == /* || "$cur" == ~/* ]]; then
            compopt +o nospace
            COMPREPLY=( $(compgen -d -- ${cur}) )
            return 0
        fi

        # Get known repos from dp
        local known_repos
        known_repos=$(dp --repos 2>/dev/null)

        # Check if completing owner/repo format (contains /)
        if [[ "$cur" == */* ]]; then
            # Complete from known repos
            if [[ -n "$known_repos" ]]; then
                COMPREPLY=( $(compgen -W "${known_repos}" -- ${cur}) )
            fi
            return 0
        fi

        # Default: complete workspace names and offer owner/ completion
        local completions="$workspaces"

        # Add unique owners from known repos for owner/ completion
        if [[ -n "$known_repos" ]]; then
            local owners
            owners=$(echo "$known_repos" | cut -d'/' -f1 | sort -u)
            for owner in $owners; do
                completions="$completions ${owner}/"
            done
        fi

        if [[ -n "$completions" ]]; then
            COMPREPLY=( $(compgen -W "${completions}" -- ${cur}) )
        fi
        return 0
    fi

    return 0
}

complete -F _dp_completion dp
# end dp completion
