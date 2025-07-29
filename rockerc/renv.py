#!/usr/bin/env python3
"""
renv - Repository Environment Manager

A tool that makes it seamless to work in a va                return (2, owner_repo, branch)
            return (0, combo, "")ty of repos at the same time
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
from iterfzf import iterfzf
import yaml


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
        result = subprocess.run(
            ["git", "--git-dir", str(repo_dir), "branch", "-a"],
            capture_output=True,
            text=True,
            check=True,
        )
        branches = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            # Remove git status prefixes: '*' (current), '+' (worktree)
            if line.startswith("*"):
                line = line[1:].strip()
            elif line.startswith("+"):
                line = line[1:].strip()

            # Skip if line becomes empty after prefix removal
            if not line:
                continue

            # Remove 'remotes/origin/' prefix and clean up branch names
            if line.startswith("remotes/origin/"):
                branch = line.replace("remotes/origin/", "")
                if branch != "HEAD":  # Skip HEAD pointer
                    branches.append(branch)
            else:
                branches.append(line)
        # Remove duplicates and sort
        return sorted(set(branches))
    except Exception:
        return []


def get_all_repo_branch_combinations() -> List[str]:
    """Get all possible repo@branch combinations for fuzzy search."""
    combinations = []

    # Get all existing repos
    owner_repos = list_owners_and_repos()

    for owner_repo in owner_repos:
        # Add the repo without branch first (defaults to main)
        combinations.append(owner_repo)

        # Add all branches for each repo
        if "/" in owner_repo:
            try:
                owner, repo = owner_repo.split("/", 1)
                branches = list_branches(owner, repo)

                # Sort branches to put main/master first, then alphabetically
                def branch_sort_key(branch):
                    if branch == "main":
                        return (0, branch)
                    if branch == "master":
                        return (1, branch)
                    return (2, branch)

                sorted_branches = sorted(branches, key=branch_sort_key)

                for branch in sorted_branches:
                    combinations.append(f"{owner_repo}@{branch}")
            except Exception:
                # If there's an error getting branches, just skip this repo
                continue

    # Sort combinations: repos without @ first, then with @
    def combination_sort_key(combo):
        if "@" in combo:
            owner_repo, branch = combo.split("@", 1)
            if branch == "main":
                return (1, owner_repo, branch)
            if branch == "master":
                return (2, owner_repo, branch)
            return (3, owner_repo, branch)
        return (0, combo, "")

    return sorted(combinations, key=combination_sort_key)


def colorize_repo_branch_combo(combo: str) -> str:
    """
    Colorize owner/repo@branch combos for fzf display using custom palette: #F97300, #B13BFF, #00C4C4.
    """
    # 24-bit ANSI escape codes for true color
    COLOR_OWNER = "\033[38;2;249;115;0m"  # #F97300 (orange)
    COLOR_REPO = "\033[38;2;177;59;255m"  # #B13BFF (purple)
    COLOR_BRANCH = "\033[38;2;0;196;196m"  # #00C4C4 (cyan)
    COLOR_RESET = "\033[0m"
    if "@" in combo:
        owner_repo, branch = combo.split("@", 1)
        if "/" in owner_repo:
            owner, repo = owner_repo.split("/", 1)
            return f"{COLOR_OWNER}{owner}{COLOR_RESET}/{COLOR_REPO}{repo}{COLOR_RESET}@{COLOR_BRANCH}{branch}{COLOR_RESET}"
        return f"{COLOR_REPO}{owner_repo}{COLOR_RESET}@{COLOR_BRANCH}{branch}{COLOR_RESET}"
    if "/" in combo:
        owner, repo = combo.split("/", 1)
        return f"{COLOR_OWNER}{owner}{COLOR_RESET}/{COLOR_REPO}{repo}{COLOR_RESET}"
    return combo


def fuzzy_select_repo_spec() -> Optional[str]:
    """Use fuzzy finder to select a repository specification with colored suggestions."""
    options = get_all_repo_branch_combinations()
    if not options:
        print("No repositories found. Please clone some repositories first.")
        print("Example: renv blooop/bencher@main")
        return None
    # Colorize options for fzf display
    colored_options = [colorize_repo_branch_combo(opt) for opt in options]
    try:
        # Use iterfzf for fuzzy selection with ANSI color support
        selected = iterfzf(
            colored_options,
            prompt="Select repo@branch (type 'bl ben ma' for blooop/bencher@main): ",
            multi=False,
            print_query=False,
            query="",
            ansi=True,
        )
        if selected is None:
            return None
        # Remove ANSI codes from selected value to get the actual repo spec
        import re

        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        clean_selected = ansi_escape.sub("", selected)
        return clean_selected
    except KeyboardInterrupt:
        return None
    except Exception as e:
        print(f"Error during fuzzy selection: {e}")
        # Fallback to a simple input prompt
        print("Falling back to simple input...")
        try:
            user_input = input("Enter repo@branch (e.g., blooop/bencher@main): ").strip()
            return user_input if user_input else None
        except (KeyboardInterrupt, EOFError):
            return None


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


def ensure_defaults_yaml():
    """
    Ensure the template rockerc.defaults.template.yaml is copied to rockerc.defaults.yaml if missing.
    """
    import shutil

    base_dir = get_renv_base_dir()
    yaml_path = base_dir / "rockerc.yaml"
    template_path = Path(__file__).parent.parent / "rockerc.defaults.template.yaml"
    if not yaml_path.exists():
        try:
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            if template_path.exists() and template_path.stat().st_size > 0:
                shutil.copy(template_path, yaml_path)
                logging.info(f"Copied template defaults to {yaml_path}")
            else:
                logging.warning(
                    f"Template file {template_path} does not exist or is empty. Skipping copy."
                )
        except Exception as e:
            logging.warning(f"Could not copy template defaults: {e}")
    ensure_github_known_host()


def ensure_github_known_host():
    """
    Ensure that GitHub's SSH fingerprint is present in ~/.ssh/known_hosts to avoid SSH prompts.
    """
    ssh_dir = Path.home() / ".ssh"
    known_hosts = ssh_dir / "known_hosts"
    github_host = "github.com"
    # Create .ssh directory if missing
    ssh_dir.mkdir(parents=True, exist_ok=True)
    # Check if github.com is already in known_hosts
    if known_hosts.exists():
        try:
            with known_hosts.open("r") as f:
                if any(github_host in line for line in f):
                    return  # Already present
        except Exception:
            pass
    try:
        result = subprocess.run(
            ["ssh-keyscan", github_host], capture_output=True, text=True, check=True
        )
        with known_hosts.open("a") as f:
            f.write(result.stdout)
        logging.info(f"Added {github_host} fingerprint to {known_hosts}")
    except Exception as e:
        logging.warning(f"Could not add {github_host} to known_hosts: {e}")


def parse_repo_spec(repo_spec: str) -> Tuple[str, str, str, str]:
    """
    Parse a repository specification like 'owner/repo@branch#subfolder' or 'owner/repo'.

    Args:
        repo_spec: Repository specification string

    Returns:
        Tuple of (owner, repo, branch, subfolder)

    Raises:
        ValueError: If the repo specification is invalid
    """
    # Check for subfolder specification
    if "#" in repo_spec:
        repo_part, subfolder = repo_spec.split("#", 1)
    else:
        repo_part = repo_spec
        subfolder = ""

    if "@" in repo_part:
        repo_part, branch = repo_part.split("@", 1)
    else:
        branch = "main"

    if "/" not in repo_part:
        raise ValueError(
            f"Invalid repo specification: {repo_spec}. Expected format: owner/repo[@branch][#subfolder]"
        )

    owner, repo = repo_part.split("/", 1)

    if not owner or not repo:
        raise ValueError(f"Invalid repo specification: {repo_spec}. Owner and repo cannot be empty")

    return owner, repo, branch, subfolder


def get_renv_base_dir() -> Path:
    """Get the base directory for renv repositories."""
    return Path(os.getcwd()) / "renv"


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
    # Prefer SSH for cloning to avoid username/password prompts
    repo_url = f"git@github.com:{owner}/{repo}.git"

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
            logging.info(
                f"Branch {branch} doesn't exist locally or on remote. Creating new branch from default branch."
            )

            # Determine the default branch (main or master)
            default_branch = get_default_branch(repo_dir)
            logging.info(f"Using {default_branch} as base for new branch {branch}")

            try:
                # First try to create from remote reference
                subprocess.run(
                    [
                        "git",
                        "worktree",
                        "add",
                        "-b",
                        branch,
                        str(worktree_dir),
                        f"origin/{default_branch}",
                    ],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logging.info(
                    f"Successfully created new branch {branch} from origin/{default_branch}"
                )

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
                    logging.error(
                        f"Failed to create new branch {branch} from {default_branch}: {e.stderr}"
                    )
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


def yaml_dict_to_args(d: dict) -> str:
    """Given a dictionary of arguments turn it into an argument string to pass to rocker

    Args:
        d (dict): rocker arguments dictionary

    Returns:
        str: rocker arguments string
    """
    cmd_str = ""
    image = d.pop("image", None)  # special value
    # Remove disable_args if present (should not be passed to rocker)
    d.pop("disable_args", None)

    if "args" in d:
        args = d.pop("args")
        for a in args:
            cmd_str += f"--{a} "

    # the rest of the named arguments
    for k, v in d.items():
        cmd_str += f"--{k} {v} "

    # last argument is the image name
    if image is not None:
        cmd_str += image

    return cmd_str


def collect_arguments(path: str = ".") -> dict:
    """Search for rockerc.yaml files and return a merged dictionary

    Args:
        path (str, optional): path to reach for files. Defaults to ".".

    Returns:
        dict: A dictionary of merged rockerc arguments
    """
    search_path = Path(path)

    # Start with defaults
    merged_dict = load_defaults_config(path)

    # Load and merge local rockerc.yaml files
    local_configs_found = False
    for p in search_path.glob("rockerc.yaml"):
        print(f"loading {p}")
        local_configs_found = True

        with open(p.as_posix(), "r", encoding="utf-8") as f:
            local_config = yaml.safe_load(f) or {}

            # Handle disable_args - remove these from the current args
            if "disable_args" in local_config:
                disabled_args = local_config["disable_args"]
                if isinstance(disabled_args, list):
                    for arg in disabled_args:
                        if arg in merged_dict["args"]:
                            merged_dict["args"].remove(arg)
                    print(f"Local disabled extensions: {', '.join(disabled_args)}")

                # Remove disable_args so it doesn't get passed to rocker
                local_config.pop("disable_args")

            # Handle regular args - add these to existing args (avoiding duplicates)
            if "args" in local_config:
                local_args = local_config["args"]
                if isinstance(local_args, list):
                    for arg in local_args:
                        if arg not in merged_dict["args"]:
                            merged_dict["args"].append(arg)
                    print(f"Added extensions: {', '.join(local_args)}")

                # Remove args from local_config since we handled it specially
                local_config.pop("args")

            # Merge other configuration options (image, dockerfile, etc.)
            for key, value in local_config.items():
                merged_dict[key] = value

    # If no local config found, show what defaults are being used
    if not local_configs_found:
        if merged_dict["args"]:
            print(f"Using default extensions: {', '.join(merged_dict['args'])}")
        print("No local rockerc.yaml found - using defaults. Create rockerc.yaml to customize.")

    return merged_dict


def container_exists(container_name: str) -> bool:
    """Check if a Docker container with the given name exists.

    Args:
        container_name: Name of the container to check

    Returns:
        bool: True if container exists, False otherwise
    """
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"name=^/{container_name}$",
                "--format",
                "{{.Names}}",
            ],
            cwd="/tmp",
            capture_output=True,
            text=True,
            check=True,
        )
        return container_name in result.stdout.strip().split("\n")
    except subprocess.CalledProcessError:
        return False


def container_is_running(container_name: str) -> bool:
    """Check if a Docker container is currently running.

    Args:
        container_name: Name of the container to check

    Returns:
        bool: True if container is running, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name=^/{container_name}$", "--format", "{{.Names}}"],
            cwd="/tmp",
            capture_output=True,
            text=True,
            check=True,
        )
        return container_name in result.stdout.strip().split("\n")
    except subprocess.CalledProcessError:
        return False


