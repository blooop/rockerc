#!/usr/bin/env python3
"""
renv - Repository Environment Manager

A tool that makes it seamless to work in a variety of repos at the same time
using git worktrees and rocker containers.

Usage:
    renv [repo_name@branch]

Examples:
    renv blooop/bencher@main
    renv osrf/rocker
    renv blooop/bencher@feature_branch
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from .rockerc import run_rockerc

# TODO: Add autocomplete functionality using prompt-toolkit
# Example implementation would include:
# - Autocomplete for repo names (blooop/, osrf/, etc.)
# - Autocomplete for branch names after @ symbol
# - Integration with git commands to get available repos and branches


def setup_logging():
    """Set up logging for renv."""
    logging.basicConfig(level=logging.INFO, format="[renv] %(levelname)s: %(message)s")


def parse_repo_spec(repo_spec: str) -> Tuple[str, str, str]:
    """
    Parse a repository specification like 'owner/repo@branch' or 'owner/repo'.

    Args:
        repo_spec: Repository specification string

    Returns:
        Tuple of (owner, repo, branch)

    Raises:
        ValueError: If the repo specification is invalid
    """
    if "@" in repo_spec:
        repo_part, branch = repo_spec.split("@", 1)
    else:
        repo_part = repo_spec
        branch = "main"

    if "/" not in repo_part:
        raise ValueError(
            f"Invalid repo specification: {repo_spec}. Expected format: owner/repo[@branch]"
        )

    owner, repo = repo_part.split("/", 1)

    if not owner or not repo:
        raise ValueError(f"Invalid repo specification: {repo_spec}. Owner and repo cannot be empty")

    return owner, repo, branch


def get_renv_base_dir() -> Path:
    """Get the base directory for renv repositories."""
    return Path.home() / "renv"


def get_repo_dir(owner: str, repo: str) -> Path:
    """Get the directory for a specific repository."""
    return get_renv_base_dir() / owner / repo


def get_worktree_dir(owner: str, repo: str, branch: str) -> Path:
    """Get the directory for a specific worktree."""
    # Replace slashes in branch names with dashes for directory names
    safe_branch = branch.replace("/", "-")
    return get_repo_dir(owner, repo) / f"worktree-{safe_branch}"


def repo_exists(owner: str, repo: str) -> bool:
    """Check if a repository has been cloned already."""
    repo_dir = get_repo_dir(owner, repo)
    # For bare repositories, check for HEAD file instead of .git directory
    return repo_dir.exists() and (repo_dir / "HEAD").exists()


def worktree_exists(owner: str, repo: str, branch: str) -> bool:
    """Check if a worktree exists for the given branch."""
    worktree_dir = get_worktree_dir(owner, repo, branch)
    return worktree_dir.exists() and (worktree_dir / ".git").exists()


def clone_bare_repo(owner: str, repo: str) -> None:
    """
    Clone a repository as a bare repo.

    Args:
        owner: Repository owner
        repo: Repository name
    """
    repo_dir = get_repo_dir(owner, repo)
    repo_url = f"https://github.com/{owner}/{repo}"

    logging.info(f"Cloning {repo_url} as bare repository to {repo_dir}")

    # Create parent directories
    repo_dir.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            ["git", "clone", "--bare", repo_url, str(repo_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        logging.info(f"Successfully cloned {repo_url}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to clone {repo_url}: {e.stderr}")
        raise


def create_worktree(owner: str, repo: str, branch: str) -> Path:
    """
    Create a worktree for the specified branch.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name

    Returns:
        Path to the created worktree
    """
    repo_dir = get_repo_dir(owner, repo)
    worktree_dir = get_worktree_dir(owner, repo, branch)

    if worktree_exists(owner, repo, branch):
        logging.info(f"Worktree already exists for {owner}/{repo}@{branch}")
        return worktree_dir

    logging.info(f"Creating worktree for {owner}/{repo}@{branch}")

    try:
        # First, try to create worktree from existing branch
        subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), branch],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    except subprocess.CalledProcessError:
        # If branch doesn't exist locally, try to create it from remote
        try:
            subprocess.run(
                ["git", "worktree", "add", "-b", branch, str(worktree_dir), f"origin/{branch}"],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True,
            )

        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to create worktree for branch {branch}: {e.stderr}")
            raise

    logging.info(f"Successfully created worktree at {worktree_dir}")
    return worktree_dir


def fetch_repo(owner: str, repo: str) -> None:
    """
    Fetch latest changes from the remote repository.

    Args:
        owner: Repository owner
        repo: Repository name
    """
    repo_dir = get_repo_dir(owner, repo)

    logging.info(f"Fetching latest changes for {owner}/{repo}")

    try:
        subprocess.run(
            ["git", "fetch", "origin"], cwd=repo_dir, check=True, capture_output=True, text=True
        )
        logging.info("Successfully fetched latest changes")
    except subprocess.CalledProcessError as e:
        logging.warning(f"Failed to fetch changes: {e.stderr}")


def run_rockerc_in_worktree(worktree_dir: Path) -> None:
    """
    Run rockerc in the specified worktree directory.

    Args:
        worktree_dir: Path to the worktree directory
    """
    original_cwd = os.getcwd()
    original_argv = sys.argv.copy()  # Save original argv

    try:
        os.chdir(worktree_dir)
        # Clear sys.argv to prevent renv arguments from being passed to rocker
        sys.argv = [sys.argv[0]]  # Keep only the script name
        logging.info(f"Running rockerc in {worktree_dir}")
        run_rockerc(str(worktree_dir))
    except Exception as e:
        logging.error(f"Failed to run rockerc: {e}")
        raise
    finally:
        os.chdir(original_cwd)
        sys.argv = original_argv  # Restore original argv


def setup_repo_environment(owner: str, repo: str, branch: str) -> Path:
    """
    Set up the repository environment (clone if needed, create worktree).

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name

    Returns:
        Path to the worktree directory
    """
    # Clone repository if it doesn't exist
    if not repo_exists(owner, repo):
        clone_bare_repo(owner, repo)
    else:
        # Fetch latest changes if repo already exists
        fetch_repo(owner, repo)

    # Create worktree if it doesn't exist
    worktree_dir = create_worktree(owner, repo, branch)

    return worktree_dir


def main():
    """Main entry point for renv."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Repository Environment Manager - seamlessly work in multiple repos using git worktrees and rocker containers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  renv blooop/bencher@main          # Clone blooop/bencher and switch to main branch
  renv blooop/bencher@feature       # Switch to feature branch (creates worktree if needed)
  renv osrf/rocker                  # Clone osrf/rocker and switch to main branch (default)
  
The tool will:
1. Clone the repository as a bare repo to ~/renv/owner/repo (if not already cloned)
2. Create a worktree for the specified branch at ~/renv/owner/repo/worktree-{branch}
3. Run rockerc in that worktree to build and enter a container
        """,
    )

    parser.add_argument(
        "repo_spec",
        help="Repository specification in format 'owner/repo[@branch]'. If branch is omitted, 'main' is used.",
    )

    parser.add_argument(
        "--no-container",
        action="store_true",
        help="Set up the worktree but don't run rockerc (for debugging or manual container management)",
    )

    args = parser.parse_args()

    try:
        # Parse the repository specification
        owner, repo, branch = parse_repo_spec(args.repo_spec)
        logging.info(f"Setting up environment for {owner}/{repo}@{branch}")

        # Set up the repository environment
        worktree_dir = setup_repo_environment(owner, repo, branch)

        if args.no_container:
            logging.info(f"Environment ready at {worktree_dir}")
            logging.info(f"To manually run rockerc: cd {worktree_dir} && rockerc")
        else:
            # Run rockerc in the worktree
            run_rockerc_in_worktree(worktree_dir)

    except ValueError as e:
        logging.error(f"Invalid repository specification: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"Git operation failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
