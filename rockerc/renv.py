import sys
import subprocess
import pathlib
import logging
import argparse
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
    repo_url = f"https://github.com/{repo_spec.owner}/{repo_spec.repo}.git"

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
    else:
        logging.info(f"Worktree already exists: {worktree_dir}")

    return worktree_dir


def build_rocker_config(
    repo_spec: RepoSpec, force: bool = False, nocache: bool = False
) -> Dict[str, Any]:
    """Build rocker configuration with default extensions"""
    container_name = get_container_name(repo_spec)
    repo_dir = get_repo_dir(repo_spec)
    worktree_dir = get_worktree_dir(repo_spec)

    # Docker mount points
    docker_bare_repo_mount = f"/tmp/{repo_spec.repo}.git"
    docker_worktree_mount = f"/tmp/{repo_spec.repo}"
    docker_workdir = docker_worktree_mount

    if repo_spec.subfolder:
        docker_workdir = f"{docker_worktree_mount}/{repo_spec.subfolder}"

    # Git environment for worktree
    git_dir_in_container = docker_bare_repo_mount
    git_work_tree_in_container = docker_worktree_mount

    # Create config using spec from renv.md
    config = {
        "image": "ubuntu:22.04",
        "args": ["user", "pull", "git-clone", "git", "cwd", "nocleanup"],
        "name": container_name,
        "hostname": container_name,
        "oyr-run-arg": f"--workdir={docker_workdir} --env=GIT_DIR={git_dir_in_container} --env=GIT_WORK_TREE={git_work_tree_in_container}",
    }

    # Add volumes as separate entries since rockerc doesn't handle volume lists properly
    config["volume"] = f"{repo_dir}:{docker_bare_repo_mount} {worktree_dir}:{docker_worktree_mount}"

    # Note: force rebuild is handled by removing existing containers, not by rocker extensions
    # nocache is not implemented as rocker extension - it should be handled during container management

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
            # If it starts with "bash -c" or contains shell constructs, pass it to bash -c
            if cmd_str.startswith("bash -c ") or any(char in cmd_str for char in [';', '&&', '||', '|', '>', '<']):
                # Extract the actual command from "bash -c 'command'" format
                if cmd_str.startswith("bash -c "):
                    actual_cmd = cmd_str[8:].strip()
                    # Remove surrounding quotes if present
                    if (actual_cmd.startswith("'") and actual_cmd.endswith("'")) or \
                       (actual_cmd.startswith('"') and actual_cmd.endswith('"')):
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
        cmd_parts = ["docker", "exec", "-it", container_name, "/bin/bash"]
    
    logging.info(f"Attaching to container: {' '.join(cmd_parts)}")
    return subprocess.run(cmd_parts).returncode


def start_and_attach_container(container_name: str, command: Optional[List[str]] = None) -> int:
    """Start a stopped container and attach to it"""
    # Start the container
    start_result = subprocess.run(["docker", "start", container_name], capture_output=True, text=True)
    if start_result.returncode != 0:
        logging.error(f"Failed to start container {container_name}: {start_result.stderr}")
        return start_result.returncode
    
    logging.info(f"Started container {container_name}")
    
    # Now attach to it
    return attach_to_container(container_name, command)


def run_rocker_command(config: Dict[str, Any], command: Optional[List[str]] = None, detached: bool = False) -> int:
    """Execute rocker command by building command parts directly"""
    # Start with the base rocker command
    cmd_parts = ["rocker"]

    # Extract special values that need separate handling
    image = config.get("image", "")
    volumes = []
    if "volume" in config:
        volume_str = config["volume"]
        volumes = volume_str.split()

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

    # Add command if provided
    if command:
        cmd_parts.extend(command)

    # Log the full command for debugging
    cmd_str = " ".join(cmd_parts)
    logging.info(f"Running rocker: {cmd_str}")
    logging.info(f"Final command parts: {cmd_parts}")

    if detached:
        # Run in background and return immediately
        subprocess.Popen(cmd_parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 0
    else:
        return subprocess.run(cmd_parts).returncode


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

    # Implement reconnect logic as per spec:
    # 1. If container is running -> attach to it
    # 2. If container exists but not running -> start and attach  
    # 3. If container doesn't exist -> create persistent container
    
    if container_exists(container_name) and not force:
        if container_running(container_name):
            logging.info(f"Container {container_name} is running, attaching to it")
            return attach_to_container(container_name, command)
        else:
            logging.info(f"Container {container_name} exists but is stopped, starting it")
            return start_and_attach_container(container_name, command)
    else:
        logging.info(f"Creating new persistent container {container_name}")
        # Build rocker configuration
        config = build_rocker_config(repo_spec, force=force, nocache=nocache)
        
        if command:
            # For commands, create persistent container first, then run command
            create_result = run_rocker_command(config, ["tail", "-f", "/dev/null"], detached=True)
            if create_result != 0:
                return create_result
            # Wait for container to be running before attaching
            import time
            max_wait = 30  # Maximum wait time in seconds
            wait_time = 0
            while wait_time < max_wait:
                if container_running(container_name):
                    break
                time.sleep(1)
                wait_time += 1
            else:
                logging.error(f"Container {container_name} failed to start after {max_wait} seconds")
                return 1
            return attach_to_container(container_name, command)
        else:
            # For interactive sessions, create persistent container and attach
            create_result = run_rocker_command(config, ["tail", "-f", "/dev/null"], detached=True)
            if create_result != 0:
                return create_result
            # Wait for container to be running before attaching
            import time
            max_wait = 30  # Maximum wait time in seconds
            wait_time = 0
            while wait_time < max_wait:
                if container_running(container_name):
                    break
                time.sleep(1)
                wait_time += 1
            else:
                logging.error(f"Container {container_name} failed to start after {max_wait} seconds")
                return 1
            return attach_to_container(container_name, None)  # Attach interactively


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
        logging.info("Shell autocompletion installation not yet implemented")
        return 0

    if not parsed_args.repo_spec:
        logging.error("Repository specification required. Usage: renv owner/repo[@branch]")
        parser.print_help()
        return 1

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