def attach_to_container(container_name: str, workdir: str = "/workspaces") -> None:
    """Attach to an existing Docker container.

    Args:
        container_name: Name of the container to attach to
        workdir: Working directory to start in
    """
    try:
        if not container_is_running(container_name):
            logging.info(f"Container '{container_name}' exists but is not running. Starting it...")
            subprocess.run(["docker", "start", container_name], cwd="/tmp", check=True)

        logging.info(f"Attaching to existing container '{container_name}'...")
        subprocess.run(
            ["docker", "exec", "-it", "-w", workdir, container_name, "/bin/bash"],
            cwd="/tmp",
            check=True,
        )

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to attach to container '{container_name}': {e}")
        # If we can't attach, suggest removing the conflicting container
        logging.error("You may need to remove the existing container:")
        logging.error(f"  docker rm {container_name}")
        logging.error("Or remove it forcefully if it's running:")
        logging.error(f"  docker rm -f {container_name}")
        raise


def run_rockerc_in_worktree(
    worktree_dir: Path,
    _owner: str,
    repo: str,
    branch: str,
    *,
    subfolder: str = "",
    command: list[str] | None = None,
    force: bool = False,
    nocache: bool = False,
) -> None:
    """
    Run rocker directly in the specified worktree directory without using rockerc.

    Args:
        worktree_dir: Path to the worktree directory
        _owner: Repository owner (underscore prefix to avoid confusion)
        repo: Repository name
        branch: Branch name
        subfolder: Optional subfolder within the repository
        command: Optional command to run inside the container
        force: If True, force rebuild the container even if it already exists
        nocache: If True, rebuild the container with no cache
    """
    original_cwd = os.getcwd()

    try:
        # Check for .git or worktree metadata
        if not ((worktree_dir / ".git").exists() or (worktree_dir / "HEAD").exists()):
            raise RuntimeError(
                f"The directory {worktree_dir} is not a valid git repository or worktree. Aborting container launch."
            )

        # Determine target directory and docker workdir
        if subfolder:
            target_dir = worktree_dir / subfolder
            if not target_dir.exists():
                raise ValueError(f"Subfolder '{subfolder}' does not exist in {worktree_dir}")
            docker_workdir = f"/workspaces/{subfolder}"
            logging.info(
                f"Will mount {worktree_dir} to /workspaces and start in subfolder: /workspaces/{subfolder}"
            )
        else:
            target_dir = worktree_dir
            docker_workdir = "/workspaces"
            logging.info(f"Will mount {worktree_dir} to /workspaces and start in /workspaces")

        # Generate container name from repo@branch format
        safe_branch = branch.replace("/", "-")
        container_name = f"{repo}-{safe_branch}"
        if subfolder:
            safe_subfolder = subfolder.replace("/", "-")
            container_name = f"{repo}-{safe_branch}-{safe_subfolder}"

        # Get repo and worktree directories for volume mounts
        bare_repo_dir = get_repo_dir(_owner, repo)
        worktree_name = f"worktree-{safe_branch}"
        git_dir_in_container = f"/repo.git/worktrees/{worktree_name}"
        git_work_tree_in_container = "/workspaces"

        # Change to target directory to read config
        os.chdir(target_dir)

        # Collect rockerc configuration
        merged_dict = collect_arguments(str(target_dir))

        # If no config found, use hardcoded defaults
        if not merged_dict or (not merged_dict.get("args") and not merged_dict.get("image")):
            merged_dict = {
                "image": "ubuntu:24.04",
                "args": ["user", "pull", "deps", "git"],
                "disable_args": ["nvidia"],
            }
            print("No local rockerc.yaml found - using hardcoded defaults.")

        if "args" not in merged_dict:
            logging.error(
                "No 'args' key found in rockerc.yaml or defaults. Please add an 'args' list with rocker arguments. See 'rocker -h' for help."
            )
            raise ValueError("Missing 'args' configuration")

        # Add required arguments for renv
        docker_run_args = f"--workdir={docker_workdir} --env=GIT_DIR={git_dir_in_container} --env=GIT_WORK_TREE={git_work_tree_in_container}"
        rocker_args = [
            "rocker",
            "--name",
            container_name,
            "--hostname",
            container_name,
            "--volume",
            f"{bare_repo_dir}:/repo.git",
            "--volume",
            f"{worktree_dir}:/workspaces",
            "--oyr-run-arg",
            docker_run_args,
        ]

        # Add extensions from config
        for arg in merged_dict["args"]:
            rocker_args.append(f"--{arg}")

        # Add other config options (except args and image)
        for key, value in merged_dict.items():
            if key not in ["args", "image", "disable_args"]:
                rocker_args.extend([f"--{key}", str(value)])

        # Add image as the final argument
        rocker_args.append(merged_dict.get("image", "ubuntu:24.04"))

        # Add any extra command arguments
        if command:
            filtered_command = [c for c in command if c != merged_dict.get("image")]
            rocker_args.extend(filtered_command)

        def remove_container(name):
            """Remove a container (stop first if running)."""
            if container_is_running(name):
                logging.info(f"Stopping running container '{name}'...")
                subprocess.run(["docker", "stop", name], check=True)
            logging.info(f"Removing container '{name}'...")
            subprocess.run(["docker", "rm", name], check=True)

        # Handle force rebuild
        if (force or nocache) and container_exists(container_name):
            if force:
                logging.info(
                    f"Force flag specified. Removing existing container '{container_name}' to rebuild..."
                )
            if nocache:
                logging.info(
                    f"No-cache flag specified. Removing existing container '{container_name}' to rebuild with no cache..."
                )
            remove_container(container_name)

        # Check if container exists and attach if not forcing rebuild
        if container_exists(container_name) and not (force or nocache):
            logging.info(
                f"Container '{container_name}' already exists. Attaching to it instead of creating a new one."
            )
            attach_to_container(container_name, docker_workdir)
            return

        # Run rocker to create new container
        if force:
            logging.info(f"Building new container '{container_name}' (force rebuild requested)...")
        elif nocache:
            logging.info(
                f"Building new container '{container_name}' (no-cache rebuild requested)..."
            )
        else:
            logging.info(f"Container '{container_name}' does not exist. Building new container...")

        logging.info(f"running cmd: rocker {' '.join(rocker_args[1:])}")

        try:
            subprocess.run(rocker_args, cwd="/tmp", check=True)
        except subprocess.CalledProcessError as e:
            error_output = str(e)
            if container_name and ("already in use" in error_output or "Conflict" in error_output):
                logging.info(
                    f"Container name conflict detected. Attempting to attach to existing container '{container_name}'..."
                )
                if container_exists(container_name):
                    attach_to_container(container_name, docker_workdir)
                    return

                logging.error(
                    f"Container '{container_name}' was reported as conflicting but doesn't exist. This is unexpected."
                )
            raise

    except Exception as e:
        logging.error(f"Failed to run rocker: {e}")
        raise
    finally:
        os.chdir(original_cwd)


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

    # Completing owner/repo
    candidates = []
    for owner_repo in list_owners_and_repos():
        if owner_repo.startswith(current_word):
            candidates.append(owner_repo)
    return candidates


