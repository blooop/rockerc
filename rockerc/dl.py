"""
dl - DevLaunch CLI

A streamlined CLI for devpod with intuitive autocomplete and fzf fuzzy selection.
Provides an renv-like UX for managing devcontainer workspaces.

Usage:
    dl                           # fzf selector for existing workspaces
    dl <workspace>               # open/create workspace, attach shell
    dl <workspace> <command>     # run command in workspace
    dl owner/repo                # create from git repo (github.com)
    dl owner/repo@branch         # specific branch
    dl ./path                    # create from local path
    dl --ls                      # list workspaces
    dl --stop <workspace>        # stop workspace
    dl --rm <workspace>          # delete workspace
    dl --code <workspace>        # open in VS Code
    dl --install                 # install completions
"""

import sys
import subprocess
import json
import logging
import pathlib
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .completion import install_all_completions

logging.basicConfig(level=logging.INFO, format="%(message)s")

# Cache configuration
CACHE_DIR = pathlib.Path.home() / ".cache" / "dl"
CACHE_FILE = CACHE_DIR / "completions.json"


def get_cache_path() -> pathlib.Path:
    """Get the path to the completion cache file."""
    return CACHE_FILE


def read_completion_cache() -> Optional[Dict[str, Any]]:
    """Read completion data from cache file."""
    cache_path = get_cache_path()
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_completion_cache(data: Dict[str, Any]) -> None:
    """Write completion data to cache file."""
    cache_path = get_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def update_completion_cache() -> Dict[str, Any]:
    """Update the completion cache with current data."""
    workspaces = list_workspaces()
    workspace_ids = [ws.id for ws in workspaces]
    repos = discover_repos_from_workspaces(workspaces)

    # Flatten repos to list of owner/repo strings
    known_repos = []
    for owner, repo_list in sorted(repos.items()):
        for repo in sorted(repo_list):
            known_repos.append(f"{owner}/{repo}")

    # Extract unique owners
    owners = sorted(repos.keys())

    data = {
        "workspaces": workspace_ids,
        "repos": known_repos,
        "owners": owners,
    }
    write_completion_cache(data)
    return data


