"""Utilities for installing shell autocompletion scripts."""

from __future__ import annotations

import logging
import os
import pathlib
from typing import Optional

from .completion_loader import load_completion_script

_RC_BLOCK_START = "# >>> rockerc completions >>>"
_RC_BLOCK_END = "# <<< rockerc completions <<<"

_LEGACY_BLOCKS = {
    "# rockerc completion": "# end rockerc completion",
    "# renv completion": "# end renv completion",
    "# aid completion": "# end aid completion",
    _RC_BLOCK_START: _RC_BLOCK_END,
}

_LEGACY_SINGLE_LINES = {
    "complete -F _rockerc_completion rockerc",
    "complete -F _renv_completion renv",
    "complete -F _renv_completion renvvsc",
    "complete -F _aid_completion aid",
}


def _rockerc_bash_completion_script() -> str:
    """Return bash completion script for the rockerc CLI."""
    return load_completion_script("rockerc")


def _completion_file_path() -> pathlib.Path:
    """Return the path where aggregated completion scripts should be stored."""
    override = os.environ.get("ROCKERC_COMPLETION_FILE")
    if override:
        return pathlib.Path(override).expanduser()
    return pathlib.Path.home() / ".config" / "rockerc" / "completions.sh"


def _strip_old_completion_blocks(content: str) -> str:
    """Remove legacy inline completion blocks from rc files."""
    lines = content.splitlines()
    cleaned: list[str] = []
    skip_until: Optional[str] = None

    for line in lines:
        stripped = line.strip()
        if skip_until is not None:
            if stripped == skip_until:
                skip_until = None
            continue
        if stripped in _LEGACY_BLOCKS:
            skip_until = _LEGACY_BLOCKS[stripped]
            continue
        if stripped in _LEGACY_SINGLE_LINES:
            continue
        cleaned.append(line)

    # Collapse duplicate blank lines and trim leading/trailing blanks.
    collapsed: list[str] = []
    previous_blank = False
    for line in cleaned:
        if line.strip():
            collapsed.append(line)
            previous_blank = False
        else:
            if not previous_blank:
                collapsed.append(line)
            previous_blank = True

    while collapsed and not collapsed[0].strip():
        collapsed.pop(0)
    while collapsed and not collapsed[-1].strip():
        collapsed.pop()

    return "\n".join(collapsed)


def install_all_completions(rc_path: Optional[pathlib.Path] = None) -> int:
    """Install or refresh completion scripts for rockerc, renv/renvvsc, and aid."""
    completion_path = _completion_file_path().expanduser()
    rc_target = (rc_path if rc_path is not None else pathlib.Path.home() / ".bashrc").expanduser()

    try:
        completion_path.parent.mkdir(parents=True, exist_ok=True)

        combined_script_parts = [
            _rockerc_bash_completion_script().rstrip(),
            load_completion_script("renv").rstrip(),
            load_completion_script("aid").rstrip(),
        ]
        combined_script = "\n\n".join(combined_script_parts) + "\n"
        completion_path.write_text(combined_script, encoding="utf-8")
        logging.info("Wrote completion scripts to %s", completion_path)

        rc_target.parent.mkdir(parents=True, exist_ok=True)
        existing_content = ""
        if rc_target.exists():
            existing_content = rc_target.read_text(encoding="utf-8")

        stripped_content = _strip_old_completion_blocks(existing_content).strip("\n")
        escaped_path = str(completion_path).replace('"', r"\"")
        source_line = f'source "{escaped_path}"'
        block = "\n".join([_RC_BLOCK_START, source_line, _RC_BLOCK_END])

        if stripped_content:
            new_content = f"{stripped_content}\n\n{block}\n"
        else:
            new_content = f"{block}\n"

        rc_target.write_text(new_content, encoding="utf-8")
        logging.info("Added completion source block to %s", rc_target)
        logging.info("Run 'source %s' or restart your terminal to enable completion", rc_target)
        return 0
    except OSError as error:
        logging.error("Failed to install completions: %s", error)
        return 1
