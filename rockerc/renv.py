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
from typing import List, Tuple

try:
    import argcomplete

    ARGCOMPLETE_AVAILABLE = True
except ImportError:
    ARGCOMPLETE_AVAILABLE = False

from .rockerc import run_rockerc


def get_version() -> str:
    """Get version from pyproject.toml."""
    try:
        # Try using tomllib (Python 3.11+) first
        import tomllib

        with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
    except ImportError:
        # Fall back to tomli for older Python versions
        try:
            import tomli

            with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
                data = tomli.load(f)
        except ImportError:
            # Fall back to basic parsing if no toml library is available
            try:
                with open(
                    Path(__file__).parent.parent / "pyproject.toml", "r", encoding="utf-8"
                ) as f:
                    for line in f:
                        if line.strip().startswith('version = "'):
                            return line.split('"')[1]
            except (FileNotFoundError, IndexError):
                pass
            return "unknown"

    return data.get("project", {}).get("version", "unknown")


def get_existing_repos() -> List[str]:
    """Get list of existing repositories in ~/renv for autocompletion."""
    renv_dir = get_renv_base_dir()
    repos = []

    if not renv_dir.exists():
        return repos

    try:
        for owner_dir in renv_dir.iterdir():
            if owner_dir.is_dir():
                owner = owner_dir.name
                for repo_dir in owner_dir.iterdir():
                    if repo_dir.is_dir() and (repo_dir / "HEAD").exists():  # Check for bare repo
                        repos.append(f"{owner}/{repo_dir.name}")
    except PermissionError:
        pass

    return repos


def get_branches_for_repo(owner: str, repo: str) -> List[str]:
    """Get list of branches for a specific repository."""
    repo_dir = get_repo_dir(owner, repo)
    branches = []

    if not repo_exists(owner, repo):
        return branches

    try:
        # Get remote branches
        result = subprocess.run(
            ["git", "branch", "-r"], cwd=repo_dir, capture_output=True, text=True, check=True
        )

        for line in result.stdout.splitlines():
            branch = line.strip()
            if branch.startswith("origin/"):
                branch_name = branch[7:]  # Remove "origin/" prefix
                if branch_name != "HEAD":  # Skip HEAD pointer
                    branches.append(branch_name)

    except subprocess.CalledProcessError:
        pass

    return branches


def repo_completer(prefix: str, parsed_args=None, **kwargs) -> List[str]:
    """Argcomplete completer for repository specifications."""
    if not ARGCOMPLETE_AVAILABLE:
        return []

    # If there's an @ symbol, complete branch names
    if "@" in prefix:
        repo_part, branch_prefix = prefix.split("@", 1)
        if "/" in repo_part:
            owner, repo = repo_part.split("/", 1)
            branches = get_branches_for_repo(owner, repo)
            return [
                f"{repo_part}@{branch}" for branch in branches if branch.startswith(branch_prefix)
            ]

    # If there's a /, complete repository names for that owner
    elif "/" in prefix:
        owner_prefix, repo_prefix = prefix.split("/", 1)
        renv_dir = get_renv_base_dir()

        if renv_dir.exists():
            try:
                owner_dir = renv_dir / owner_prefix
                if owner_dir.exists() and owner_dir.is_dir():
                    repos = []
                    for repo_dir in owner_dir.iterdir():
                        if repo_dir.is_dir() and (repo_dir / "HEAD").exists():
                            repo_name = repo_dir.name
                            if repo_name.startswith(repo_prefix):
                                repos.append(f"{owner_prefix}/{repo_name}")
                    return repos
            except PermissionError:
                pass

    # Complete owner names
    else:
        renv_dir = get_renv_base_dir()
        owners = []

        if renv_dir.exists():
            try:
                for owner_dir in renv_dir.iterdir():
                    if owner_dir.is_dir():
                        owner = owner_dir.name
                        if owner.startswith(prefix):
                            owners.append(f"{owner}/")
            except PermissionError:
                pass

        return owners

    return []


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


