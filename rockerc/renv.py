"""
renv - Rocker Environment Manager

Architecture Overview:
This module implements a multi-repository development environment using git worktrees and rocker containers.

The architecture follows a layered approach for maximum code reuse:

1. Base Layer:
   - rockerc: Core container management, reads rockerc.yaml files and launches containers
   - rockervsc: Light wrapper on rockerc with same interface, adds VSCode integration

2. Environment Layer:
   - renv: Collects configuration arguments and passes them to rockerc
   - renvvsc: Functions the same as renv, but passes arguments to rockervsc instead of rockerc

This design ensures:
- Maximum code reuse between terminal and VSCode workflows
- Consistent interfaces across all tools
- Easy maintenance with changes in one place affecting both workflows
"""

import sys
import subprocess
import pathlib
import logging
import argparse
import time
import yaml
import shutil
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .rockerc import deduplicate_extensions


@dataclass
class RepoSpec:
    owner: str
    repo: str
    branch: str = "main"
    subfolder: Optional[str] = None

    @classmethod
    def parse(cls, spec: str) -> "RepoSpec":
        """Parse repo specification: owner/repo[@branch][#subfolder]"""
        # Split by # for subfolder
        parts = spec.split("#", 1)
        repo_branch = parts[0]
        subfolder = parts[1] if len(parts) > 1 else None

        # Split by @ for branch
        parts = repo_branch.split("@", 1)
        owner_repo = parts[0]
        branch = parts[1] if len(parts) > 1 else "main"

        # Split by / for owner/repo
        owner, repo = owner_repo.split("/", 1)

        return cls(owner=owner, repo=repo, branch=branch, subfolder=subfolder)

    def __str__(self) -> str:
        result = f"{self.owner}/{self.repo}@{self.branch}"
        if self.subfolder:
            result += f"#{self.subfolder}"
        return result


def get_renv_root() -> pathlib.Path:
    """Get the root directory for renv repositories"""
    return pathlib.Path.home() / "renv"


def get_available_users() -> List[str]:
    """Get list of available users from renv directory"""
    renv_root = get_renv_root()
    if not renv_root.exists():
        return []
    return [d.name for d in renv_root.iterdir() if d.is_dir()]


def get_available_repos(user: str) -> List[str]:
    """Get list of available repositories for a user"""
    user_dir = get_renv_root() / user
    if not user_dir.exists():
        return []
    return [d.name for d in user_dir.iterdir() if d.is_dir()]


def get_available_branches(repo_spec: RepoSpec) -> List[str]:
    """Get list of available branches for a repository"""
    repo_dir = get_repo_dir(repo_spec)
    if not repo_dir.exists():
        return []

    try:
        # For bare repositories, use 'branch' without '-r' to get local branches
        # that track remote branches
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "branch"],
            capture_output=True,
            text=True,
            check=True,
        )
        branches = []
        for line in result.stdout.strip().split("\n"):
            branch = line.strip().lstrip("* ").strip()
            if branch:
                branches.append(branch)
        return sorted(set(branches))
    except subprocess.CalledProcessError:
        return []


def branch_exists(repo_spec: RepoSpec, branch_name: str) -> bool:
    """Check if a branch exists in the repository"""
    available_branches = get_available_branches(repo_spec)
    return branch_name in available_branches


def get_default_branch(repo_spec: RepoSpec) -> str:
    """Get the default branch for a repository (main or master)"""
    available_branches = get_available_branches(repo_spec)
    if "main" in available_branches:
        return "main"
    if "master" in available_branches:
        return "master"
    if available_branches:
        return available_branches[0]  # Return first available branch
    return "main"  # Default fallback


def get_all_repo_branch_combinations() -> List[str]:
    """Get all available repo@branch combinations for fuzzy finder"""
    combinations = []
    for user in get_available_users():
        for repo in get_available_repos(user):
            repo_spec = RepoSpec(user, repo, "main")
            branches = get_available_branches(repo_spec)
            if branches:
                for branch in branches:
                    combinations.append(f"{user}/{repo}@{branch}")
            else:
                # If no branches found, still add with main
                combinations.append(f"{user}/{repo}@main")
    return sorted(combinations)


