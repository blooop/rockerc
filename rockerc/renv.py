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
    elif "master" in available_branches:
        return "master"
    elif available_branches:
        return available_branches[0]  # Return first available branch
    else:
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
        if [[ -d "$renv_root" ]]; then
            local users=$(find "$renv_root" -maxdepth 1 -type d -exec basename {} \\; | grep -v "^renv$")
            local repos=""
            for user in $users; do
                if [[ -d "$renv_root/$user" ]]; then
                    local user_repos=$(find "$renv_root/$user" -maxdepth 1 -type d -exec basename {} \\; | grep -v "^$user$")
                    for repo in $user_repos; do
                        repos="$repos $user/$repo"
                        # Add branches if @ is present
                        if [[ "$cur" == *"@"* ]]; then
                            local repo_dir="$renv_root/$user/$repo"
                            if [[ -d "$repo_dir" ]]; then
                                local branches=$(git -C "$repo_dir" branch -r 2>/dev/null | sed 's/origin\\///' | grep -v HEAD | xargs)
                                for branch in $branches; do
                                    repos="$repos $user/$repo@$branch"
                                done
                            fi
                        fi
                    done
                fi
            done
            COMPREPLY=( $(compgen -W "${repos}" -- ${cur}) )
        fi
    fi
    
    return 0
}

complete -F _renv_completion renv
complete -F _renv_completion renvsc
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
    """Get the directory path for a repository"""
    return get_renv_root() / repo_spec.owner / repo_spec.repo


def get_worktree_dir(repo_spec: RepoSpec) -> pathlib.Path:
    """Get the worktree directory path for a repository and branch"""
    safe_branch = repo_spec.branch.replace("/", "-")
    return get_repo_dir(repo_spec) / f"worktree-{safe_branch}"


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


def setup_bare_repo(repo_spec: RepoSpec) -> pathlib.Path:
    """Clone or update bare repository"""
    repo_dir = get_repo_dir(repo_spec)
    repo_url = f"git@github.com:{repo_spec.owner}/{repo_spec.repo}.git"

    if not repo_dir.exists():
        logging.info(f"Cloning bare repository: {repo_url}")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--bare", repo_url, str(repo_dir)], check=True)
    else:
        logging.info(f"Fetching updates for: {repo_url}")
        subprocess.run(["git", "-C", str(repo_dir), "fetch", "--all"], check=True)

    return repo_dir


def setup_worktree(repo_spec: RepoSpec) -> pathlib.Path:
    """Set up git worktree for the specified branch"""
    repo_dir = get_repo_dir(repo_spec)
    worktree_dir = get_worktree_dir(repo_spec)

    # Ensure bare repo exists
    setup_bare_repo(repo_spec)

    if not worktree_dir.exists():
        # Check if the branch exists
        if not branch_exists(repo_spec, repo_spec.branch):
            default_branch = get_default_branch(repo_spec)
            logging.info(f"Branch '{repo_spec.branch}' doesn't exist, creating from '{default_branch}'")

            # Create the new branch from the default branch
            subprocess.run(
                ["git", "-C", str(repo_dir), "branch", repo_spec.branch, default_branch],
                check=True,
            )

        logging.info(f"Creating worktree for branch: {repo_spec.branch}")
        subprocess.run(
            ["git", "-C", str(repo_dir), "worktree", "add", str(worktree_dir), repo_spec.branch],
            check=True,
        )
        # Ensure worktree is fully populated before returning
        git_file = worktree_dir / ".git"
        if not git_file.exists():
            time.sleep(0.5)  # Wait for filesystem to sync
        # Additional check to ensure directory is fully ready
        time.sleep(0.1)
    else:
        logging.info(f"Worktree already exists: {worktree_dir}")

    return worktree_dir


