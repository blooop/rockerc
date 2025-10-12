# aid completion
_aid_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="--help --claude --codex --gemini --yolo --flash -y -f"

    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        local renv_root="${RENV_DIR:-$HOME/renv}"
        local cache_root="$renv_root/.cache"

        if [[ "$cur" == *"#"* ]]; then
            local spec_part="${cur%%#*}"
            local repo_part="${spec_part%%@*}"
            local branch_part="${spec_part##*@}"
            local owner="${repo_part%%/*}"
            local repo="${repo_part##*/}"
            local safe_branch="${branch_part//\//-}"
            local branch_dir="$renv_root/$owner/$repo/$safe_branch/$repo"

            if [[ -d "$branch_dir" ]]; then
                local folders=$(find "$branch_dir" -type d -not -path "*/.git/*" -not -name ".git" | sed "s|$branch_dir/||" | grep -v "^$" | xargs)
                local completions=""
                for folder in $folders; do
                    completions="$completions $spec_part#$folder"
                done
                COMPREPLY=( $(compgen -W "${completions}" -- ${cur}) )
            fi
            return 0
        elif [[ "$cur" == *"@"* ]]; then
            local repo_part="${cur%%@*}"
            local owner="${repo_part%%/*}"
            local repo="${repo_part##*/}"
            local repo_dir="$cache_root/$owner/$repo"
            if [[ -d "$repo_dir" ]]; then
                local branches=$(git -C "$repo_dir" branch -r 2>/dev/null | sed 's/.*origin\///' | grep -v HEAD | xargs)
                local completions=""
                for branch in $branches; do
                    completions="$completions $repo_part@$branch"
                done
                COMPREPLY=( $(compgen -W "${completions}" -- ${cur}) )
            fi
            return 0
        else
            compopt -o nospace 2>/dev/null
            if [[ -d "$cache_root" ]]; then
                local repos=""
                local users=$(find "$cache_root" -maxdepth 1 -type d -exec basename {} \; | grep -v "^\.cache$")
                for user in $users; do
                    if [[ -d "$cache_root/$user" ]]; then
                        local user_repos=$(find "$cache_root/$user" -maxdepth 1 -type d -exec basename {} \; | grep -v "^$user$")
                        for repo in $user_repos; do
                            repos="$repos $user/$repo"
                        done
                    fi
                done
                COMPREPLY=( $(compgen -W "${repos}" -- ${cur}) )
            fi
            return 0
        fi
    fi

    return 0
}

complete -F _aid_completion aid
# end aid completion