def fuzzy_select_repo() -> Optional[str]:
    """Interactive fuzzy finder for repo selection"""
    try:
        from iterfzf import iterfzf
    except ImportError:
        logging.error("iterfzf not available. Install with: pip install iterfzf")
        return None

    combinations = get_all_repo_branch_combinations()
    if not combinations:
        logging.info("No repositories found in ~/renv/. Clone some repos first!")
        return None

    print("Select repo@branch (type 'bl tes ma' for blooop/test_renv@main):")
    selected = iterfzf(combinations, multi=False)
    return selected


def install_shell_completion() -> int:
    """Install shell autocompletion for renv"""
    bash_completion = """# renv completion
_renv_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # Basic options
    opts="--help --install --force --nocache --no-container"
    
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
    
    # Complete repository specifications
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        local renv_root="$HOME/renv"
        local cache_root="$renv_root/.cache"

        # Check if we're completing branches (after @)
        if [[ "$cur" == *"@"* ]]; then
            # Extract owner/repo from before @
            local repo_part="${cur%%@*}"
            local branch_part="${cur##*@}"
            local owner="${repo_part%%/*}"
            local repo="${repo_part##*/}"

            local repo_dir="$cache_root/$owner/$repo"
            if [[ -d "$repo_dir" ]]; then
                local branches=$(git -C "$repo_dir" branch -r 2>/dev/null | sed 's/.*origin\\///' | grep -v HEAD | xargs)
                local completions=""
                for branch in $branches; do
                    completions="$completions $repo_part@$branch"
                done
                COMPREPLY=( $(compgen -W "${completions}" -- ${cur}) )
            fi
        else
            # Complete repository names without trailing space
            compopt -o nospace

            if [[ -d "$cache_root" ]]; then
                local repos=""
                local users=$(find "$cache_root" -maxdepth 1 -type d -exec basename {} \\; | grep -v "^\\.cache$")
                for user in $users; do
                    if [[ -d "$cache_root/$user" ]]; then
                        local user_repos=$(find "$cache_root/$user" -maxdepth 1 -type d -exec basename {} \\; | grep -v "^$user$")
                        for repo in $user_repos; do
                            repos="$repos $user/$repo"
                        done
                    fi
                done
                COMPREPLY=( $(compgen -W "${repos}" -- ${cur}) )
            fi
        fi
    fi
    
    return 0
}

complete -F _renv_completion renv
complete -F _renv_completion renvvsc
"""

    # Install to .bashrc
    bashrc_path = pathlib.Path.home() / ".bashrc"

    try:
        # Check if already installed
        if bashrc_path.exists():
            with open(bashrc_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "# renv completion" in content:
                    logging.info("renv completion already installed in ~/.bashrc")
                    return 0

        # Append completion to .bashrc
        with open(bashrc_path, "a", encoding="utf-8") as f:
            f.write("\n" + bash_completion + "\n")

        logging.info("Shell completion installed to ~/.bashrc")
        logging.info("Run 'source ~/.bashrc' or restart your terminal to enable completion")
        return 0

    except Exception as e:
        logging.error(f"Failed to install shell completion: {e}")
        return 1


def get_repo_dir(repo_spec: RepoSpec) -> pathlib.Path:
    """Get the directory path for a repository cache"""
    return get_renv_root() / ".cache" / repo_spec.owner / repo_spec.repo


def get_worktree_dir(repo_spec: RepoSpec) -> pathlib.Path:
    """Get the branch copy directory path for a repository and branch

    Returns: ~/renv/{owner}/{repo}-{branch}
    """
    safe_branch = repo_spec.branch.replace("/", "-")
    return get_renv_root() / repo_spec.owner / f"{repo_spec.repo}-{safe_branch}"


def load_renv_rockerc_config() -> dict:
    """Load global renv rockerc configuration from ~/renv/rockerc.yaml

    Creates the file from template if it doesn't exist.

    Returns:
        dict: Parsed configuration dictionary, or empty dict if parsing fails.
    """
    renv_dir = pathlib.Path.home() / "renv"
    config_path = renv_dir / "rockerc.yaml"

    # Create renv directory if it doesn't exist
    renv_dir.mkdir(exist_ok=True)

    # Copy template if config doesn't exist
    if not config_path.exists():
        template_path = pathlib.Path(__file__).parent / "renv_rockerc_template.yaml"
        if template_path.exists():
            shutil.copy2(template_path, config_path)
            logging.info(f"Created default renv config at {config_path}")
        else:
            logging.warning(f"Template file not found at {template_path}")
            return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logging.warning(f"Failed to parse YAML config at {config_path}: {e}")
        return {}
    except Exception as e:
        logging.warning(f"Error loading config at {config_path}: {e}")
        return {}


def load_repo_rockerc_config(worktree_dir: pathlib.Path) -> dict:
    """Load repository rockerc configuration from rockerc.yaml in the worktree

    Args:
        worktree_dir: Path to the repository worktree

    Returns:
        dict: Parsed configuration dictionary, or empty dict if file doesn't exist or parsing fails.
    """
    config_path = worktree_dir / "rockerc.yaml"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logging.warning(f"Failed to parse YAML config at {config_path}: {e}")
        return {}
    except Exception as e:
        logging.warning(f"Error loading config at {config_path}: {e}")
        return {}


def combine_rockerc_configs(renv_config: dict, repo_config: dict) -> dict:
    """Combine renv and repository rockerc configurations

    Args:
        renv_config: Configuration from ~/renv/rockerc.yaml
        repo_config: Configuration from repository's rockerc.yaml

    Returns:
        dict: Combined configuration with repo config taking precedence
    """
    # Start with renv config as base, then override with repo config
    combined = renv_config.copy()
    combined.update(repo_config)

    # Special handling for args - merge and deduplicate instead of overriding
    renv_args = renv_config.get("args", [])
    repo_args = repo_config.get("args", [])
    if renv_args or repo_args:
        combined["args"] = deduplicate_extensions(renv_args + repo_args)

    return combined


def get_container_name(repo_spec: RepoSpec) -> str:
    """Generate container name from repo specification"""
    safe_branch = repo_spec.branch.replace("/", "-")
    return f"{repo_spec.repo}-{safe_branch}"


def setup_cache_repo(repo_spec: RepoSpec) -> pathlib.Path:
    """Clone or update cache repository (full clone, not bare)"""
    repo_dir = get_repo_dir(repo_spec)
    repo_url = f"git@github.com:{repo_spec.owner}/{repo_spec.repo}.git"

    if not repo_dir.exists():
        logging.info(f"Cloning cache repository: {repo_url}")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo_url, str(repo_dir)], check=True)
    else:
        logging.info(f"Fetching updates for cache: {repo_url}")
        subprocess.run(["git", "-C", str(repo_dir), "fetch", "--all"], check=True)

    return repo_dir


