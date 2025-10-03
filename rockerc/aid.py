"""
aid - AI Develop command

A tool that combines renv's containerization with Claude Code CLI for automated development.

Usage: aid repo_owner/repo_name <prompt in plain text>
"""

import sys
import pathlib
import logging
import argparse
from typing import List, Optional

from .renv import (
    RepoSpec,
    setup_branch_copy,
    manage_container,
)

# CLAUDE.MD template for the aid workflow
CLAUDE_MD_TEMPLATE = """This project uses pixi to manage its environment.

look at the pyproject.toml to see the pixi tasks

Workflow:
    * On first message:
        - create a new specification according to the pattern specs/01/short-spec-name/spec.md.  Keep it as concise as possible
        - create a plan in the same folder, you can expand more here
        - commit the contents of this folder only

    * Every time I ask for a change
        - update the spec.md with clarifications while keeping it concise. commit if there are changes
        - implement the change
        - run `pixi run ci`
        - fix errors and iterate until ci passes
        - only if ci passes commit the changes.
"""


def inject_claude_md(worktree_dir: pathlib.Path) -> None:
    """Inject CLAUDE.MD into the worktree root"""
    claude_md_path = worktree_dir / "CLAUDE.md"

    # Write CLAUDE.md file
    with open(claude_md_path, "w", encoding="utf-8") as f:
        f.write(CLAUDE_MD_TEMPLATE)

    logging.info(f"Injected CLAUDE.md into {worktree_dir}")


def run_aid(args: Optional[List[str]] = None) -> int:
    """Main entry point for aid"""
    if args is None:
        args = sys.argv[1:]

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="AI Develop - Automated development with Claude Code in containerized environments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aid blooop/test_renv "add feature to parse yaml files"
  aid owner/repo@branch "fix bug in parser"
  aid owner/repo --force "refactor main module"
        """,
    )

    parser.add_argument(
        "repo_spec",
        help="Repository specification: owner/repo[@branch][#subfolder]",
    )

    parser.add_argument(
        "prompt",
        nargs="+",
        help="Prompt for Claude Code (plain text, will be joined with spaces)",
    )

    parser.add_argument("--force", "-f", action="store_true", help="Force rebuild container")

    parser.add_argument("--nocache", action="store_true", help="Rebuild container with no cache")

    parser.add_argument(
        "--no-container",
        action="store_true",
        help="Set up worktree and inject CLAUDE.md only, do not launch container",
    )

    parsed_args = parser.parse_args(args)

    try:
        # Parse repo specification
        repo_spec = RepoSpec.parse(parsed_args.repo_spec)
        logging.info(f"Working with: {repo_spec}")

        # Join prompt arguments into single string
        prompt_text = " ".join(parsed_args.prompt)
        logging.info(f"Prompt: {prompt_text}")

        # Setup branch copy
        worktree_dir = setup_branch_copy(repo_spec)

        # Inject CLAUDE.md into worktree
        inject_claude_md(worktree_dir)

        # If no-container, just setup and exit
        if parsed_args.no_container:
            logging.info(f"Worktree set up at: {worktree_dir}")
            logging.info("CLAUDE.md injected. Use --no-container=false to launch container.")
            return 0

        # Build claude-code command
        # The command will be executed inside the container
        claude_cmd = ["claude-code", "--prompt", prompt_text]

        # Launch container with claude-code command
        return manage_container(
            repo_spec=repo_spec,
            command=claude_cmd,
            force=parsed_args.force,
            nocache=parsed_args.nocache,
            no_container=False,
            vsc=False,
        )

    except ValueError as e:
        logging.error(f"Invalid repository specification: {e}")
        parser.print_help()
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


def main():
    """Entry point for the aid command"""
    sys.exit(run_aid())


if __name__ == "__main__":
    main()
