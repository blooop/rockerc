# Completion scripts for worktree_docker


def bash_completion():
    """Return bash completion script as a string."""
    return """
# Bash completion for worktree_docker
_complete_worktree_docker() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    opts="init start stop status"
    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "--help --version" -- ${cur}) )
        return 0
    fi
    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}
complete -F _complete_worktree_docker worktree_docker
"""


def zsh_completion():
    """Return zsh completion script as a string."""
    return """
#compdef worktree_docker
_arguments '*:command:(init start stop status)'
"""


def fish_completion():
    """Return fish completion script as a string."""
    return """
# Fish completion for worktree_docker
complete -c worktree_docker -f -a "init start stop status"
"""
