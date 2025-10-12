"""Helpers for loading embedded completion scripts."""

from __future__ import annotations

from importlib import resources


def load_completion_script(name: str) -> str:
    """Return the text of the embedded completion script."""
    package = "rockerc.completions"
    resource = resources.files(package).joinpath(f"{name}.bash")
    return resource.read_text(encoding="utf-8")
