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
from typing import Tuple, List, Optional
import toml
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion

from .rockerc import run_rockerc


# --- Autocompletion logic ---
def list_owners_and_repos() -> List[str]:
    base = get_renv_base_dir()
    if not base.exists():
        return []
    owners = []
    for owner_dir in base.iterdir():
        if owner_dir.is_dir():
            for repo_dir in owner_dir.iterdir():
                if repo_dir.is_dir() and (repo_dir / "HEAD").exists():
                    owners.append(f"{owner_dir.name}/{repo_dir.name}")
    return owners

def list_branches(owner: str, repo: str) -> List[str]:
    repo_dir = get_repo_dir(owner, repo)
    if not repo_dir.exists():
        return []
    try:
        result = subprocess.run([
            "git", "--git-dir", str(repo_dir), "branch", "-a"
        ], capture_output=True, text=True, check=True)
        branches = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith('*'):
                continue
            # Remove 'remotes/origin/' prefix and clean up branch names
            if line.startswith('remotes/origin/'):
                branch = line.replace('remotes/origin/', '')
                if branch != 'HEAD':  # Skip HEAD pointer
                    branches.append(branch)
            else:
                branches.append(line)
        # Remove duplicates and sort
        return sorted(set(branches))
    except Exception:
        return []

class RenvCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if "@" in text:
            # Complete branch names
            try:
                owner_repo, partial_branch = text.split("@", 1)
            except ValueError:
                return
            if "/" not in owner_repo:
                return
            owner, repo = owner_repo.split("/", 1)
            for branch in list_branches(owner, repo):
                if branch.startswith(partial_branch):
                    # Calculate how much of the completion to show
                    completion_text = branch[len(partial_branch):]
                    yield Completion(completion_text, start_position=0)
        else:
            # Complete owner/repo
            for owner_repo in list_owners_and_repos():
                if owner_repo.startswith(text):
                    # Calculate how much of the completion to show
                    completion_text = owner_repo[len(text):]
                    yield Completion(completion_text, start_position=0)

