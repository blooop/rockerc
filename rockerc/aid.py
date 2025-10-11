"""
aid - AI Develop command for rockerc

Provides streamlined AI-driven development within containerized environments.
Reuses renv infrastructure for container management and setup.
"""

import sys
import argparse
import logging
from typing import List, Optional

from .renv import RepoSpec, manage_container


def parse_aid_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments for aid command."""
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="AI Develop - Streamlined AI-driven development in containerized environments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aid blooop/my-repo "help me refactor this code"
  aid --claude owner/repo@dev "implement a new feature" 
  aid --gemini owner/repo#subfolder "debug this issue"
        """,
    )

    # AI Agent selection (mutually exclusive)
    agent_group = parser.add_mutually_exclusive_group()
    agent_group.add_argument(
        "--gemini",
        action="store_const",
        dest="agent",
        const="gemini",
        help="Use Gemini AI (default)",
    )
    agent_group.add_argument(
        "--claude", action="store_const", dest="agent", const="claude", help="Use Claude AI"
    )
    agent_group.add_argument(
        "--codex", action="store_const", dest="agent", const="codex", help="Use OpenAI Codex"
    )

    # y/--yolo flag
    parser.add_argument(
        "-y",
        "--yolo",
        action="store_true",
        help="Pass --yolo to gemini agent",
    )

    # Repository specification
    parser.add_argument(
        "repo_spec", help="Repository specification: owner/repo[@branch][#subfolder]"
    )

    # Prompt (remaining arguments)
    parser.add_argument("prompt", nargs="+", help="Prompt to send to AI agent")

    # Set default agent
    parser.set_defaults(agent="gemini")

    return parser.parse_args(args)


def build_ai_command(agent: str, prompt: str) -> List[str]:
    """Build the AI CLI command for the specified agent and prompt.

    Args:
        agent: AI agent type ('gemini', 'claude', 'codex')
        prompt: The prompt text to send to the agent

    Returns:
        List of command components for execution
    """
    # Escape single quotes in prompt for shell safety
    escaped_prompt = prompt.replace("'", "'\"'\"'")

    def build_gemini_cmd(yolo: bool) -> List[str]:
        cmd = ["gemini", "--prompt-interactive"]
        if yolo:
            cmd.append("--yolo")
        cmd.append(f'"{escaped_prompt}"')
        return cmd

    if agent == "gemini":
        # Use gemini CLI with --prompt-interactive and optional --yolo
        import inspect
        frame = inspect.currentframe()
        outer = frame.f_back
        parsed_args = outer.f_locals.get("parsed_args")
        yolo = False
        if parsed_args and hasattr(parsed_args, "yolo"):
            yolo = parsed_args.yolo or getattr(parsed_args, "y", False)
        return build_gemini_cmd(yolo)
    if agent == "claude":
        # Use claude CLI - send prompt then start interactive mode
        return [
            "bash",
            "-c",
            f"claude '{escaped_prompt}' && echo 'Starting interactive session...' && claude",
        ]
    if agent == "codex":
        # Use openai CLI for interactive chat with GPT-4
        return [
            "bash",
            "-c",
            f"openai api chat.completions.create -m gpt-4 -g user '{escaped_prompt}' && echo 'Starting interactive session...' && openai api chat.completions.create -m gpt-4",
        ]
    raise ValueError(f"Unsupported AI agent: {agent}")


def run_aid(args: Optional[List[str]] = None) -> int:
    """Main entry point for aid command."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        parsed_args = parse_aid_args(args)

        # Parse repository specification
        repo_spec = RepoSpec.parse(parsed_args.repo_spec)
        logging.info(f"Working with: {repo_spec}")

        # Combine prompt parts into single string
        prompt_text = " ".join(parsed_args.prompt)
        logging.info(
            f"Using {parsed_args.agent} with prompt: {prompt_text[:100]}{'...' if len(prompt_text) > 100 else ''}"
        )

        # Build AI command
        ai_command = build_ai_command(parsed_args.agent, prompt_text)

        # Use renv's container management to execute the AI command
        return manage_container(
            repo_spec=repo_spec,
            command=ai_command,
            force=False,  # Don't force rebuild unless needed
            nocache=False,  # Use cache for faster startup
            no_container=False,  # We need the container for AI CLI
            vsc=False,  # Terminal mode, not VSCode
        )

    except ValueError as e:
        logging.error(f"Invalid repository specification: {e}")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1


def main():
    """Entry point for the aid command."""
    sys.exit(run_aid())


if __name__ == "__main__":
    main()
