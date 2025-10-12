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
import importlib.metadata
import pathlib
import logging
import argparse
import time
import yaml
import shutil
import shlex
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager

from .completion_loader import load_completion_script
from .rockerc import deduplicate_extensions


# Shared utility for git subprocess.run
def git_run(args, **kwargs):
    """Run a git command with consistent error handling."""
    # Security: args must be a list of static strings, not user-controlled
    # If any element is user-controlled, use shlex.quote()
    safe_args = [str(a) for a in args]
    try:
        return subprocess.run(["git"] + safe_args, check=True, **kwargs)
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {' '.join(safe_args)}; {e}")
        raise


# Context manager for changing cwd
@contextmanager
def cwd(path: str):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


# Helper for sparse-checkout setup/update
def _apply_sparse_checkout(branch_dir: pathlib.Path, subfolder: str, reapply: bool = False):
    base = ["-C", str(branch_dir), "sparse-checkout"]
    git_run(base + ["init", "--cone"])
    git_run(base + ["set", subfolder])
    if reapply:
        git_run(base + ["reapply"])
    _verify_sparse_checkout_path(branch_dir, subfolder, branch_dir.name)


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
    """Get the root directory for renv repositories.

    Prefers `RENV_DIR` when set, otherwise falls back to `~/renv`.
    """

    renv_dir = os.environ.get("RENV_DIR", "~/renv")
    return pathlib.Path(renv_dir).expanduser()


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
    repos: set[str] = set()
    for entry in user_dir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if (entry / ".git").exists():
            # Legacy layout repo-branch directories (e.g., repo-main, repo-with-dashes-main)
            if "-" in entry.name:
                name = entry.name.rsplit("-", 1)[0]
            else:
                name = entry.name
            repos.add(name)
        else:
            repos.add(entry.name)
    return sorted(repos)


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