def get_version_from_pyproject() -> Optional[str]:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        data = toml.load(pyproject)
        return data.get("project", {}).get("version")
    except Exception:
        return None


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
        # First, try to create worktree from existing local branch
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

        except subprocess.CalledProcessError:
            # If branch doesn't exist on remote either, create new branch from default branch
            logging.info(f"Branch {branch} doesn't exist locally or on remote. Creating new branch from default branch.")
            
            # Determine the default branch (main or master)
            default_branch = get_default_branch(repo_dir)
            logging.info(f"Using {default_branch} as base for new branch {branch}")
            
            try:
                # First try to create from remote reference
                subprocess.run(
                    ["git", "worktree", "add", "-b", branch, str(worktree_dir), f"origin/{default_branch}"],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logging.info(f"Successfully created new branch {branch} from origin/{default_branch}")
                
            except subprocess.CalledProcessError:
                # If remote reference doesn't exist, try with local branch reference
                try:
                    subprocess.run(
                        ["git", "worktree", "add", "-b", branch, str(worktree_dir), default_branch],
                        cwd=repo_dir,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    logging.info(f"Successfully created new branch {branch} from {default_branch}")
                    
                except subprocess.CalledProcessError as e:
                    logging.error(f"Failed to create new branch {branch} from {default_branch}: {e.stderr}")
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


def run_rockerc_in_worktree(worktree_dir: Path, owner: str, repo: str, branch: str) -> None:
    """
    Run rockerc in the specified worktree directory.

    Args:
        worktree_dir: Path to the worktree directory
        owner: Repository owner
        repo: Repository name
        branch: Branch name
    """
    original_cwd = os.getcwd()
    original_argv = sys.argv.copy()  # Save original argv

    try:
        os.chdir(worktree_dir)
        # Generate container name from repo@branch format
        # Replace slashes in branch names with dashes for container name
        safe_branch = branch.replace("/", "-")
        container_name = f"{repo}-{safe_branch}"
        
        # Set sys.argv to pass the container name and hostname to rocker
        # Keep the original program name and add the --name and --hostname arguments
        sys.argv = [original_argv[0], "--name", container_name, "--hostname", container_name]
        logging.info(f"Running rockerc in {worktree_dir} with container name and hostname: {container_name}")
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



# --- Bash completion functions ---

def generate_completion_candidates(partial_words: List[str]) -> List[str]:
    """
    Generate completion candidates based on partial input.
    
    Args:
        partial_words: List of partial words from COMP_WORDS
        
    Returns:
        List of completion candidates
    """
    if not partial_words:
        # No input yet, show all available owner/repo combinations
        return list_owners_and_repos()
    
    current_word = partial_words[-1] if partial_words else ""
    
    if "@" in current_word:
        # Completing branch names
        try:
            owner_repo, partial_branch = current_word.split("@", 1)
        except ValueError:
            return []
        
        if "/" not in owner_repo:
            return []
            
        try:
            owner, repo = owner_repo.split("/", 1)
        except ValueError:
            return []
            
        branches = list_branches(owner, repo)
        candidates = []
        for branch in branches:
            if branch.startswith(partial_branch):
                candidates.append(f"{owner_repo}@{branch}")
        return candidates
    else:
        # Completing owner/repo
        candidates = []
        for owner_repo in list_owners_and_repos():
            if owner_repo.startswith(current_word):
                candidates.append(owner_repo)
        return candidates


def get_completion_script_content() -> str:
    """Generate the bash completion script content."""
    return '''#!/bin/bash
# Bash completion script for renv
# This script provides tab completion for renv commands

_renv_complete() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Get completion candidates from renv itself
    local candidates
    candidates=$(renv --list-candidates "${COMP_WORDS[@]:1}" 2>/dev/null)
    
    # Convert candidates to array and set COMPREPLY
    if [[ -n "$candidates" ]]; then
        COMPREPLY=($(compgen -W "$candidates" -- "$cur"))
    else
        COMPREPLY=()
    fi
}

# Register the completion function
complete -F _renv_complete renv
'''


def install_completion() -> None:
    """Install bash completion for renv."""
    print("Starting completion installation...")
    
    # Determine completion directory
    home = Path.home()
    completion_dir = home / ".local" / "share" / "bash-completion" / "completions"
    completion_file = completion_dir / "renv"
    
    print(f"Completion directory: {completion_dir}")
    print(f"Completion file: {completion_file}")
    
    # Create directory if it doesn't exist
    completion_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {completion_dir}")
    
    # Write completion script
    completion_script = get_completion_script_content()
    completion_file.write_text(completion_script)
    completion_file.chmod(0o755)
    
    print(f"✓ Completion script installed to {completion_file}")
    
    print("\n📋 Next steps:")
    print("1. Reload your shell: source ~/.bashrc")
    print("2. Or start a new terminal session")
    print("3. Try: renv <TAB> for completion!")


def uninstall_completion() -> None:
    """Uninstall bash completion for renv."""
    completion_file = Path.home() / ".local" / "share" / "bash-completion" / "completions" / "renv"
    
    if completion_file.exists():
        completion_file.unlink()
        print(f"✓ Completion script removed from {completion_file}")
    else:
        print("ℹ Completion script was not found (already uninstalled?)")
    
    print("\n📋 Completion disabled.")
    print("Reload your shell or start a new terminal session for changes to take effect.")


def get_default_branch(repo_dir: Path) -> str:
    """
    Get the default branch name for a repository.
    
    Args:
        repo_dir: Path to the bare repository directory
        
    Returns:
        Name of the default branch (e.g., 'main' or 'master')
    """
    try:
        # For bare repositories, try to get the default branch from HEAD
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        default_branch = result.stdout.strip()
        if default_branch and default_branch != "HEAD":
            return default_branch
    except subprocess.CalledProcessError:
        pass
    
    try:
        # If that fails, try to determine from available local branches
        result = subprocess.run(
            ["git", "branch"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        branches = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line:
                # Remove the * marker if present
                branch = line.lstrip('* ')
                branches.append(branch)
        
        # Look for common default branch names in order of preference
        for default_name in ['main', 'master', 'develop']:
            if default_name in branches:
                return default_name
        
        # If no common default found, use the first branch
        if branches:
            return branches[0]
                    
    except subprocess.CalledProcessError:
        pass
    
    # Fallback to 'main' if all else fails
    return 'main'


def main():
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Repository Environment Manager - seamlessly work in multiple repos using git worktrees and rocker containers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  renv blooop/bencher@main          # Clone blooop/bencher and switch to main branch
  renv blooop/bencher@feature       # Switch to feature branch (creates worktree if needed)
  renv osrf/rocker                  # Clone osrf/rocker and switch to main branch (default)
  renv --install                    # Install bash completion
  renv --uninstall                  # Uninstall bash completion
  
The tool will:
1. Clone the repository as a bare repo to ~/renv/owner/repo (if not already cloned)
2. Create a worktree for the specified branch at ~/renv/owner/repo/worktree-{branch}
3. Run rockerc in that worktree to build and enter a container
        """,
    )
    parser.add_argument(
        "repo_spec",
        nargs="?",
        help="Repository specification in format 'owner/repo[@branch]'. If branch is omitted, 'main' is used.",
    )
    parser.add_argument(
        "--no-container",
        action="store_true",
        help="Set up the worktree but don't run rockerc (for debugging or manual container management)",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install bash completion for renv",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall bash completion for renv",
    )
    parser.add_argument(
        "--list-candidates",
        nargs="*",
        help="List completion candidates for given partial input (used by bash completion)",
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version information",
    )
    args = parser.parse_args()

    # Handle version display
    if args.version:
        version = get_version_from_pyproject()
        if version:
            print(f"renv version: {version}")
        else:
            print("renv version: unknown")
        return

    # Handle completion installation/uninstallation
    if args.install:
        install_completion()
        return
    
    if args.uninstall:
        uninstall_completion()
        return
    
    # Handle completion candidate listing
    if args.list_candidates is not None:
        candidates = generate_completion_candidates(args.list_candidates)
        for candidate in candidates:
            print(candidate)
        return

    # If no arguments, prompt for input
    if args.repo_spec is None:
        # Prompt for repo_spec with autocomplete - simple text without color for compatibility
        try:
            user_input = prompt(
                "Enter user_name/repo_name@branch_name: ",
                completer=RenvCompleter(),
                complete_while_typing=True,
            )
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)
        if not user_input.strip():
            sys.exit(0)
        args.repo_spec = user_input.strip()
    try:
        owner, repo, branch = parse_repo_spec(args.repo_spec)
        logging.info(f"Setting up environment for {owner}/{repo}@{branch}")
        worktree_dir = setup_repo_environment(owner, repo, branch)
        if args.no_container:
            logging.info(f"Environment ready at {worktree_dir}")
            logging.info(f"To manually run rockerc: cd {worktree_dir} && rockerc")
        else:
            run_rockerc_in_worktree(worktree_dir, owner, repo, branch)
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