def build_rocker_config(
    repo_spec: RepoSpec,
    force: bool = False,  # pylint: disable=unused-argument
    nocache: bool = False,  # pylint: disable=unused-argument
) -> Dict[str, Any]:
    """Build rocker configuration combining renv and repository configurations"""
    container_name = get_container_name(repo_spec)
    repo_dir = get_repo_dir(repo_spec)
    worktree_dir = get_worktree_dir(repo_spec)

    # Load and combine rockerc configurations
    renv_config = load_renv_rockerc_config()
    repo_config = load_repo_rockerc_config(worktree_dir)
    combined_config = combine_rockerc_configs(renv_config, repo_config)

    logging.info(f"Loaded renv config: {renv_config}")
    logging.info(f"Loaded repo config: {repo_config}")
    logging.info(f"Combined config: {combined_config}")

    # Docker mount points
    docker_bare_repo_mount = f"/workspace/{repo_spec.repo}.git"
    docker_worktree_mount = f"/workspace/{repo_spec.repo}"
    docker_workdir = docker_worktree_mount

    if repo_spec.subfolder:
        docker_workdir = f"{docker_worktree_mount}/{repo_spec.subfolder}"

    # For git worktrees, we need to mount the worktree git directory as well
    worktree_git_dir = repo_dir / "worktrees" / f"worktree-{repo_spec.branch.replace('/', '-')}"
    docker_worktree_git_mount = (
        f"/workspace/{repo_spec.repo}.git/worktrees/worktree-{repo_spec.branch.replace('/', '-')}"
    )

    # Set up git configuration file on host
    git_config_content = f"gitdir: /workspace/{repo_spec.repo}.git/worktrees/worktree-{repo_spec.branch.replace('/', '-')}"
    git_config_file = worktree_dir / ".git"

    # Ensure the git config file exists and has the right content
    with open(git_config_file, "w", encoding="utf-8") as f:
        f.write(git_config_content)

    # Start with base renv configuration
    config = {
        "image": combined_config.get("image", "ubuntu:22.04"),
        "args": combined_config.get("args", [
            "user",
            "pull",
            "git-clone",
            "git",
            "persist-image",
        ]),
        "name": container_name,
        "hostname": container_name,
        "volume": [
            f"{repo_dir}:{docker_bare_repo_mount}",
            f"{worktree_dir}:{docker_worktree_mount}",
            f"{worktree_git_dir}:{docker_worktree_git_mount}",
        ],
        "oyr-run-arg": f"--workdir={docker_workdir} --env=REPO_NAME={repo_spec.repo} --env=BRANCH_NAME={repo_spec.branch.replace('/', '-')}",
    }

    # Add any additional configuration parameters from the combined config
    for key, value in combined_config.items():
        if key not in ["image", "args"]:
            config[key] = value

    return config


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


def _setup_git_in_container(container_name: str, repo_spec: RepoSpec) -> bool:
    """Set up git configuration in running container. Returns True on success."""
    fix_git_cmd = [
        "docker",
        "exec",
        container_name,
        "bash",
        "-c",
        f"echo 'gitdir: /workspace/{repo_spec.repo}.git/worktrees/worktree-{repo_spec.branch.replace('/', '-')}' > /workspace/{repo_spec.repo}/.git",
    ]
    result = subprocess.run(fix_git_cmd, capture_output=True, text=True, check=False)
    return result.returncode == 0


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
        # Check if command contains shell metacharacters and needs bash -c wrapping
        if len(command) == 1 and any(
            char in command[0] for char in [";", "&&", "||", "|", ">", "<"]
        ):
            # Check if it's already wrapped in bash -c
            if command[0].startswith("bash -c "):
                # Already wrapped, use as-is
                cmd_parts.extend(command)
            else:
                # Compound command, wrap in bash -c
                cmd_parts.extend(["bash", "-c", command[0]])
        else:
            # Simple command or multiple arguments
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
    config = build_rocker_config(repo_spec, force=True, nocache=False)
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

    # Container seems functional, try to fix git configuration if needed
    fix_git_cmd = [
        "/bin/bash",
        "-c",
        f"echo 'gitdir: /workspace/{repo_spec.repo}.git/worktrees/worktree-{repo_spec.branch.replace('/', '-')}' > /workspace/{repo_spec.repo}/.git",
    ]
    fix_result = subprocess.run(
        ["docker", "exec", "--user", "root", container_name] + fix_git_cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if fix_result.returncode != 0:
        logging.warning(f"Failed to fix git file, container may be corrupted: {fix_result.stderr}")
        return _handle_container_corruption(repo_spec, container_name, command)

    return attach_to_container(container_name, command)


def manage_container(
    repo_spec: RepoSpec,
    command: Optional[List[str]] = None,
    force: bool = False,
    nocache: bool = False,
    no_container: bool = False,
) -> int:
    """Manage container lifecycle and execution"""
    if no_container:
        setup_worktree(repo_spec)
        logging.info(f"Worktree set up at: {get_worktree_dir(repo_spec)}")
        return 0

    # Set up worktree
    setup_worktree(repo_spec)

    container_name = get_container_name(repo_spec)

    # Handle force rebuild by removing existing container
    if force and container_exists(container_name):
        logging.info(f"Force rebuild: removing existing container {container_name}")
        subprocess.run(["docker", "rm", "-f", container_name], check=True)

    # Simplified approach: always use rocker to launch containers
    # This avoids the complex reattachment logic that conflicts with rocker's security model
    if force or not container_exists(container_name) or not container_running(container_name):
        if container_exists(container_name) and not force:
            # Remove stopped container and recreate with rocker
            logging.info(f"Removing stopped container {container_name} to recreate with rocker")
            subprocess.run(["docker", "rm", "-f", container_name], check=False)

        logging.info(f"Using rocker to launch container {container_name}")
        config = build_rocker_config(repo_spec, force=force, nocache=nocache)
        return run_rocker_command(config, command, detached=False)

    # Container is running, try to attach but handle breakout detection
    logging.info(f"Container {container_name} is running, attempting to attach")
    setup_worktree(repo_spec)
    return _try_attach_with_fallback(repo_spec, container_name, command)


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
