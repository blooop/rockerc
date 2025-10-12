"""
aid - AI Develop command for rockerc

Provides streamlined AI-driven development within containerized environments.
Reuses renv infrastructure for container management and setup.
"""

import argparse
import logging
import pathlib
import sys
from typing import List, Optional

from .completion_loader import load_completion_script
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
    parser.add_argument(
        "-f",
        "--flash",
        action="store_true",
        help="Use Gemini in flash mode (gemini-2.5-flash)",
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


def generate_aid_completion(shell: str = "bash") -> str:
    """Generate completion script for the requested shell."""
    if shell != "bash":
        raise ValueError("Only bash completion is currently supported for aid")
    return load_completion_script("aid")


def aid_completion_block(shell: str = "bash") -> str:
    """Return the completion block for aid with standard markers."""
    script = generate_aid_completion(shell)
    return f"{script.rstrip()}\n"


def install_aid_completion(shell: str = "bash", rc_path: Optional[pathlib.Path] = None) -> int:
    """Install or update aid shell completion via centralized installer."""
    if shell != "bash":
        logging.error("Only bash completion is currently supported for aid")
        return 1

    try:
        from .completion import install_all_completions
    except ImportError as error:  # pragma: no cover - defensive
        logging.error("Unable to load completion installer: %s", error)
        return 1
    return install_all_completions(rc_path)


def build_ai_command(
    agent: str, prompt: str, *, yolo: bool = False, flash: bool = False
) -> List[str]:
    """Build the AI CLI command for the specified agent and prompt.

    Args:
        agent: AI agent type ('gemini', 'claude', 'codex')
        prompt: The prompt text to send to the agent

    Returns:
        List of command components for execution
    """
    # Escape single quotes in prompt for shell safety
    escaped_prompt = prompt.replace("'", "'\"'\"'")

    def build_gemini_cmd(yolo_flag: bool, flash_flag: bool) -> List[str]:
        cmd = ["gemini", "--prompt-interactive"]
        if flash_flag:
            cmd.extend(["--model", "gemini-2.5-flash"])
        if yolo_flag:
            cmd.append("--yolo")
        cmd.append(f'"{escaped_prompt}"')
        return cmd

    if agent == "gemini":
        return build_gemini_cmd(yolo, flash)
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

        if parsed_args.flash and parsed_args.agent != "gemini":
            logging.warning(
                "--flash is only supported with Gemini; ignoring for %s", parsed_args.agent
            )

        # Build AI command
        ai_command = build_ai_command(
            parsed_args.agent,
            prompt_text,
            yolo=getattr(parsed_args, "yolo", False),
            flash=getattr(parsed_args, "flash", False) if parsed_args.agent == "gemini" else False,
        )

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