# --- Review: Replace branch_exists/remote_branch_exists with git_ref_exists ---
def git_ref_exists(repo_dir: pathlib.Path, ref: str) -> bool:
    """Return True if <ref> (branch or origin/branch) is known to git."""
    return (
        subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--verify", ref],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


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
        logging.info("No repositories found in %s. Clone some repos first!", get_renv_root())
        return None

    print("Select repo@branch (type 'bl tes ma' for blooop/test_renv@main):")
    selected = iterfzf(combinations, multi=False)
    return selected


def renv_completion_block(shell: str = "bash") -> str:
    """Return the completion block for renv."""
    if shell != "bash":
        raise ValueError("Only bash completion is currently supported")
    return f"{load_completion_script('renv').rstrip()}\n"


def install_shell_completion(shell: str = "bash", rc_path: Optional[pathlib.Path] = None) -> int:
    """Install shell autocompletion via the centralized installer."""
    if shell != "bash":
        logging.error("Only bash completion is currently supported")
        return 1

    try:
        from .completion import install_all_completions
    except ImportError as error:  # pragma: no cover - defensive
        logging.error("Unable to load completion installer: %s", error)
        return 1
    return install_all_completions(rc_path)


def get_repo_dir(repo_spec: RepoSpec) -> pathlib.Path:
    """Get the directory path for a repository cache"""
    return get_renv_root() / ".cache" / repo_spec.owner / repo_spec.repo


def _get_repo_workspace_root(repo_spec: RepoSpec) -> pathlib.Path:
    """Return the workspace directory dedicated to a repo."""
    return get_renv_root() / repo_spec.owner / repo_spec.repo


def get_legacy_worktree_dir(repo_spec: RepoSpec) -> pathlib.Path:
    """Return the legacy branch directory path (pre repo-folder layout).

    Returns: ~/renv/{owner}/{repo}-{branch}
    """
    safe_branch = repo_spec.branch.replace("/", "-")
    return get_renv_root() / repo_spec.owner / f"{repo_spec.repo}-{safe_branch}"


def get_previous_worktree_dir(repo_spec: RepoSpec) -> pathlib.Path:
    """Return the previous branch directory path (before cwd-based layout).

    Returns: ~/renv/{owner}/{repo}/{repo}-{branch}
    """
    safe_branch = repo_spec.branch.replace("/", "-")
    return _get_repo_workspace_root(repo_spec) / f"{repo_spec.repo}-{safe_branch}"


def get_worktree_dir(repo_spec: RepoSpec) -> pathlib.Path:
    """Get the branch copy directory path for a repository and branch.

    Returns: ~/renv/{owner}/{repo}/{branch}/{repo}
    """
    safe_branch = repo_spec.branch.replace("/", "-")
    return _get_repo_workspace_root(repo_spec) / safe_branch / repo_spec.repo


def _verify_sparse_checkout_path(branch_dir: pathlib.Path, subfolder: str, branch: str) -> None:
    """Ensure the sparse-checkout subfolder exists in the repository history."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(branch_dir),
            "rev-parse",
            "--verify",
            f"HEAD:{subfolder}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FileNotFoundError(f"Subfolder '{subfolder}' not found in branch '{branch}'.")


def _has_upstream(branch_dir: pathlib.Path) -> bool:
    """Return True if the current branch has an upstream configured."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(branch_dir),
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{u}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def load_renv_rockerc_config() -> dict:
    """Load global renv rockerc configuration from ~/renv/rockerc.yaml

    Creates the file from template if it doesn't exist.

    Returns:
        dict: Parsed configuration dictionary, or empty dict if parsing fails.
    """
    renv_dir = get_renv_root()
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
    """Generate container name from repo specification

    Uses '.' separator between repo and branch, and 'sub-' prefix for subfolder
    to prevent naming conflicts between branch names and subfolder paths.
    """
    safe_branch = repo_spec.branch.replace("/", "-")
    # Use '.' separator between repo and branch
    base_name = f"{repo_spec.repo}.{safe_branch}"
    if repo_spec.subfolder:
        # Use 'sub-' prefix and sanitize subfolder path
        safe_subfolder = repo_spec.subfolder.replace("/", "-")
        result = f"{base_name}-sub-{safe_subfolder}"
    else:
        result = base_name
    # Sanitize to allow only alphanumeric, dash, underscore, dot
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", result)


def get_hostname(repo_spec: RepoSpec) -> str:
    """Generate hostname from repo specification

    Returns just the repo name as hostname, without branch information.
    """
    # Sanitize to allow only alphanumeric, dash, underscore
    return re.sub(r"[^a-zA-Z0-9_-]", "_", repo_spec.repo)


def setup_cache_repo(repo_spec: RepoSpec) -> pathlib.Path:
    """Clone or update cache repository (full clone, not bare)"""
    repo_dir = get_repo_dir(repo_spec)
    repo_url = f"git@github.com:{repo_spec.owner}/{repo_spec.repo}.git"

    if not repo_dir.exists():
        logging.info(f"Cloning cache repository: {repo_url}")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        # repo_url and repo_dir are constructed, not user input
        subprocess.run(
            ["git", "clone", repo_url, str(repo_dir)], check=True, cwd=str(repo_dir.parent)
        )
    else:
        logging.info(f"Fetching updates for cache: {repo_url}")
        subprocess.run(["git", "-C", str(repo_dir), "fetch", "--all"], check=True)

    return repo_dir


def setup_branch_copy(repo_spec: RepoSpec) -> pathlib.Path:
    """Set up branch copy by copying from cache and checking out branch

    If repo_spec.subfolder is specified, enables sparse-checkout to only
    check out that subfolder in the working tree.
    """
    cache_dir = get_repo_dir(repo_spec)
    branch_dir = get_worktree_dir(repo_spec)
    repo_workspace = _get_repo_workspace_root(repo_spec)
    repo_workspace.mkdir(parents=True, exist_ok=True)

    # Handle migrations from old layouts
    # Priority: previous layout > legacy layout (migrate from newest to oldest)
    previous_dir = get_previous_worktree_dir(repo_spec)
    legacy_dir = get_legacy_worktree_dir(repo_spec)

    if not branch_dir.exists():
        # Try to migrate from previous layout first
        if previous_dir.exists():
            logging.info(f"Migrating from previous layout for {repo_spec.repo}@{repo_spec.branch}")
            # Create parent branch directory
            branch_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(previous_dir), str(branch_dir))
        # Otherwise try legacy layout
        elif legacy_dir.exists():
            logging.info(f"Migrating from legacy layout for {repo_spec.repo}@{repo_spec.branch}")
            # Create parent branch directory
            branch_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy_dir), str(branch_dir))

    # Ensure cache repo exists and is updated
    setup_cache_repo(repo_spec)

    if not branch_dir.exists():
        logging.info(f"Creating branch copy for: {repo_spec.branch}")

        # Copy entire cache directory to branch directory
        shutil.copytree(cache_dir, branch_dir)
        # Ensure remote references are up to date in the new working tree
        subprocess.run(
            ["git", "-C", str(branch_dir), "fetch", "--all"],
            check=True,
        )

        # Use git_ref_exists to check for local and remote branch
        local = git_ref_exists(branch_dir, repo_spec.branch)
        remote = git_ref_exists(branch_dir, f"origin/{repo_spec.branch}")
        default = get_default_branch(repo_spec)

        try:
            if local:
                logging.info(f"Checking out local branch: {repo_spec.branch}")
                subprocess.run(
                    ["git", "-C", str(branch_dir), "checkout", repo_spec.branch],
                    check=True,
                )
            elif remote:
                logging.info(f"Checking out remote branch: {repo_spec.branch}")
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(branch_dir),
                        "checkout",
                        "-b",
                        repo_spec.branch,
                        f"origin/{repo_spec.branch}",
                    ],
                    check=True,
                )
            else:
                logging.info(
                    f"Branch '{repo_spec.branch}' doesn't exist, creating from '{default}'"
                )
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(branch_dir),
                        "checkout",
                        "--no-track",
                        "-b",
                        repo_spec.branch,
                        f"origin/{default}",
                    ],
                    check=True,
                )
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to checkout branch '{repo_spec.branch}'. Error: {e}")
            raise
        if not remote and _has_upstream(branch_dir):
            # Newly created branches should not track the default branch automatically
            subprocess.run(
                ["git", "-C", str(branch_dir), "branch", "--unset-upstream"],
                check=False,
            )

        # Enable sparse checkout if subfolder specified
        if repo_spec.subfolder:
            logging.info(f"Enabling sparse-checkout for subfolder: {repo_spec.subfolder}")
            # Initialize sparse-checkout in cone mode
            subprocess.run(
                ["git", "-C", str(branch_dir), "sparse-checkout", "init", "--cone"],
                check=True,
            )
            # Set the subfolder pattern
            subprocess.run(
                ["git", "-C", str(branch_dir), "sparse-checkout", "set", repo_spec.subfolder],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(branch_dir), "sparse-checkout", "reapply"],
                check=True,
            )
            logging.info(f"Sparse-checkout configured for: {repo_spec.subfolder}")
            _verify_sparse_checkout_path(branch_dir, repo_spec.subfolder, repo_spec.branch)
    else:
        logging.info(f"Branch copy already exists: {branch_dir}")
        # Fetch and pull latest changes
        subprocess.run(
            ["git", "-C", str(branch_dir), "fetch", "--all"],
            check=True,
        )
        if _has_upstream(branch_dir):
            subprocess.run(
                ["git", "-C", str(branch_dir), "pull"],
                check=False,  # Don't fail if already up to date
            )
        else:
            logging.info("Skipping git pull for %s (no upstream configured)", branch_dir)

        # Update sparse checkout if subfolder specified and not already configured
        if repo_spec.subfolder:
            # Check if sparse-checkout is already enabled
            sparse_checkout_file = branch_dir / ".git" / "info" / "sparse-checkout"
            if not sparse_checkout_file.exists():
                logging.info(f"Enabling sparse-checkout for subfolder: {repo_spec.subfolder}")
                subprocess.run(
                    ["git", "-C", str(branch_dir), "sparse-checkout", "init", "--cone"],
                    check=True,
                )
            # Update the subfolder pattern
            subprocess.run(
                ["git", "-C", str(branch_dir), "sparse-checkout", "set", repo_spec.subfolder],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(branch_dir), "sparse-checkout", "reapply"],
                check=True,
            )
            _verify_sparse_checkout_path(branch_dir, repo_spec.subfolder, repo_spec.branch)

    return branch_dir


