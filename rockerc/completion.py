# pylint: disable=too-many-return-statements
"""Utilities for installing shell autocompletion scripts."""

from __future__ import annotations

import logging
import pathlib
from typing import Callable, Optional


def _rockerc_bash_completion_script() -> str:
    """Return bash completion script for the rockerc CLI."""
    return r"""# rockerc completion
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
"""


def _write_completion_block(
    *,
    script: str,
    rc_path: Optional[pathlib.Path],
    start_marker: str,
    end_marker: str,
) -> int:
    """Write (and replace) a completion block inside rc file."""
    try:
        target_path = rc_path if rc_path is not None else pathlib.Path.home() / ".bashrc"
        target_path = target_path.expanduser()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        existing_content = ""
        if target_path.exists():
            existing_content = target_path.read_text(encoding="utf-8")

        def _strip_existing(content: str) -> str:
            current = content
            while True:
                start_idx = current.find(start_marker)
                if start_idx == -1:
                    break
                end_idx = current.find(end_marker, start_idx)
                if end_idx != -1:
                    end_idx += len(end_marker)
                else:
                    end_idx = current.find("\n", start_idx + len(start_marker))
                    if end_idx == -1:
                        end_idx = len(current)
                    else:
                        end_idx += 1
                before = current[:start_idx].rstrip("\n")
                after = current[end_idx:].lstrip("\n")
                if before and after:
                    current = before + "\n\n" + after
                elif before:
                    current = before + "\n"
                else:
                    current = after
            return current.rstrip("\n")

        updated_content = _strip_existing(existing_content)
        if updated_content:
            updated_content = f"{updated_content}\n\n{script}\n"
        else:
            updated_content = f"{script}\n"

        target_path.write_text(updated_content, encoding="utf-8")
        logging.info("rockerc completion installed to %s", target_path)
        logging.info("Run 'source %s' or restart your terminal to enable completion", target_path)
        return 0
    except OSError as error:
        logging.error("Failed to install rockerc completion: %s", error)
        return 1


def install_rockerc_completion(rc_path: Optional[pathlib.Path] = None) -> int:
    """Install bash completion for the rockerc CLI."""
    script = _rockerc_bash_completion_script()
    return _write_completion_block(
        script=script,
        rc_path=rc_path,
        start_marker="# rockerc completion",
        end_marker="# end rockerc completion",
    )


def install_all_completions(rc_path: Optional[pathlib.Path] = None) -> int:
    """Install or refresh completion scripts for rockerc, renv/renvvsc, and aid."""
    from .aid import install_aid_completion
    from .renv import install_shell_completion

    success = True
    installers: list[tuple[str, Callable[[Optional[pathlib.Path]], int]]] = [
        ("rockerc", install_rockerc_completion),
        (
            "renv",
            lambda path, installer=install_shell_completion: installer(rc_path=path),
        ),
        (
            "aid",
            lambda path, installer=install_aid_completion: installer(rc_path=path),
        ),
    ]
    for name, installer in installers:
        result = installer(rc_path)
        if result != 0:
            logging.error("Completion installer for %s failed with exit code %s", name, result)
            success = False
    return 0 if success else 1