def get_completion_script_content() -> str:
    """Generate the bash completion script content."""
    return """#!/bin/bash
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
        
        # Don't add space if we're completing a repo name (no @ in current word)
        # This allows users to type @ after the repo name
        if [[ "$cur" != *"@"* ]] && [[ ${#COMPREPLY[@]} -eq 1 ]]; then
            # Check if the completion is a repo (contains /)
            if [[ "${COMPREPLY[0]}" == *"/"* ]]; then
                # Disable space suffix for repo completions
                compopt -o nospace
            fi
        fi
    else
        COMPREPLY=()
    fi
}

# Register the completion function
complete -F _renv_complete renv
"""


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
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                # Remove the * marker if present
                branch = line.lstrip("* ")
                branches.append(branch)

        # Look for common default branch names in order of preference
        for default_name in ["main", "master", "develop"]:
            if default_name in branches:
                return default_name

        # If no common default found, use the first branch
        if branches:
            return branches[0]

    except subprocess.CalledProcessError:
        pass

    # Fallback to 'main' if all else fails
    return "main"


def load_defaults_config(path: str = ".") -> dict:
    """Load rockerc.defaults.yaml and return default configuration

    Looks for rockerc.defaults.yaml file in the following order:
    1. Current directory (for local overrides)
    2. ~/.renv/rockerc.defaults.yaml (global renv config)
    3. Home directory (fallback)

    If no defaults file is found, creates a default one in ~/.renv/rockerc.defaults.yaml

    Args:
        path (str, optional): Path to search for defaults file. Defaults to ".".

    Returns:
        dict: A dictionary with default configuration
    """
    # Use top-level imports
    # Search locations in order of preference
    search_paths = [
        Path(path) / "rockerc.defaults.yaml",  # Local directory
        Path(path) / "renv" / "rockerc.defaults.yaml",  # Local renv config
    ]

    defaults_found = False
    defaults_config = {"args": []}

    for defaults_path in search_paths:
        if defaults_path.exists():
            print(f"loading defaults file {defaults_path}")
            try:
                with open(defaults_path, "r", encoding="utf-8") as f:
                    defaults_config = yaml.safe_load(f) or {"args": []}
                defaults_found = True
                break  # Use first found file
            except Exception as e:
                logging.warning(f"Error reading rockerc.defaults.yaml file: {e}")
                continue

    # If no defaults file was found, create a default one in the global renv config location
    if not defaults_found:
        local_defaults_path = Path(path) / "renv" / "rockerc.defaults.yaml"
        ensure_defaults_yaml()
        try:
            with open(local_defaults_path, "r", encoding="utf-8") as f:
                defaults_config = yaml.safe_load(f) or {"args": []}
        except Exception as e:
            logging.warning(f"Error reading newly created rockerc.defaults.yaml file: {e}")
            defaults_config = {"args": []}

    return defaults_config