AVAILABLE_ROCKER_EXTENSIONS: Optional[set[str]] = None
ESSENTIAL_CORE_ARGS = {"pull", "persist-image"}


def _get_available_rocker_extensions() -> set[str]:
    """Discover rocker extension names available in the current environment."""
    global AVAILABLE_ROCKER_EXTENSIONS  # pylint: disable=global-statement
    if AVAILABLE_ROCKER_EXTENSIONS is not None:
        return AVAILABLE_ROCKER_EXTENSIONS

    try:
        entry_points = importlib.metadata.entry_points()
        group = entry_points.select(group="rocker.extensions")
        AVAILABLE_ROCKER_EXTENSIONS = {ep.name.replace("_", "-") for ep in group}
    except Exception as exc:  # pragma: no cover - defensive, shouldn't happen
        logging.warning("Failed to discover rocker extensions: %s", exc)
        AVAILABLE_ROCKER_EXTENSIONS = set()
    return AVAILABLE_ROCKER_EXTENSIONS


def _filter_unavailable_extensions(args: list[str]) -> Tuple[list[str], list[str]]:
    """Filter out extensions that are not installed in the current environment."""
    if not args:
        return [], []

    available = _get_available_rocker_extensions()
    kept = []
    removed = []
    for arg in args:
        normalized = arg.replace("_", "-")
        # Always keep 'auto' and 'auto=...' arguments
        if (
            normalized == "auto"
            or (isinstance(arg, str) and arg.startswith("auto="))
            or normalized in ESSENTIAL_CORE_ARGS
            or normalized in available
        ):
            kept.append(arg)
        else:
            removed.append(arg)
    return kept, removed