def setup_branch_copy(repo_spec: RepoSpec) -> pathlib.Path:
    """Set up branch copy by copying from cache and checking out branch"""
    cache_dir = get_repo_dir(repo_spec)
    branch_dir = get_worktree_dir(repo_spec)

    # Ensure cache repo exists and is updated
    setup_cache_repo(repo_spec)

    if not branch_dir.exists():
        logging.info(f"Creating branch copy for: {repo_spec.branch}")

        # Copy entire cache directory to branch directory
        shutil.copytree(cache_dir, branch_dir)

        # Check if the branch exists in cache
        if not branch_exists(repo_spec, repo_spec.branch):
            default_branch = get_default_branch(repo_spec)
            logging.info(
                f"Branch '{repo_spec.branch}' doesn't exist, creating from '{default_branch}'"
            )
            # Create the new branch from the default branch
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(branch_dir),
                    "checkout",
                    "-b",
                    repo_spec.branch,
                    f"origin/{default_branch}",
                ],
                check=True,
            )
        else:
            # Checkout the existing branch
            subprocess.run(
                ["git", "-C", str(branch_dir), "checkout", repo_spec.branch],
                check=True,
            )
            # Pull latest changes
            subprocess.run(
                ["git", "-C", str(branch_dir), "pull"],
                check=False,  # Don't fail if already up to date
            )
    else:
        logging.info(f"Branch copy already exists: {branch_dir}")
        # Fetch and pull latest changes
        subprocess.run(
            ["git", "-C", str(branch_dir), "fetch", "--all"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(branch_dir), "pull"],
            check=False,  # Don't fail if already up to date
        )

    return branch_dir


