"""Shared CLI parsing helpers for rockerc/renv entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class FlagSpec:
    """Specification for a boolean or value-taking CLI flag."""

    name: str
    aliases: Tuple[str, ...] = ()
    takes_value: bool = False
    key: Optional[str] = None
    default: Any = False

    @property
    def all_names(self) -> Tuple[str, ...]:
        return (self.name, *self.aliases)

    @property
    def resolved_key(self) -> str:
        return self.key if self.key else self.name.lstrip("-").replace("-", "_")


def consume_flags(
    argv: Sequence[str], specs: Sequence[FlagSpec]
) -> Tuple[Dict[str, Any], List[str]]:
    """Consume known flags from argv and return (values, remaining_args).

    Args:
        argv: Original argument list (without executable name)
        specs: Flag specifications describing which tokens to consume

    Returns:
        Tuple of (flag_values, remaining_args)
    """
    flag_map: Dict[str, FlagSpec] = {}
    values: Dict[str, Any] = {}
    for spec in specs:
        for token in spec.all_names:
            flag_map[token] = spec
        values[spec.resolved_key] = spec.default

    remaining: List[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        spec = flag_map.get(token)
        if not spec:
            remaining.append(token)
            i += 1
            continue

        key = spec.resolved_key
        if spec.takes_value:
            try:
                value = argv[i + 1]
            except (
                IndexError
            ) as exc:  # pragma: no cover - defensive, validated by argparse historically
                raise ValueError(f"Flag {token} requires a value") from exc
            values[key] = value
            i += 2
        else:
            values[key] = True
            i += 1
    return values, remaining


def parse_cli_extensions_and_positional(
    args: Iterable[str],
) -> Tuple[List[str], Optional[str], List[str]]:
    """Parse CLI arguments into (extensions, first_positional, remainder command)."""
    extensions: List[str] = []
    positional: Optional[str] = None
    command: List[str] = []

    positional_found = False
    for arg in args:
        if isinstance(arg, str) and arg.startswith("--"):
            extensions.append(arg[2:])
            continue
        if not positional_found:
            positional = arg
            positional_found = True
        else:
            command.append(arg)

    return extensions, positional, command


def parse_cli_extensions_and_image(
    args: Iterable[str],
) -> Tuple[List[str], Optional[str], List[str]]:
    """Backward-compatible alias for rockerc's original helper."""

    return parse_cli_extensions_and_positional(args)
