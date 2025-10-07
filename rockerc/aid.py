"""
aid - AI Develop command

A tool that combines renv's containerization with interactive AI CLIs for automated development.

Usage: aid repo_owner/repo_name <prompt in plain text>
"""

import sys
import logging
import argparse
import shlex
from typing import List, Optional

from .renv import (
    RepoSpec,
    get_container_name,
    run_renv,
)

MODEL_SELECTION = {
    "claude": {
        "binary": "claude",
        "prompt_args": ["-p"],
        "description": "Use Claude CLI (default)",
    },
    "codex": {
        "binary": "codex",
        "prompt_args": ["-p"],
        "description": "Use Codex CLI",
    },
    "gemini": {
        "binary": "gemini",
        "prompt_args": ["-p"],
        "description": "Use Gemini CLI",
    },
}


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
  aid --codex owner/repo@branch "fix bug in parser"
  aid --gemini owner/repo --force "refactor main module"
        """,
    )

    model_group = parser.add_mutually_exclusive_group()
    model_group.add_argument(
        "--claude", action="store_true", help=MODEL_SELECTION["claude"]["description"]
    )
    model_group.add_argument(
        "--codex", action="store_true", help=MODEL_SELECTION["codex"]["description"]
    )
    model_group.add_argument(
        "--gemini", action="store_true", help=MODEL_SELECTION["gemini"]["description"]
    )

    parser.add_argument(
        "repo_spec",
        help="Repository specification: owner/repo[@branch][#subfolder]",
    )

    parser.add_argument(
        "prompt", nargs="+", help="Prompt for the selected model (joined with spaces)"
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

        model_key = "claude"
        if parsed_args.codex:
            model_key = "codex"
        elif parsed_args.gemini:
            model_key = "gemini"
        elif parsed_args.claude:
            model_key = "claude"

        model_config = MODEL_SELECTION[model_key]

        # If no-container, setup worktree only
        if parsed_args.no_container:
            renv_args: List[str] = []
            if parsed_args.force:
                renv_args.append("--force")
            if parsed_args.nocache:
                renv_args.append("--nocache")
            renv_args.append("--no-container")
            renv_args.append(parsed_args.repo_spec)
            return run_renv(renv_args)

        # Determine the container workspace path
        # renv mounts at /workspaces/{container_name}
        container_name = get_container_name(repo_spec)
        workspace_path = f"/workspaces/{container_name}"
        if repo_spec.subfolder:
            workspace_path = f"{workspace_path}/{repo_spec.subfolder}"

        # Run claude in interactive mode with prompt
        # The command needs to be a single bash -c string that rocker will pass to docker
        model_cmd_parts = [model_config["binary"], *model_config["prompt_args"], prompt_text]
        model_cmd_str = shlex.join(model_cmd_parts)
        claude_cmd_str = f"cd {shlex.quote(workspace_path)} && {model_cmd_str}"
        claude_cmd = ["bash", "-lc", claude_cmd_str]

        renv_args: List[str] = []
        if parsed_args.force:
            renv_args.append("--force")
        if parsed_args.nocache:
            renv_args.append("--nocache")
        renv_args.append(parsed_args.repo_spec)
        renv_args.extend(["--", *claude_cmd])

        return run_renv(renv_args)

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