def update_cache_background() -> None:
    """Update completion cache in background."""
    try:
        # pylint: disable=consider-using-with
        subprocess.Popen(
            [sys.executable, "-m", "rockerc.dl", "--update-cache"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass


# Regex to match owner/repo[@branch] format (not a path, not already a URL)

OWNER_REPO_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(@[a-zA-Z0-9_./%-]+)?$")


def is_path_spec(spec: str) -> bool:
    """Check if spec looks like a filesystem path."""
    return spec.startswith("./") or spec.startswith("/") or spec.startswith("~")


def is_git_spec(spec: str) -> bool:
    """Check if spec looks like a git repo (owner/repo or URL)."""
    # Paths are not git specs
    if is_path_spec(spec):
        return False
    if "://" in spec:
        return True
    if spec.startswith("github.com/") or spec.startswith("gitlab.com/"):
        return True
    return bool(OWNER_REPO_PATTERN.match(spec))


def expand_workspace_spec(spec: str) -> str:
    """Expand owner/repo[@branch] to github.com/owner/repo[@branch] for devpod."""
    # Don't expand if it's a path
    if is_path_spec(spec):
        return spec
    # Don't expand if it already looks like a URL
    if "://" in spec or spec.startswith("github.com/") or spec.startswith("gitlab.com/"):
        return spec
    # Check if it matches owner/repo[@branch] pattern
    if OWNER_REPO_PATTERN.match(spec):
        return f"github.com/{spec}"
    # Otherwise return as-is (existing workspace name)
    return spec


def validate_workspace_spec(spec: str, existing_ids: List[str]) -> Optional[str]:
    """Validate workspace spec and return error message if invalid."""
    # Valid if it's an existing workspace
    if spec in existing_ids:
        return None
    # Valid if it's a path
    if is_path_spec(spec):
        return None
    # Valid if it's a git spec (owner/repo or URL)
    if is_git_spec(spec):
        return None
    # Invalid - provide helpful error
    return f"Unknown workspace '{spec}'. Use 'dl --ls' to list workspaces, or specify owner/repo or ./path"


@dataclass
class Workspace:
    """Represents a devpod workspace."""

    id: str
    source_type: str  # "local" or "git"
    source: str
    last_used: str
    provider: str
    ide: str

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Workspace":
        """Parse workspace from devpod JSON output."""
        source = data.get("source", {})
        if "localFolder" in source:
            source_type = "local"
            source_path = source["localFolder"]
        elif "gitRepository" in source:
            source_type = "git"
            source_path = source["gitRepository"]
        else:
            source_type = "unknown"
            source_path = str(source)

        return cls(
            id=data.get("id", ""),
            source_type=source_type,
            source=source_path,
            last_used=data.get("lastUsed", ""),
            provider=data.get("provider", {}).get("name", ""),
            ide=data.get("ide", {}).get("name", ""),
        )


# Regex patterns for parsing git URLs
GIT_URL_PATTERNS = [
    # git@github.com:owner/repo.git
    re.compile(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$"),
    # https://github.com/owner/repo.git or https://github.com/owner/repo
    re.compile(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$"),
    # github.com/owner/repo
    re.compile(r"^github\.com/([^/]+)/([^/]+?)(?:\.git)?$"),
]


def parse_owner_repo_from_url(url: str) -> Optional[tuple]:
    """Extract (owner, repo) from a git URL."""
    for pattern in GIT_URL_PATTERNS:
        match = pattern.match(url)
        if match:
            return (match.group(1), match.group(2))
    return None


def get_git_remote_url(path: str) -> Optional[str]:
    """Get the origin remote URL from a git repository."""
    try:
        result = subprocess.run(
            ["git", "-C", path, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def get_git_branches(path: str) -> List[str]:
    """Get list of branches from a git repository."""
    try:
        result = subprocess.run(
            ["git", "-C", path, "branch", "-r"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            branches = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and "origin/" in line and "HEAD" not in line:
                    branch = line.replace("origin/", "")
                    branches.append(branch)
            return branches
    except (OSError, subprocess.SubprocessError):
        pass
    return []


def discover_repos_from_workspaces(workspaces: List[Workspace]) -> Dict[str, List[str]]:
    """Discover owner/repo from workspace git remotes.

    Returns dict mapping owner -> list of repos.
    """
    repos: Dict[str, List[str]] = {}

    for ws in workspaces:
        owner_repo = None

        # For git workspaces, parse the source URL directly
        if ws.source_type == "git":
            owner_repo = parse_owner_repo_from_url(ws.source)

        # For local workspaces, try to get git remote
        elif ws.source_type == "local" and ws.source:
            remote_url = get_git_remote_url(ws.source)
            if remote_url:
                owner_repo = parse_owner_repo_from_url(remote_url)

        if owner_repo:
            owner, repo = owner_repo
            if owner not in repos:
                repos[owner] = []
            if repo not in repos[owner]:
                repos[owner].append(repo)

    return repos


def get_known_repos() -> List[str]:
    """Get list of known owner/repo strings from workspaces."""
    workspaces = list_workspaces()
    repos = discover_repos_from_workspaces(workspaces)
    result = []
    for owner, repo_list in sorted(repos.items()):
        for repo in sorted(repo_list):
            result.append(f"{owner}/{repo}")
    return result


def run_devpod(args: List[str], capture: bool = False) -> subprocess.CompletedProcess:
    """Run a devpod command."""
    cmd = ["devpod"] + args
    logging.debug("Running: %s", " ".join(cmd))
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    return subprocess.run(cmd, check=False)


def list_workspaces() -> List[Workspace]:
    """List all devpod workspaces."""
    result = run_devpod(["list", "--output", "json"], capture=True)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
        return [Workspace.from_json(ws) for ws in data]
    except json.JSONDecodeError:
        logging.error("Failed to parse devpod output")
        return []


def get_workspace_ids() -> List[str]:
    """Get list of workspace IDs for completion."""
    return [ws.id for ws in list_workspaces()]


def print_workspaces():
    """Print workspace list in a nice format."""
    workspaces = list_workspaces()
    if not workspaces:
        print("No workspaces found.")
        return

    # Calculate column widths
    id_width = max(len(ws.id) for ws in workspaces)
    type_width = max(len(ws.source_type) for ws in workspaces)
    source_width = max(len(ws.source) for ws in workspaces)

    # Print header
    print(
        f"{'WORKSPACE':<{id_width}}  {'TYPE':<{type_width}}  {'SOURCE':<{source_width}}  LAST USED"
    )
    print("-" * (id_width + type_width + source_width + 30))

    # Print rows
    for ws in workspaces:
        last_used = ws.last_used[:19].replace("T", " ") if ws.last_used else "never"
        print(
            f"{ws.id:<{id_width}}  {ws.source_type:<{type_width}}  {ws.source:<{source_width}}  {last_used}"
        )


def fuzzy_select_workspace() -> Optional[str]:
    """Interactive fuzzy finder for workspace selection."""
    try:
        from iterfzf import iterfzf
    except ImportError:
        logging.error("iterfzf not available. Install with: pip install iterfzf")
        return None

    workspaces = list_workspaces()
    if not workspaces:
        logging.info("No workspaces found. Create one with: dl owner/repo or dl ./path")
        return None

    # Format options for display: "id | type | source"
    options = []
    ws_map = {}
    for ws in workspaces:
        label = f"{ws.id} | {ws.source_type} | {ws.source}"
        options.append(label)
        ws_map[label] = ws.id

    print("Select workspace (type to filter):")
    try:
        selected = iterfzf(options, multi=False)
    except KeyboardInterrupt:
        return None
    if selected:
        return ws_map.get(selected)
    return None


def workspace_up(
    workspace: str, ide: Optional[str] = None, recreate: bool = False, reset: bool = False
):
    """Start or create a workspace."""
    args = ["up", workspace]
    if ide:
        args.extend(["--ide", ide])
    if recreate:
        args.append("--recreate")
    if reset:
        args.append("--reset")
    return run_devpod(args)


def workspace_ssh(workspace: str, command: Optional[str] = None) -> int:
    """SSH into a workspace, optionally running a command."""
    args = ["ssh", workspace]
    if command:
        args.extend(["--command", command])
    result = run_devpod(args)
    return result.returncode


def workspace_stop(workspace: str) -> int:
    """Stop a workspace."""
    result = run_devpod(["stop", workspace])
    return result.returncode


def workspace_delete(workspace: str) -> int:
    """Delete a workspace."""
    result = run_devpod(["delete", workspace])
    return result.returncode


def workspace_status(workspace: str) -> int:
    """Get status of a workspace."""
    result = run_devpod(["status", workspace])
    return result.returncode


def print_help():
    """Print usage help."""
    help_text = """dl - DevLaunch CLI

Usage:
    dl                           Interactive workspace selector (fzf)
    dl <workspace>               Start workspace and attach shell
    dl <workspace> <command>     Run command in workspace
    dl owner/repo                Create workspace from GitHub repo
    dl owner/repo@branch         Create workspace from specific branch
    dl ./path                    Create workspace from local path

Commands:
    --ls                         List all workspaces
    --stop <workspace>           Stop a workspace
    --rm <workspace>             Delete a workspace
    --code <workspace>           Open workspace in VS Code
    --status <workspace>         Show workspace status
    --recreate <workspace>       Recreate workspace container
    --reset <workspace>          Reset workspace (clean slate)
    --install                    Install shell completions
    --help, -h                   Show this help

Examples:
    dl                           # Select workspace with fzf
    dl myproject                 # Open existing workspace
    dl loft-sh/devpod            # Create from GitHub
    dl blooop/rockerc@main       # Create from specific branch
    dl ./my-project              # Create from local folder
    dl --code myproject          # Open in VS Code
    dl myproject 'make test'     # Run command in workspace
"""
    print(help_text)


def main() -> int:
    """Main entry point for dl CLI."""
    args = sys.argv[1:]

    # Handle help
    if not args or (len(args) == 1 and args[0] in ("--help", "-h")):
        if not args:
            # No args - try fzf selection
            selected = fuzzy_select_workspace()
            if not selected:
                print_help()
                return 1
            workspace_up(selected)
            return workspace_ssh(selected)
        print_help()
        return 0

    # Handle flags
    if args[0] == "--ls":
        print_workspaces()
        return 0

    if args[0] == "--repos":
        # Output known repos for bash completion (uses cache if available)
        cache = read_completion_cache()
        if cache and "repos" in cache:
            for repo in cache["repos"]:
                print(repo)
        else:
            for repo in get_known_repos():
                print(repo)
        return 0

    if args[0] == "--update-cache":
        # Update completion cache (called in background)
        update_completion_cache()
        return 0

    if args[0] == "--completion-data":
        # Output all completion data as JSON (fast, from cache)
        cache = read_completion_cache()
        if cache:
            print(json.dumps(cache))
        else:
            # No cache, generate and cache it
            data = update_completion_cache()
            print(json.dumps(data))
        return 0

    if args[0] == "--install":
        rc_path = None
        if len(args) > 1:
            rc_path = pathlib.Path(args[1])
        return install_all_completions(rc_path)

    if args[0] == "--stop":
        if len(args) < 2:
            workspace = fuzzy_select_workspace()
            if not workspace:
                logging.error("Usage: dl --stop <workspace>")
                return 1
        else:
            workspace = args[1]
        return workspace_stop(workspace)

    if args[0] == "--rm":
        if len(args) < 2:
            workspace = fuzzy_select_workspace()
            if not workspace:
                logging.error("Usage: dl --rm <workspace>")
                return 1
        else:
            workspace = args[1]
        return workspace_delete(workspace)

    if args[0] == "--status":
        if len(args) < 2:
            workspace = fuzzy_select_workspace()
            if not workspace:
                logging.error("Usage: dl --status <workspace>")
                return 1
        else:
            workspace = args[1]
        return workspace_status(workspace)

    if args[0] == "--code":
        if len(args) < 2:
            workspace = fuzzy_select_workspace()
            if not workspace:
                logging.error("Usage: dl --code <workspace>")
                return 1
        else:
            workspace = args[1]
        result = workspace_up(workspace, ide="vscode")
        return result.returncode

    if args[0] == "--recreate":
        if len(args) < 2:
            workspace = fuzzy_select_workspace()
            if not workspace:
                logging.error("Usage: dl --recreate <workspace>")
                return 1
        else:
            workspace = args[1]
        result = workspace_up(workspace, recreate=True)
        if result.returncode != 0:
            return result.returncode
        return workspace_ssh(workspace)

    if args[0] == "--reset":
        if len(args) < 2:
            workspace = fuzzy_select_workspace()
            if not workspace:
                logging.error("Usage: dl --reset <workspace>")
                return 1
        else:
            workspace = args[1]
        result = workspace_up(workspace, reset=True)
        if result.returncode != 0:
            return result.returncode
        return workspace_ssh(workspace)

    # Default: workspace name and optional command
    raw_spec = args[0]
    command = " ".join(args[1:]) if len(args) > 1 else None

    # Validate the workspace spec
    existing_ids = get_workspace_ids()
    error = validate_workspace_spec(raw_spec, existing_ids)
    if error:
        logging.error(error)
        return 1

    workspace = expand_workspace_spec(raw_spec)

    # Start the workspace
    result = workspace_up(workspace)
    if result.returncode != 0:
        return result.returncode

    # Attach to workspace
    ret = workspace_ssh(workspace, command)

    # Update cache in background after workspace operations
    update_cache_background()

    return ret


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