def build_rocker_config(
    repo_spec: RepoSpec,
    force: bool = False,  # pylint: disable=unused-argument
    nocache: bool = False,  # pylint: disable=unused-argument
) -> Dict[str, Any]:
    """Build rocker configuration using rockerc's config loading

    This loads:
    1. Renv global config from ~/renv/rockerc.yaml (creates from template if needed)
    2. Repo-specific config from the worktree's rockerc.yaml (if it exists)
    3. Standard global config from ~/.rockerc.yaml (if it exists)

    Precedence (highest to lowest):
    - Repo-specific config
    - Renv global config
    - Standard global config
    """
    from rockerc.rockerc import (
        load_global_config,
        _load_and_validate_config,
    )

    container_name = get_container_name(repo_spec)
    branch_dir = get_worktree_dir(repo_spec)

    def _load_configs():
        standard = load_global_config()
        renv = load_renv_rockerc_config()
        repo = {}
        if branch_dir.exists():
            repo_config_path = branch_dir / "rockerc.yaml"
            if repo_config_path.exists():
                repo = _load_and_validate_config(repo_config_path)
        return standard, renv, repo

    def _merge_args(*args_lists):
        merged = []
        for lst in args_lists:
            if lst:
                merged.extend(lst)
        return deduplicate_extensions(merged)

    def _merge_blacklists(*blists):
        merged = []
        for bl in blists:
            if not isinstance(bl, list):
                if bl:
                    merged.append(bl)
            elif bl:
                merged.extend(bl)
        return deduplicate_extensions(merged)

    standard, renv, repo = _load_configs()
    config = standard.copy()
    config.update(renv)
    config.update(repo)

    # Merge and deduplicate args
    config["args"] = _merge_args(
        standard.get("args", []), renv.get("args", []), repo.get("args", [])
    )
    # Merge and deduplicate blacklists
    config["extension-blacklist"] = _merge_blacklists(
        standard.get("extension-blacklist", []),
        renv.get("extension-blacklist", []),
        repo.get("extension-blacklist", []),
    )

    # Remove cwd extension - we use explicit volume mounts to /{repo} instead
    if "cwd" in config["args"]:
        config["args"].remove("cwd")

    # Ensure 'auto' is always present and set to correct path
    auto_path = f"~/renv/{repo_spec.owner}/{repo_spec.repo}/{repo_spec.branch}/{repo_spec.repo}"
    found_auto = False
    for i, arg in enumerate(config["args"]):
        if arg == "auto" or (isinstance(arg, str) and arg.strip() == "auto"):
            config["args"][i] = f"auto={auto_path}"
            found_auto = True
        elif isinstance(arg, str) and arg.startswith("auto="):
            config["args"][i] = f"auto={auto_path}"
            found_auto = True
    if not found_auto:
        config["args"].insert(0, f"auto={auto_path}")

    # Filter unavailable extensions
    filtered_args, removed_args = _filter_unavailable_extensions(config.get("args", []))
    if removed_args:
        logging.warning(
            "Removing unavailable rocker extensions: %s",
            ", ".join(sorted(removed_args)),
        )
    config["args"] = filtered_args

    # Set renv-specific parameters
    config["name"] = container_name
    config["hostname"] = get_hostname(repo_spec)
    # Target dir is the working directory we cd to before calling rocker
    config["_renv_target_dir"] = (
        str(branch_dir / repo_spec.subfolder) if repo_spec.subfolder else str(branch_dir)
    )

    meta = {
        "original_global_args": standard.get("args", []) or None,
        "original_project_args": (renv.get("args", []) + repo.get("args", [])) or None,
        "merged_args_before_blacklist": config.get("args", []),
        "removed_by_blacklist": [],
        "blacklist": config.get("extension-blacklist", []),
        "original_global_blacklist": standard.get("extension-blacklist", []) or None,
        "original_project_blacklist": (
            renv.get("extension-blacklist", []) + repo.get("extension-blacklist", [])
        )
        or None,
        "global_config_used": bool(standard or renv),
        "project_config_used": bool(repo),
        "source_files": [],
    }

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
        # Skip internal markers (keys starting with underscore) and special keys
        if key.startswith("_"):
            continue
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
    worktree_cwd = None
    # Extract worktree directory from volume mounts
    for volume in volumes:
        if "/workspace/" in volume and not volume.endswith(".git"):
            host_path = volume.split(":")[0]
            if pathlib.Path(host_path).exists():
                worktree_cwd = host_path
                logging.info(f"Using worktree directory as cwd: {worktree_cwd}")
                break

    # Enable Docker BuildKit for improved build performance
    env = {**os.environ, "DOCKER_BUILDKIT": "1"}

    if detached:
        # Security: cmd_parts is constructed from validated config and arguments
        with subprocess.Popen(
            cmd_parts,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=worktree_cwd,
            env=env,
        ):
            time.sleep(2)
        return 0
    # Security: cmd_parts is constructed from validated config and arguments
    return subprocess.run(cmd_parts, check=False, cwd=worktree_cwd, env=env).returncode


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