def build_rocker_config(
    repo_spec: RepoSpec,
    force: bool = False,  # pylint: disable=unused-argument
    nocache: bool = False,  # pylint: disable=unused-argument
) -> Dict[str, Any]:
    """Build rocker configuration using rockerc's config loading"""
    from rockerc.rockerc import collect_arguments_with_meta

    container_name = get_container_name(repo_spec)
    branch_dir = get_worktree_dir(repo_spec)

    # Use rockerc's config loading from the branch directory
    config, meta = collect_arguments_with_meta(str(branch_dir))

    # Docker mount point for branch copy - use /workspaces/{container_name} to match rockerc convention
    docker_branch_mount = f"/workspaces/{container_name}"

    # Add cwd extension if not already present
    if "args" not in config:
        config["args"] = []
    if "cwd" not in config["args"]:
        config["args"].append("cwd")

    # Set renv-specific parameters
    config["name"] = container_name
    config["hostname"] = container_name

    # Add renv-specific volume - only mount the branch copy
    # Use :Z flag for SELinux support (same as rockerc)
    config["volume"] = [
        f"{branch_dir}:{docker_branch_mount}:Z",
    ]

    # Store the target directory for changing cwd before launching
    # The cwd extension will pick up the current working directory
    config["_renv_target_dir"] = (
        str(branch_dir / repo_spec.subfolder) if repo_spec.subfolder else str(branch_dir)
    )

    return config, meta


def container_exists(container_name: str) -> bool:
    """Check if container exists"""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}", "--filter", f"name={container_name}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return container_name in result.stdout.strip().split("\n")
    except subprocess.CalledProcessError:
        return False