def ensure_manifest_rocker_repo():
    """
    Ensure that blooop/manifest_rocker is cloned into the renv environment as 'renv'.
    """
    owner = "blooop"
    repo = "manifest_rocker"
    target_repo_name = "renv"
    target_dir = get_renv_base_dir() / owner / target_repo_name
    if not (target_dir.exists() and (target_dir / "HEAD").exists()):
        try:
            # Clone to a temp dir, then rename
            temp_dir = get_renv_base_dir() / owner / repo
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)
            clone_bare_repo(owner, repo)
            # Rename manifest_rocker to renv
            if temp_dir.exists():
                temp_dir.rename(target_dir)
            logging.info(f"Cloned {owner}/{repo} into renv environment as '{target_repo_name}'.")
        except Exception as e:
            logging.warning(f"Could not clone {owner}/{repo} as '{target_repo_name}': {e}")


def main():
    setup_logging()
    ensure_defaults_yaml()
    ensure_manifest_rocker_repo()  # Ensure manifest_rocker is present
    parser = argparse.ArgumentParser(
        description="Repository Environment Manager - seamlessly work in multiple repos using git worktrees and rocker containers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  renv blooop/bencher@main             # Clone blooop/bencher and switch to main branch
  renv blooop/bencher@feature          # Switch to feature branch (creates worktree if needed)
  renv blooop/bencher@main#scripts     # Work in the scripts subfolder of main branch
  renv osrf/rocker                     # Clone osrf/rocker and switch to main branch (default)
  renv --force blooop/bencher@main     # Force rebuild container even if it exists
  renv --install                       # Install bash completion
  renv --uninstall                     # Uninstall bash completion
  
The tool will:
1. Clone the repository as a bare repo to ~/renv/owner/repo (if not already cloned)
2. Create a worktree for the specified branch at ~/renv/owner/repo/worktree-{branch}
3. Optionally change to a subfolder within the repository if specified with #subfolder
4. If a container exists for this repo@branch, attach to it automatically
5. If --force is used, remove existing container and rebuild from scratch
6. Run rockerc in that directory to build and enter a container
        """,
    )
    parser.add_argument(
        "repo_spec",
        nargs="?",
        help="Repository specification in format 'owner/repo[@branch][#subfolder]'. If branch is omitted, 'main' is used.",
    )
    parser.add_argument(
        "--no-container",
        action="store_true",
        help="Set up the worktree but don't run rockerc (for debugging or manual container management)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force rebuild the container even if it already exists",
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
        "--version",
        "-v",
        action="store_true",
        help="Show version information",
    )
    parser.add_argument(
        "--nocache",
        action="store_true",
        help="Rebuild the container with no cache (pass --no-cache to docker build)",
    )
    # Parse known args, leave extra for passing to rockerc/rocker
    args, extra_args = parser.parse_known_args()

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
        # Use fuzzy finder for interactive selection
        try:
            user_input = fuzzy_select_repo_spec()
            if user_input is None:
                print("\nExiting.")
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)
        if not user_input or not user_input.strip():
            sys.exit(0)
        args.repo_spec = user_input.strip()
    try:
        owner, repo, branch, subfolder = parse_repo_spec(args.repo_spec)
        if subfolder:
            logging.info(f"Setting up environment for {owner}/{repo}@{branch}#{subfolder}")
        else:
            logging.info(f"Setting up environment for {owner}/{repo}@{branch}")
        worktree_dir = setup_repo_environment(owner, repo, branch)
        if args.no_container:
            if subfolder:
                target_dir = worktree_dir / subfolder
                logging.info(f"Environment ready at {target_dir}")
                logging.info(f"To manually run rockerc: cd {target_dir} && rockerc")
            else:
                logging.info(f"Environment ready at {worktree_dir}")
                logging.info(f"To manually run rockerc: cd {worktree_dir} && rockerc")
        else:
            # Only pass command arguments after repo_spec
            command = extra_args.copy() if extra_args else None
            if command and len(command) > 0 and command[0] == args.repo_spec:
                command = command[1:]
            run_rockerc_in_worktree(
                worktree_dir,
                owner,
                repo,
                branch,
                subfolder=subfolder,
                force=args.force,
                nocache=args.nocache,
                command=command if command else None,
            )
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
