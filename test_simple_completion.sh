#!/bin/bash
# Minimal test completion script

_renv_complete() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Simple test candidates instead of calling renv
    local candidates="user1/repo1 user2/repo2 user1/repo1@main user1/repo1@develop"
    
    # Convert candidates to array and set COMPREPLY
    if [[ -n "$candidates" ]]; then
        COMPREPLY=($(compgen -W "$candidates" -- "$cur"))
    else
        COMPREPLY=()
    fi
}

# Register the completion function
complete -F _renv_complete renv

echo "Simple bash completion for renv installed successfully!"
echo "The completion will provide static test candidates: user1/repo1, user2/repo2, user1/repo1@main, user1/repo1@develop"