def container_running(container_name: str) -> bool:
    """Check if container is running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", f"name={container_name}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return container_name in result.stdout.strip().split("\n")
    except subprocess.CalledProcessError:
        return False


def attach_to_container(container_name: str, command: Optional[List[str]] = None) -> int:
    """Attach to an existing running container"""
    if command:
        # Execute command in running container (non-interactive for commands)
        # Check if we have a single argument that looks like a shell command
        if len(command) == 1:
            cmd_str = command[0]
            # If it starts with "bash -c" or contains shell constructs or spaces, pass it to bash -c
            if (
                cmd_str.startswith("bash -c ")
                or any(char in cmd_str for char in [";", "&&", "||", "|", ">", "<"])
                or " " in cmd_str
            ):
                # Extract the actual command from "bash -c 'command'" format
                if cmd_str.startswith("bash -c "):
                    actual_cmd = cmd_str[8:].strip()
                    # Remove surrounding quotes if present
                    if (actual_cmd.startswith("'") and actual_cmd.endswith("'")) or (
                        actual_cmd.startswith('"') and actual_cmd.endswith('"')
                    ):
                        actual_cmd = actual_cmd[1:-1]
                    cmd_parts = ["docker", "exec", container_name, "/bin/bash", "-c", actual_cmd]
                else:
                    # For other shell constructs, wrap the whole thing
                    cmd_parts = ["docker", "exec", container_name, "/bin/bash", "-c", cmd_str]
            else:
                # Simple command, execute directly
                cmd_parts = ["docker", "exec", container_name] + command
        else:
            # Multiple arguments, execute directly
            cmd_parts = ["docker", "exec", container_name] + command
    else:
        # Attach to running container for interactive session
        # Check if we have a TTY available
        if sys.stdin.isatty() and sys.stdout.isatty():
            cmd_parts = ["docker", "exec", "-it", container_name, "/bin/bash"]
        else:
            # No TTY available, run non-interactively
            cmd_parts = ["docker", "exec", container_name, "/bin/bash"]

    logging.info(f"Attaching to container: {' '.join(cmd_parts)}")
    return subprocess.run(cmd_parts, check=False).returncode


def run_rocker_command(
    config: Dict[str, Any], command: Optional[List[str]] = None, detached: bool = False
) -> int:
    """Execute rocker command by building command parts directly"""
    # Start with the base rocker command
    cmd_parts = ["rocker"]

    # Extract special values that need separate handling
    image = config.get("image", "")
    volumes = []
    if "volume" in config:
        volume_config = config["volume"]
        if isinstance(volume_config, list):
            volumes = volume_config
        else:
            volumes = volume_config.split()

    oyr_run_arg = config.get("oyr-run-arg", "")

    # Add basic extensions from args
    if "args" in config:
        for arg in config["args"]:
            cmd_parts.append(f"--{arg}")

    # Add named parameters (but skip special ones we handle separately)
    for key, value in config.items():
        if key not in ["image", "args", "volume", "oyr-run-arg"]:
            cmd_parts.extend([f"--{key}", str(value)])

    # Add oyr-run-arg if present
    if oyr_run_arg:
        cmd_parts.extend(["--oyr-run-arg", oyr_run_arg])

    # Add volumes
    for volume in volumes:
        cmd_parts.extend(["--volume", volume])

    # Add -- separator if volumes are present (required by rocker)
    if volumes:
        cmd_parts.append("--")

    # Add image
    if image:
        cmd_parts.append(image)

    # Add command if provided, otherwise default to bash
    if command:
        # Pass through explicit bash -c commands unchanged
        if (
            len(command) >= 2
            and command[0] in {"bash", "/bin/bash"}
            and command[1] in {"-c", "-lc"}
        ):
            cmd_parts.extend(command)
        else:
            command_str: Optional[str] = None

            if len(command) == 1:
                command_str = command[0]
            else:
                # Detect shell metacharacters spread across multiple tokens (e.g. ['git', 'status;'])
                if any(
                    any(meta in arg for meta in [";", "&&", "||", "|", ">", "<"]) for arg in command
                ):
                    command_str = " ".join(command)

            if command_str is not None:

                def _quote_for_rocker(cmd: str) -> str:
                    if (cmd.startswith('"') and cmd.endswith('"')) or (
                        cmd.startswith("'") and cmd.endswith("'")
                    ):
                        return cmd
                    escaped = cmd.replace('"', r"\"")
                    return f'"{escaped}"'

                if command_str.startswith("bash -c "):
                    actual_cmd = command_str[8:].strip()
                    if (
                        actual_cmd.startswith("'")
                        and actual_cmd.endswith("'")
                        or actual_cmd.startswith('"')
                        and actual_cmd.endswith('"')
                    ):
                        actual_cmd = actual_cmd[1:-1]
                    cmd_parts.extend(["bash", "-c", _quote_for_rocker(actual_cmd)])
                else:
                    cmd_parts.extend(["bash", "-c", _quote_for_rocker(command_str)])
            else:
                # Simple command or multiple arguments without shell metacharacters
                cmd_parts.extend(command)
    else:
        cmd_parts.extend(["bash"])

    # Log the full command for debugging
    cmd_str = " ".join(cmd_parts)
    logging.info(f"Running rocker: {cmd_str}")

    # Always use worktree directory as working directory for renv
    cwd = None
    # Extract worktree directory from volume mounts
    for volume in volumes:
        if "/workspace/" in volume and not volume.endswith(".git"):
            host_path = volume.split(":")[0]
            if pathlib.Path(host_path).exists():
                cwd = host_path
                logging.info(f"Using worktree directory as cwd: {cwd}")
                break

    if detached:
        # Run in background and return immediately
        # pylint: disable=consider-using-with
        subprocess.Popen(cmd_parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cwd)
        # Give it a moment to start
        time.sleep(2)
        return 0
    return subprocess.run(cmd_parts, check=False, cwd=cwd).returncode


def _handle_container_corruption(
    repo_spec: RepoSpec, container_name: str, command: Optional[List[str]]
) -> int:
    """Handle container corruption by using rocker to launch a new container directly"""
    logging.info(
        "Container appears corrupted (possible breakout detection), launching new container with rocker"
    )
    # Remove the corrupted container
    subprocess.run(["docker", "stop", container_name], check=False)
    subprocess.run(["docker", "rm", "-f", container_name], check=False)

    # Use rocker directly to launch a new container instead of trying to reattach
    logging.info("Using rocker to launch new container directly")
    config, _ = build_rocker_config(repo_spec, force=True, nocache=False)
    return run_rocker_command(config, command, detached=False)


def _try_attach_with_fallback(
    repo_spec: RepoSpec, container_name: str, command: Optional[List[str]]
) -> int:
    """Try to attach to container, fallback to rocker if breakout detected"""
    # First test if container is still functional
    test_result = subprocess.run(
        ["docker", "exec", container_name, "pwd"],
        capture_output=True,
        text=True,
        check=False,
    )

    if test_result.returncode != 0 or "container breakout" in test_result.stderr.lower():
        return _handle_container_corruption(repo_spec, container_name, command)

    return attach_to_container(container_name, command)


def manage_container(  # pylint: disable=too-many-positional-arguments
    repo_spec: RepoSpec,
    command: Optional[List[str]] = None,
    force: bool = False,
    nocache: bool = False,
    no_container: bool = False,
    vsc: bool = False,
) -> int:
    """Manage container lifecycle and execution using core.py's unified flow"""
    if no_container:
        setup_branch_copy(repo_spec)
        logging.info(f"Branch copy set up at: {get_worktree_dir(repo_spec)}")
        return 0

    # Set up branch copy
    branch_dir = setup_branch_copy(repo_spec)
    container_name = get_container_name(repo_spec)

    # Build rocker configuration and get metadata
    config, meta = build_rocker_config(repo_spec, force=force, nocache=nocache)

    # Print extension table using rockerc's logic
    from rockerc.rockerc import render_extension_table

    render_extension_table(
        config.get("args", []),
        original_global_args=meta.get("original_global_args"),
        original_project_args=meta.get("original_project_args"),
        blacklist=meta.get("blacklist", []),
        removed_by_blacklist=meta.get("removed_by_blacklist", []),
        original_global_blacklist=meta.get("original_global_blacklist"),
        original_project_blacklist=meta.get("original_project_blacklist"),
    )

    # Extract and remove the target directory from config
    target_dir = config.pop("_renv_target_dir", str(branch_dir))

    # Change to the target directory so cwd extension picks it up
    import os

    original_cwd = os.getcwd()
    os.chdir(target_dir)

    try:
        from rockerc.core import (
            container_exists as core_container_exists,
            stop_and_remove_container,
            wait_for_container,
            launch_vscode,
            container_hex_name,
            interactive_shell,
        )

        exists = core_container_exists(container_name)
        running = container_running(container_name) if exists else False

        if force and exists:
            stop_and_remove_container(container_name)
            exists = False
            running = False

        # Handle VSCode mode using core.py flow components
        if vsc:
            # Launch detached container if it doesn't exist
            if not exists:
                ret = run_rocker_command(config, None, detached=True)
                if ret != 0:
                    return ret

            # Restore working directory before attach operations
            # (cwd change only needed for container launch, not for attach)
            os.chdir(original_cwd)

            # Wait for container to be ready
            if not wait_for_container(container_name):
                logging.error(f"Timed out waiting for container '{container_name}'")
                return 1

            # Launch VSCode
            container_hex = container_hex_name(container_name)
            launch_vscode(container_name, container_hex)

            # Attach interactive shell (matching rockervsc flow)
            return interactive_shell(container_name)

        # Handle interactive terminal mode
        if exists and running:
            # Container already running, attach to it
            if command:
                return attach_to_container(container_name, command)
            return _try_attach_with_fallback(repo_spec, container_name, None)

        # Need to create/start container
        return run_rocker_command(config, command, detached=False)
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


