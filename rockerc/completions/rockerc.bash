# rockerc completion
_rockerc_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="--help --vsc --force -f --verbose -v --show-dockerfile --install --rc-file --auto"

    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    return 0
}

complete -F _rockerc_completion rockerc
# end rockerc completion

