"""renvvsc thin alias for renv with --vsc implied.

Following the same pattern as rockervsc, this is a thin wrapper that adds
the --vsc flag and delegates to run_renv() for all functionality.
"""

from .renv import run_renv  # type: ignore
import sys


def main():  # pragma: no cover - thin wrapper
    if "--vsc" not in sys.argv:
        sys.argv.insert(1, "--vsc")
    sys.exit(run_renv())


if __name__ == "__main__":
    main()
