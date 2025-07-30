import sys
import subprocess
import pathlib
import logging
import argparse
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


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
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "branch", "-r"],
            capture_output=True,
            text=True,
            check=True,
        )
        branches = []
        for line in result.stdout.strip().split("\n"):
            if line.strip() and not line.strip().startswith("origin/HEAD"):
                branch = line.strip().replace("origin/", "")
                if branch:
                    branches.append(branch)
        return sorted(set(branches))
    except subprocess.CalledProcessError:
        return []


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


def build_rocker_config(repo_spec: RepoSpec) -> Dict[str, Any]:
    """Build rocker configuration with default extensions"""
    container_name = get_container_name(repo_spec)
    repo_dir = get_repo_dir(repo_spec)
    worktree_dir = get_worktree_dir(repo_spec)

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

    # Create config matching renv.md spec - use rocker's default extensions
    config = {
        "image": "ubuntu:22.04",
        "args": ["user", "pull", "git", "git-clone", "nocleanup"],
        "name": container_name,
        "hostname": container_name,
        "volume": [
            f"{repo_dir}:{docker_bare_repo_mount}",
            f"{worktree_dir}:{docker_worktree_mount}",
            f"{worktree_git_dir}:{docker_worktree_git_mount}",
        ],
        "oyr-run-arg": f"--workdir={docker_workdir} --env=REPO_NAME={repo_spec.repo} --env=BRANCH_NAME={repo_spec.branch.replace('/', '-')}",
    }

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
        # Execute command in running container - handle shell commands properly
        if len(command) == 1 and (
            " " in command[0]
            or any(char in command[0] for char in [";", "&&", "||", "|", ">", "<"])
        ):
            # Complex shell command - need to parse it properly
            cmd_str = command[0]
            if cmd_str.startswith("bash -c "):
                # Extract the command part from "bash -c 'command'"
                actual_cmd = cmd_str[8:].strip()
                # Remove surrounding quotes if present
                if (actual_cmd.startswith("'") and actual_cmd.endswith("'")) or (
                    actual_cmd.startswith('"') and actual_cmd.endswith('"')
                ):
                    actual_cmd = actual_cmd[1:-1]
                cmd_parts = ["docker", "exec", container_name, "/bin/bash", "-c", actual_cmd]
            else:
                # Other complex command - wrap in bash -c
                cmd_parts = ["docker", "exec", container_name, "/bin/bash", "-c", cmd_str]
        else:
            # Simple command or multiple arguments
            cmd_parts = ["docker", "exec", container_name] + command
    else:
        # Interactive session - use TTY detection like rocker does
        if sys.stdin.isatty() and sys.stdout.isatty():
            cmd_parts = ["docker", "exec", "-it", container_name, "/bin/bash"]
        else:
            cmd_parts = ["docker", "exec", container_name, "/bin/bash"]

    logging.info(f"Attaching to container: {' '.join(cmd_parts)}")
    return subprocess.run(cmd_parts, check=False).returncode


def start_and_attach_container(container_name: str, command: Optional[List[str]] = None) -> int:
    """Start a stopped container and attach to it"""
    # Start the container
    start_result = subprocess.run(
        ["docker", "start", container_name], capture_output=True, text=True, check=False
    )
    if start_result.returncode != 0:
        logging.error(f"Failed to start container {container_name}: {start_result.stderr}")
        return start_result.returncode

    logging.info(f"Started container {container_name}")

    # Wait a moment for container to be fully started
    if not _wait_for_container_running(container_name, max_wait=10):
        logging.error(f"Container {container_name} failed to fully start")
        return 1

    # Now attach to it
    return attach_to_container(container_name, command)