def run_renv(args: Optional[List[str]] = None) -> int:
    """Main entry point for renv"""
    if args is None:
        args = sys.argv[1:]

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Rocker Environment Manager - Seamless multi-repo development with git worktrees and rocker containers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "repo_spec", nargs="?", help="Repository specification: owner/repo[@branch][#subfolder]"
    )

    parser.add_argument("command", nargs="*", help="Command to execute in container")

    parser.add_argument(
        "--no-container", action="store_true", help="Set up worktree only, do not launch container"
    )

    parser.add_argument("--force", "-f", action="store_true", help="Force rebuild container")

    parser.add_argument("--nocache", action="store_true", help="Rebuild container with no cache")

    parser.add_argument("--install", action="store_true", help="Install shell autocompletion")

    parser.add_argument("--vsc", action="store_true", help="Launch with VS Code integration")

    parsed_args = parser.parse_args(args)

    if parsed_args.install:
        return install_shell_completion()

    # Interactive fuzzy finder if no repo_spec provided
    if not parsed_args.repo_spec:
        selected = fuzzy_select_repo()
        if not selected:
            logging.error("No repository selected. Usage: renv owner/repo[@branch]")
            parser.print_help()
            return 1
        parsed_args.repo_spec = selected

    try:
        repo_spec = RepoSpec.parse(parsed_args.repo_spec)
        logging.info(f"Working with: {repo_spec}")

        return manage_container(
            repo_spec=repo_spec,
            command=parsed_args.command if parsed_args.command else None,
            force=parsed_args.force,
            nocache=parsed_args.nocache,
            no_container=parsed_args.no_container,
            vsc=parsed_args.vsc,
        )

    except ValueError as e:
        logging.error(f"Invalid repository specification: {e}")
        return 1
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e}")
        return e.returncode
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1


def main():
    """Entry point for the renv command"""
    sys.exit(run_renv())


if __name__ == "__main__":
    main()
