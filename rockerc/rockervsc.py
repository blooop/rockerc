"""rockervsc thin alias for rockerc with --vsc implied.

The legacy implementation is replaced by argument injection and delegation to
`rockerc.run_rockerc` to ensure a single code path for container + VS Code attach flows.
"""

from .rockerc import run_rockerc  # type: ignore
import sys


def main():  # pragma: no cover - thin wrapper
    if "--vsc" not in sys.argv:
        sys.argv.insert(1, "--vsc")
    run_rockerc()


if __name__ == "__main__":  # pragma: no cover - script entry
    main()