def run_rocker_command(
    config: Dict[str, Any], command: Optional[List[str]] = None, detached: bool = False
) -> int:
    """Execute rocker command - simplified to match rocker CLI patterns"""
    cmd_parts = ["rocker"]

    # Add extensions from args
    if "args" in config:
        for arg in config["args"]:
            cmd_parts.append(f"--{arg}")

    # Add container name and hostname
    if "name" in config:
        cmd_parts.extend(["--name", config["name"]])
    if "hostname" in config:
        cmd_parts.extend(["--hostname", config["hostname"]])

    # Add volumes
    if "volume" in config:
        volumes = config["volume"] if isinstance(config["volume"], list) else [config["volume"]]
        for volume in volumes:
            cmd_parts.extend(["--volume", volume])

    # Add oyr-run-arg for custom docker arguments
    if "oyr-run-arg" in config:
        cmd_parts.extend(["--oyr-run-arg", config["oyr-run-arg"]])

    # Add -- separator before image when we have volumes (required by rocker)
    if "volume" in config:
        cmd_parts.append("--")

    # Add image
    cmd_parts.append(config.get("image", "ubuntu:22.04"))

    # Add command if provided
    if command:
        cmd_parts.extend(command)

    logging.info(f"Running rocker: {' '.join(cmd_parts)}")

    if detached:
        subprocess.Popen(cmd_parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)  # Let container start
        return 0
    return subprocess.run(cmd_parts, check=False).returncode


def manage_container(
    repo_spec: RepoSpec,
    command: Optional[List[str]] = None,
    force: bool = False,
    nocache: bool = False,
    no_container: bool = False,
) -> int:
    """Manage container lifecycle and execution - simplified logic matching rocker patterns"""
    if no_container:
        setup_worktree(repo_spec)
        logging.info(f"Worktree set up at: {get_worktree_dir(repo_spec)}")
        return 0

    setup_worktree(repo_spec)
    container_name = get_container_name(repo_spec)

    # Force rebuild: remove existing container
    if force and container_exists(container_name):
        logging.info(f"Force rebuild: removing existing container {container_name}")
        subprocess.run(["docker", "rm", "-f", container_name], check=True)

    # Nocache: remove cached images to force rebuild
    if nocache:
        logging.info("No-cache rebuild: removing cached rocker images")
        # Remove intermediate rocker images
        subprocess.run(["docker", "image", "prune", "-f"], capture_output=True, check=False)
        # Remove specific image tags that rocker might have cached
        image_name = f"rocker_{container_name}"
        subprocess.run(["docker", "rmi", "-f", image_name], capture_output=True, check=False)

    # Simple 3-state logic:
    # 1. Container running -> attach
    # 2. Container exists -> start and attach
    # 3. No container -> create and attach
    if container_exists(container_name) and not force:
        if container_running(container_name):
            logging.info(f"Attaching to running container {container_name}")
            return attach_to_container(container_name, command)

        logging.info(f"Starting stopped container {container_name}")
        return start_and_attach_container(container_name, command)

    # Create new persistent container using rocker - always persistent for renv workflow
    logging.info(f"Creating new persistent container {container_name}")
    config = build_rocker_config(repo_spec)

    # Always create persistent container first
    create_result = run_rocker_command(config, ["tail", "-f", "/dev/null"], detached=True)
    if create_result != 0:
        return create_result

    # Wait for container to start
    if not _wait_for_container_running(container_name, max_wait=30):
        logging.error(f"Container {container_name} failed to start")
        return 1

    # Fix git worktree reference
    _fix_git_worktree(container_name, repo_spec)

    # Now attach to container (interactive or with command)
    return attach_to_container(container_name, command)


def _wait_for_container_running(container_name: str, max_wait: int = 30) -> bool:
    """Wait for container to be running, return True on success, False on timeout"""
    wait_time = 0
    while wait_time < max_wait:
        if container_running(container_name):
            return True
        time.sleep(1)
        wait_time += 1

    return False


def _fix_git_worktree(container_name: str, repo_spec: RepoSpec) -> None:
    """Fix git worktree reference inside container"""
    safe_branch = repo_spec.branch.replace("/", "-")
    fix_git_cmd = [
        "/bin/bash",
        "-c",
        f"echo 'gitdir: /workspace/{repo_spec.repo}.git/worktrees/worktree-{safe_branch}' > /workspace/{repo_spec.repo}/.git",
    ]
    subprocess.run(
        ["docker", "exec", container_name] + fix_git_cmd,
        capture_output=True,
        check=False,
    )


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