def detect_global_package_manager():
    """Detect available global package managers (uv tool, pipx, pip --user)."""
    # Check for uv tool
    try:
        subprocess.run(['uv', 'tool', '--help'], capture_output=True, check=True)
        return {
            'type': 'uv_tool',
            'command': ['uv', 'tool', 'install'],
            'uninstall_command': ['uv', 'tool', 'uninstall']
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Check for pipx
    try:
        subprocess.run(['pipx', '--version'], capture_output=True, check=True)
        return {
            'type': 'pipx',
            'command': ['pipx', 'install'],
            'uninstall_command': ['pipx', 'uninstall']
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # pip --user is always available if pip exists
    try:
        subprocess.run(['pip', '--version'], capture_output=True, check=True)
        return {
            'type': 'pip_user',
            'command': ['pip', 'install', '--user'],
            'uninstall_command': ['pip', 'uninstall']  # Note: --user not needed for uninstall
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # No global package manager found
    return {
        'type': None,
        'command': None,
        'uninstall_command': None
    }


def detect_virtual_env():
    """Detect the type of virtual environment (uv, pip, etc.) - now optional."""
    venv_info = {
        'type': None,
        'activate_script': None,
        'shell_config': None
    }
    
    # Check for uv environment
    if os.environ.get('UV_VENV') or os.environ.get('VIRTUAL_ENV'):
        venv_path = os.environ.get('UV_VENV') or os.environ.get('VIRTUAL_ENV')
        if venv_path:
            activate_script = Path(venv_path) / "bin" / "activate"
            if activate_script.exists():
                venv_info['type'] = 'uv' if os.environ.get('UV_VENV') else 'pip'
                venv_info['activate_script'] = str(activate_script)
    
    # Detect shell config file
    shell = os.environ.get('SHELL', '/bin/bash')
    if 'zsh' in shell:
        venv_info['shell_config'] = str(Path.home() / '.zshrc')
    elif 'fish' in shell:
        venv_info['shell_config'] = str(Path.home() / '.config' / 'fish' / 'config.fish')
    else:
        venv_info['shell_config'] = str(Path.home() / '.bashrc')
    
    return venv_info


def install_argcomplete():
    """Install and setup argcomplete for renv globally."""
    print("Setting up argcomplete for renv...")
    
    # Check available global package managers
    global_managers = detect_global_package_manager()
    venv_info = detect_virtual_env()
    
    if not global_managers and not venv_info['type']:
        print("❌ No package manager available. Please install one of:")
        print("  - uv (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  - pipx: pip install pipx")
        print("  - Or activate a virtual environment")
        return False
    
    # Prefer global managers over virtual environments
    install_method = None
    if 'uv_tool' in global_managers:
        install_method = 'uv_tool'
        print("✓ Using uv tool for global installation")
    elif 'pipx' in global_managers:
        install_method = 'pipx'
        print("✓ Using pipx for global installation")
    elif 'pip_user' in global_managers:
        install_method = 'pip_user'
        print("✓ Using pip --user for global installation")
    elif venv_info['type']:
        install_method = venv_info['type']
        print(f"✓ Using {venv_info['type']} virtual environment")
    
    try:
        # Install argcomplete based on available method
        print("Installing argcomplete...")
        
        if install_method == 'uv_tool':
            subprocess.run(['uv', 'tool', 'install', 'argcomplete'], 
                          capture_output=True, text=True, check=True)
        elif install_method == 'pipx':
            subprocess.run(['pipx', 'install', 'argcomplete'], 
                          capture_output=True, text=True, check=True)
        elif install_method == 'pip_user':
            subprocess.run(['pip', 'install', '--user', 'argcomplete'], 
                          capture_output=True, text=True, check=True)
        elif install_method == 'uv':
            subprocess.run(['uv', 'pip', 'install', 'argcomplete'], 
                          capture_output=True, text=True, check=True)
        else:  # pip venv
            subprocess.run(['pip', 'install', 'argcomplete'], 
                          capture_output=True, text=True, check=True)
        
        print("✓ argcomplete installed successfully")
        
        # Setup autocompletion in shell
        shell_config = venv_info['shell_config']
        if shell_config and Path(shell_config).exists():
            # Check if already configured
            with open(shell_config, 'r', encoding='utf-8') as f:
                content = f.read()
            
            completion_line = 'eval "$(register-python-argcomplete renv)"'
            
            if completion_line not in content:
                print(f"Adding autocompletion to {shell_config}...")
                with open(shell_config, 'a', encoding='utf-8') as f:
                    f.write(f'\n# renv autocompletion\n{completion_line}\n')
                print("✓ Autocompletion added to shell configuration")
            else:
                print("✓ Autocompletion already configured in shell")
        else:
            print(f"⚠ Shell configuration file not found: {shell_config}")
            print("You may need to manually add the following to your shell config:")
            print('eval "$(register-python-argcomplete renv)"')
        
        # Try to enable global argcomplete if possible
        try:
            subprocess.run(['activate-global-python-argcomplete'], 
                         capture_output=True, text=True, check=True)
            print("✓ Global argcomplete activated")
        except subprocess.CalledProcessError:
            print("ℹ Global argcomplete activation failed (this is optional)")
        
        print("\n🎉 Setup complete!")
        if install_method in ['uv_tool', 'pipx', 'pip_user']:
            print("✓ argcomplete is now globally available")
        
        print("Restart your shell or run:")
        print(f"  source {shell_config}")
        print("\nThen try: renv <TAB> for autocompletion")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        
        # Provide helpful suggestions
        if install_method == 'uv_tool':
            print("\nTry installing uv first:")
            print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        elif install_method == 'pipx':
            print("\nTry installing pipx first:")
            print("  pip install pipx")
        
        return False
    except Exception as e:
        print(f"❌ Unexpected error during installation: {e}")
        return False


def uninstall_argcomplete():
    """Remove argcomplete setup for renv."""
    print("Removing argcomplete setup for renv...")
    
    venv_info = detect_virtual_env()
    global_managers = detect_global_package_manager()
    
    # Remove from shell configuration
    shell_config = venv_info['shell_config']
    if shell_config and Path(shell_config).exists():
        print(f"Removing autocompletion from {shell_config}...")
        
        with open(shell_config, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter out renv autocompletion lines
        filtered_lines = []
        skip_next = False
        
        for line in lines:
            if skip_next and 'register-python-argcomplete renv' in line:
                skip_next = False
                continue
            elif '# renv autocompletion' in line:
                skip_next = True
                continue
            else:
                filtered_lines.append(line)
        
        if len(filtered_lines) != len(lines):
            with open(shell_config, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            print("✓ Autocompletion removed from shell configuration")
        else:
            print("ℹ No autocompletion configuration found in shell")
    
    # Optionally uninstall argcomplete package (ask user)
    try:
        print("\nArgcomplete package removal options:")
        if global_managers:
            print("Available removal methods:")
            if 'uv_tool' in global_managers:
                print("  1. uv tool uninstall argcomplete")
            if 'pipx' in global_managers:
                print("  2. pipx uninstall argcomplete")
            if 'pip_user' in global_managers:
                print("  3. pip uninstall argcomplete (user install)")
            print("  4. Skip package removal")
        
        response = input("Choose removal method (1-4) or press Enter to skip: ").strip()
        
        if response == "1" and 'uv_tool' in global_managers:
            subprocess.run(['uv', 'tool', 'uninstall', 'argcomplete'], 
                         capture_output=True, text=True, check=True)
            print("✓ argcomplete uninstalled with uv tool")
        elif response == "2" and 'pipx' in global_managers:
            subprocess.run(['pipx', 'uninstall', 'argcomplete'], 
                         capture_output=True, text=True, check=True)
            print("✓ argcomplete uninstalled with pipx")
        elif response == "3" and 'pip_user' in global_managers:
            subprocess.run(['pip', 'uninstall', 'argcomplete', '-y'], 
                         capture_output=True, text=True, check=True)
            print("✓ argcomplete package uninstalled")
        elif response in ["4", ""]:
            print("ℹ Skipping package removal")
        else:
            print("ℹ Invalid selection, skipping package removal")
            
    except subprocess.CalledProcessError as e:
        print(f"ℹ Could not uninstall argcomplete package: {e}")
    except KeyboardInterrupt:
        print("\nSkipping package uninstall")
    except EOFError:
        print("Skipping package uninstall")
    
    print("\n✓ renv autocompletion setup removed")
    print("Restart your shell for changes to take effect")
    
    return True


# ...existing code...
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
  renv                              # Show version number
  renv --install                    # Install and setup autocompletion
  renv --uninstall                  # Remove autocompletion setup
  
The tool will:
1. Clone the repository as a bare repo to ~/renv/owner/repo (if not already cloned)
2. Create a worktree for the specified branch at ~/renv/owner/repo/worktree-{branch}
3. Run rockerc in that worktree to build and enter a container
        """,
    )

    repo_spec_arg = parser.add_argument(
        "repo_spec",
        nargs="?",  # Make it optional
        help="Repository specification in format 'owner/repo[@branch]'. If branch is omitted, 'main' is used. If no argument is provided, shows version.",
    )

    parser.add_argument(
        "--no-container",
        action="store_true",
        help="Set up the worktree but don't run rockerc (for debugging or manual container management)",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    parser.add_argument(
        "--install",
        action="store_true",
        help="Install and setup argcomplete for autocompletion (requires uv or pip virtual environment)",
    )

    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove argcomplete setup for renv",
    )

    # Add argcomplete support if available
    if ARGCOMPLETE_AVAILABLE:
        repo_spec_arg.completer = repo_completer
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Handle install command
    if args.install:
        success = install_argcomplete()
        sys.exit(0 if success else 1)

    # Handle uninstall command
    if args.uninstall:
        success = uninstall_argcomplete()
        sys.exit(0 if success else 1)

    # Handle version display
    if args.version or not args.repo_spec:
        version = get_version()
        print(f"renv version {version}")
        if args.version:
            sys.exit(0)
        if not args.repo_spec:
            sys.exit(0)

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
