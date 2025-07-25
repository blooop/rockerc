#!/bin/bash
# Bash completion script for renv
# This script provides tab completion for renv commands

_renv_complete() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Get completion candidates from renv itself
    local candidates
    candidates=$(renv --list-candidates "${COMP_WORDS[@]:1}" 2>/dev/null)
    
    # Convert candidates to array and set COMPREPLY
    if [[ -n "$candidates" ]]; then
        COMPREPLY=($(compgen -W "$candidates" -- "$cur"))
    else
        COMPREPLY=()
    fi
}

# Register the completion function
complete -F _renv_complete renv