def manage_container(  # pylint: disable=too-many-positional-arguments,too-many-return-statements
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

    # Set up branch copy (with sparse-checkout if subfolder specified)
    branch_dir = setup_branch_copy(repo_spec)

    container_name = get_container_name(repo_spec)

    # Determine workspace mount path and any additional volumes
    # For subfolders: mount only that directory and provide a .git bind mount
    # For full repo: mount branch directory to /{repo}
    extra_volumes = []
    if repo_spec.subfolder:
        mount_path = branch_dir / repo_spec.subfolder
        extra_volumes.append(
            (
                branch_dir / ".git",
                f"/{repo_spec.repo}/.git",
            )
        )
    else:
        mount_path = branch_dir

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
    @contextmanager
    def _restore_cwd_context():
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            logging.warning(
                "Current working directory missing; defaulting subsequent operations to %s",
                branch_dir,
            )
            original_cwd = None
        target = (
            original_cwd
            if original_cwd and pathlib.Path(original_cwd).exists()
            else str(branch_dir)
        )
        try:
            os.chdir(target_dir)
        except FileNotFoundError as exc:
            target_path = pathlib.Path(target_dir)
            logging.error(
                "Target directory missing after setup: %s (branch dir: %s)",
                target_path,
                branch_dir,
            )
            raise FileNotFoundError(f"Target directory not found: {target_path}") from exc
        try:
            yield
        finally:
            try:
                os.chdir(target)
            except FileNotFoundError as exc:
                logging.error(
                    "Failed to restore cwd: target directory missing (%s). original_cwd: %s, branch_dir: %s",
                    target,
                    original_cwd,
                    branch_dir,
                )
                raise FileNotFoundError(
                    f"Could not restore cwd, target directory not found: {target} (original_cwd: {original_cwd}, branch_dir: {branch_dir})"
                ) from exc

    try:
        from rockerc.core import (
            prepare_launch_plan,
            launch_rocker,
            wait_for_container,
            launch_vscode,
        )

        with _restore_cwd_context():
            # Handle VSCode mode using unified backend (same as rockervsc)
            if vsc:
                # For renv, mount to /{repo} at root, not /workspaces/{container_name}
                mount_target = f"/{repo_spec.repo}"
                plan = prepare_launch_plan(
                    args_dict=config,
                    extra_cli="",
                    container_name=container_name,
                    vscode=True,
                    force=force,
                    path=mount_path,
                    extensions=config.get("args", []),
                    extra_volumes=extra_volumes,
                    mount_target=mount_target,
                )

                if plan.rocker_cmd:
                    ret = launch_rocker(plan.rocker_cmd)
                    if ret != 0:
                        return ret

                # Change to branch_dir for docker exec operations (must be in mounted directory)
                os.chdir(branch_dir)

                if not wait_for_container(container_name):
                    logging.error(f"Timed out waiting for container '{container_name}'")
                    return 1

                if not plan.created:
                    test_result = subprocess.run(
                        ["docker", "exec", container_name, "pwd"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if (
                        test_result.returncode != 0
                        or "container breakout" in test_result.stderr.lower()
                    ):
                        logging.info(
                            "Container appears corrupted (possible breakout detection), rebuilding for VSCode"
                        )
                        from rockerc.core import stop_and_remove_container as core_stop_and_remove

                        core_stop_and_remove(container_name)

                        from rockerc.core import (
                            ensure_name_args,
                            add_extension_env,
                            ensure_volume_binding,
                            append_volume_binding,
                        )
                        from rockerc.rockerc import yaml_dict_to_args

                        injections = ""
                        injections = ensure_name_args(injections, container_name)
                        injections = add_extension_env(injections, config.get("args", []))
                        injections = ensure_volume_binding(injections, container_name, mount_path)
                        for host_path, target in extra_volumes:
                            injections = append_volume_binding(injections, host_path, target)

                        args_copy = dict(config)
                        rocker_argline = yaml_dict_to_args(args_copy, injections)
                        rocker_cmd = ["rocker"] + shlex.split(rocker_argline)

                        logging.info(f"Rebuilding container: {' '.join(rocker_cmd)}")

                        env = {**os.environ, "DOCKER_BUILDKIT": "1"}
                        result = subprocess.run(rocker_cmd, check=False, cwd=branch_dir, env=env)
                        if result.returncode != 0:
                            return result.returncode

                        time.sleep(2)

                        if not wait_for_container(container_name):
                            logging.error(
                                f"Timed out waiting for rebuilt container '{container_name}'"
                            )
                            return 1

                if plan.vscode:
                    # For non-subfolder: open /{repo} at root
                    # For subfolder: open /{repo} (subfolder is mounted directly)
                    vsc_folder = f"/{repo_spec.repo}"
                    launch_vscode(plan.container_name, plan.container_hex, vsc_folder)

                # Open interactive shell with correct working directory
                # Working directory is always /{repo} at root
                workdir = f"/{repo_spec.repo}"
                if sys.stdin.isatty() and sys.stdout.isatty():
                    exec_cmd = ["docker", "exec", "-it", "-w", workdir, container_name, "/bin/bash"]
                else:
                    exec_cmd = ["docker", "exec", "-w", workdir, container_name, "/bin/bash"]

                logging.info(f"Attaching interactive shell: {' '.join(exec_cmd)}")
                return subprocess.run(exec_cmd, check=False).returncode

            # Terminal mode: use detached workflow (same as rockerc)
        # For renv, mount to /{repo} at root, not /workspaces/{container_name}
        mount_target = f"/{repo_spec.repo}"
        plan = prepare_launch_plan(
            args_dict=config,
            extra_cli="",
            container_name=container_name,
            vscode=False,
            force=force,
            path=mount_path,
            extensions=config["args"],
            extra_volumes=extra_volumes,
            mount_target=mount_target,
        )

        # Add keep-alive command to rocker_cmd so detached container stays running
        if plan.rocker_cmd:
            plan.rocker_cmd.extend(["tail", "-f", "/dev/null"])

        # If we need to launch a new container, do it
        if plan.rocker_cmd:
            ret = launch_rocker(plan.rocker_cmd)
            if ret != 0:
                # Restore cwd using context manager
                with _restore_cwd_context():
                    pass
                return ret

        # Wait for container to be ready
        if not wait_for_container(container_name):
            logging.error(f"Timed out waiting for container '{container_name}'")
            with _restore_cwd_context():
                pass
            return 1

        # Test for container breakout (if directory was deleted while container running)
        # Only test if we're reusing an existing container
        # Working directory is always /{repo} at root
        workdir = f"/{repo_spec.repo}"

        if not plan.created:
            # Test if we can actually access the working directory
            # Just checking if it exists isn't enough - we need to try to use it
            test_result = subprocess.run(
                ["docker", "exec", "-w", workdir, container_name, "pwd"],
                capture_output=True,
                text=True,
                check=False,
            )

            stderr_val = test_result.stderr or ""
            if test_result.returncode != 0 or "container breakout" in stderr_val.lower():
                # Container is corrupted - rebuild it
                logging.info(
                    "Container appears corrupted (possible breakout detection), rebuilding"
                )
                from rockerc.core import stop_and_remove_container as core_stop_and_remove

                core_stop_and_remove(container_name)

                # Rebuild container
                plan = prepare_launch_plan(
                    args_dict=config,
                    extra_cli="",
                    container_name=container_name,
                    vscode=False,
                    force=True,
                    path=mount_path,
                    extensions=config["args"],
                    extra_volumes=extra_volumes,
                    mount_target=mount_target,
                )

                if plan.rocker_cmd:
                    plan.rocker_cmd.extend(["tail", "-f", "/dev/null"])
                    ret = launch_rocker(plan.rocker_cmd)
                    if ret != 0:
                        with _restore_cwd_context():
                            pass
                        return ret

                if not wait_for_container(container_name):
                    logging.error(f"Timed out waiting for rebuilt container '{container_name}'")
                    with _restore_cwd_context():
                        pass
                    return 1

        # Execute command or attach interactive shell with working directory set

        if command:
            # Ensure command is a list of strings
            if not (isinstance(command, list) and all(isinstance(x, str) for x in command)):
                raise ValueError("command must be a list of strings")
            # Use -it for interactive AI commands
            interactive_agents = {"gemini", "claude", "codex"}
            use_tty = command and command[0] in interactive_agents
            exec_cmd = ["docker", "exec"]
            if use_tty:
                exec_cmd.append("-it")
            exec_cmd += ["-w", workdir, container_name] + command
            logging.info(f"Executing command: {' '.join(exec_cmd)}")
            result = subprocess.run(exec_cmd, check=False)
            with _restore_cwd_context():
                pass
            return result.returncode

        # Attach interactive shell - need to set working directory via env or wrapper
        # Since core.py's interactive_shell doesn't support -w flag, we need to use our own exec
        # Check if we have a TTY to use -it flags
        if sys.stdin.isatty() and sys.stdout.isatty():
            exec_cmd = ["docker", "exec", "-it", "-w", workdir, container_name, "/bin/bash"]
        else:
            # No TTY, run without -it
            exec_cmd = ["docker", "exec", "-w", workdir, container_name, "/bin/bash"]

        logging.info(f"Attaching interactive shell: {' '.join(exec_cmd)}")
        result = subprocess.run(exec_cmd, check=False)
        with _restore_cwd_context():
            pass
        return result.returncode
    finally:
        # Restore original working directory
        with _restore_cwd_context():
            pass


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

    parser.add_argument("--vsc", action="store_true", help="Launch with VS Code integration")

    parsed_args = parser.parse_args(args)

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
