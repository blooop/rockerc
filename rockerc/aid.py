"""
aid - AI Develop command

A tool that combines renv's containerization with Claude Code CLI for automated development.

Usage: aid repo_owner/repo_name <prompt in plain text>
"""

import sys
import logging
import argparse
from typing import List, Optional

from .renv import (
    RepoSpec,
    manage_container,
    get_container_name,
)


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
        help="Set up worktree only, do not launch container",
    )

    parsed_args = parser.parse_args(args)

    try:
        # Parse repo specification
        repo_spec = RepoSpec.parse(parsed_args.repo_spec)
        logging.info(f"Working with: {repo_spec}")

        # Join prompt arguments into single string
        prompt_text = " ".join(parsed_args.prompt)
        logging.info(f"Prompt: {prompt_text}")

        # If no-container, setup worktree only
        if parsed_args.no_container:
            from .renv import setup_branch_copy, get_worktree_dir

            setup_branch_copy(repo_spec)
            worktree_dir = get_worktree_dir(repo_spec)
            logging.info(f"Worktree set up at: {worktree_dir}")
            return 0

        # Build claude command in agent mode
        # Just run Claude directly - user will see live output and can interact
        # Escape single quotes in prompt for shell
        escaped_prompt = prompt_text.replace("'", "'\\''")

        # Determine the container workspace path
        # renv mounts at /workspaces/{container_name}
        container_name = get_container_name(repo_spec)
        workspace_path = f"/workspaces/{container_name}"
        if repo_spec.subfolder:
            workspace_path = f"{workspace_path}/{repo_spec.subfolder}"

        # Run claude directly in the workspace
        claude_cmd = ["bash", "-c", f"cd {workspace_path} && claude --agent -p '{escaped_prompt}'"]

        # Launch container with claude command
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
