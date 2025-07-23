#!/usr/bin/env python3
"""
Rocker Environment (renv) - Workspace management tool for rockerc repositories.
"""

import argparse
import subprocess
import os
from pathlib import Path
import shlex

from . import rockerc

# Version number - increment when making changes
__version__ = "1.3.0"


class RenvManager:
    """Manages git worktrees for different codebases with rockerc integration."""

    def __init__(self, repo_root=None, renv_home=None):
        # Get renv home directory first
        if renv_home:
            self.renv_home = Path(renv_home).expanduser().resolve()
        else:
            self.renv_home = self._get_renv_home()

        # Always use renv_home as the repo root for git operations
        if repo_root is None:
            repo_root = self.renv_home

        self.repo_root = Path(repo_root).resolve()
        self.worktrees_dir = self.renv_home

        # Initialize git repository in renv_home if it doesn't exist
        self._ensure_git_repo()

    def _get_renv_home(self):
        """Get the renv home directory from environment or default."""
        renv_home = os.environ.get("RENV_HOME")
        if renv_home:
            return Path(renv_home).expanduser().resolve()
        return Path.home() / "renv"

    def _set_renv_home(self, path):
        """Set the RENV_HOME environment variable in bashrc."""
        renv_path = Path(path).expanduser().resolve()
        renv_path.mkdir(parents=True, exist_ok=True)

        bashrc_path = Path.home() / ".bashrc"
        export_line = f"export RENV_HOME={renv_path}\n"

        # Check if RENV_HOME is already set in bashrc
        if bashrc_path.exists():
            with open(bashrc_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Remove existing RENV_HOME lines
            lines = content.split("\n")
            new_lines = [line for line in lines if not line.strip().startswith("export RENV_HOME=")]

            # Add new RENV_HOME line
            new_lines.append(export_line.strip())

            with open(bashrc_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
        else:
            # Create bashrc if it doesn't exist
            with open(bashrc_path, "w", encoding="utf-8") as f:
                f.write(export_line)

        print(f"RENV_HOME set to: {renv_path}")
        print(f"Added to {bashrc_path}")
        print("Run 'source ~/.bashrc' or restart your terminal to apply changes.")

        return renv_path

    def _run_git_command(self, cmd, cwd=None):
        """Run a git command and return the result."""
        if cwd is None:
            cwd = self.repo_root

        full_cmd = ["git"] + cmd
        print(f"Running: {' '.join(full_cmd)} (in {cwd})")

        try:
            result = subprocess.run(full_cmd, cwd=cwd, capture_output=True, text=True, check=True)
            return result
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            raise

    def _run_rockerc_command(self, cwd):
        """Run rockerc in the specified directory."""
        try:
            # Collect rockerc arguments from the workspace
            args_dict = rockerc.collect_arguments(str(cwd))
            if not args_dict:
                print(f"No rockerc.yaml found in {cwd}")
                return False

            # Convert to rocker command arguments
            args_str = rockerc.yaml_dict_to_args(args_dict)

            # Run rocker with the arguments
            cmd = f"rocker {args_str}"
            print(f"Running rockerc in {cwd}: {cmd}")

            # Use shlex to properly parse the command
            cmd_list = shlex.split(cmd)

            subprocess.run(cmd_list, cwd=cwd, check=True)
            return True

        except Exception as e:
            print(f"Failed to run rockerc in {cwd}: {e}")
            return False

    def parse_repo_spec(self, repo_spec):
        """Parse repo specification in format: repo_name[:branch[:folder_in_repo]]

        If branch is not specified, defaults to 'main'.
        Examples:
        - blooop/bencher -> repo=blooop/bencher, branch=main
        - blooop/bencher:develop -> repo=blooop/bencher, branch=develop
        - blooop/bencher:main:src -> repo=blooop/bencher, branch=main, folder=src
        """
        parts = repo_spec.split(":")

        repo_name = parts[0]
        branch = parts[1] if len(parts) > 1 and parts[1] else "main"
        folder_in_repo = parts[2] if len(parts) > 2 else None

        return repo_name, branch, folder_in_repo

    def _get_existing_branches(self):
        """Get list of existing local branches."""
        result = self._run_git_command(["branch", "--format=%(refname:short)"])
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    def _get_existing_worktrees(self):
        """Get list of existing worktrees."""
        try:
            result = self._run_git_command(["worktree", "list", "--porcelain"])
            worktrees = []
            for line in result.stdout.strip().split("\n"):
                if line.startswith("worktree "):
                    worktree_path = line.replace("worktree ", "")
                    worktree_name = Path(worktree_path).name
                    if worktree_name != self.repo_root.name:  # Skip main worktree
                        worktrees.append(worktree_name)
            return worktrees
        except subprocess.CalledProcessError:
            return []

    def _ensure_git_repo(self):
        """Ensure git repository exists in renv_home, create if needed."""
        self.renv_home.mkdir(parents=True, exist_ok=True)

        if not (self.repo_root / ".git").exists():
            print(f"Initializing git repository in {self.repo_root}")
            try:
                subprocess.run(["git", "init"], cwd=self.repo_root, check=True, capture_output=True)
                # Set up minimal git config for this repo
                subprocess.run(
                    ["git", "config", "user.email", "renv@example.com"],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "config", "user.name", "Renv"],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )
                # Create initial commit to avoid issues with worktrees
                subprocess.run(
                    ["git", "commit", "--allow-empty", "-m", "Initial commit"],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to initialize git repository: {e}") from e

    def generate_workspace_name(self, repo_name, branch):
        """Generate a workspace name that is both a valid folder name and git branch name.
        
        Git branch name restrictions:
        - No spaces, control characters
        - No consecutive dots  
        - Cannot start/end with slash
        - Cannot contain ~, ^, :, ?, *, [, \
        - Cannot end with .lock
        """
        # Extract just the repo name without org/user prefix
        if "/" in repo_name:
            repo_name = repo_name.split("/")[-1]

        # Remove .git suffix if present
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        # Sanitize repo name for git branch and folder names
        # Replace invalid characters with hyphens, then normalize
        safe_repo = repo_name
        for char in "~^:?*[\\. /":
            safe_repo = safe_repo.replace(char, "-")

        # Sanitize branch name similarly
        safe_branch = branch
        for char in "~^:?*[\\. /":
            safe_branch = safe_branch.replace(char, "-")

        # Remove consecutive hyphens and normalize
        import re

        safe_repo = re.sub(r"-+", "-", safe_repo).strip("-")
        safe_branch = re.sub(r"-+", "-", safe_branch).strip("-")

        # Ensure names don't start with hyphen or dot (git restriction)
        if safe_repo.startswith(("-", ".")):
            safe_repo = "repo-" + safe_repo.lstrip("-.")
        if safe_branch.startswith(("-", ".")):
            safe_branch = "branch-" + safe_branch.lstrip("-.")

        # Generate final name
        if safe_branch == "main":
            # For main branch, just use repo name to keep it clean
            workspace_name = safe_repo
        else:
            workspace_name = f"{safe_repo}-{safe_branch}"

        # Ensure it doesn't end with .lock (git restriction)
        if workspace_name.endswith(".lock"):
            workspace_name = workspace_name[:-5] + "-lock"

        return workspace_name

    def install(self, path=None):
        """Install and configure renv home directory."""
        if path is None:
            path = self.renv_home
        else:
            path = Path(path).expanduser().resolve()

        # Update renv_home and ensure git repo exists there
        self.renv_home = path
        self.repo_root = path
        self.worktrees_dir = path

        # Set up the directory and git repo
        self._ensure_git_repo()
        self._set_renv_home(path)

        print(f"Renv installation complete. Home directory: {self.renv_home}")

    def add_workspace(self, repo_spec, workspace_name=None, run_rockerc=True):
        """Add a new workspace by cloning a repo/branch and creating a worktree."""
        repo_name, remote_branch, folder_in_repo = self.parse_repo_spec(repo_spec)

        # Auto-generate workspace name if not provided
        if workspace_name is None:
            workspace_name = self.generate_workspace_name(repo_name, remote_branch)
            print(f"Auto-generated workspace name: {workspace_name}")

        # Generate a safe branch name (replace invalid characters)
        branch_name = workspace_name.replace(":", "_").replace("/", "_")

        # Check if branch already exists
        existing_branches = self._get_existing_branches()
        if branch_name in existing_branches:
            print(
                f"Branch '{branch_name}' already exists. Use 'renv open {workspace_name}' to open it."
            )
            return

        # Ensure worktrees directory exists
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        worktree_path = self.worktrees_dir / workspace_name

        # Check if worktree directory already exists
        if worktree_path.exists():
            print(f"Worktree directory '{worktree_path}' already exists.")
            return

        try:
            # Sanitize remote name (replace slashes with underscores)
            sanitized_remote_name = repo_name.replace("/", "_").replace(":", "_")

            # Add remote if it doesn't exist
            try:
                self._run_git_command(["remote", "get-url", sanitized_remote_name])
                print(f"Remote '{sanitized_remote_name}' already exists")
            except subprocess.CalledProcessError:
                # Assume repo_name is a URL if it contains :// or @
                if "://" in repo_name or "@" in repo_name:
                    remote_url = repo_name
                else:
                    # Try common git hosting patterns
                    if "/" in repo_name:
                        remote_url = f"https://github.com/{repo_name}.git"
                    else:
                        raise ValueError(f"Cannot determine remote URL for: {repo_name}") from None

                print(f"Adding remote '{sanitized_remote_name}' -> '{remote_url}'")
                self._run_git_command(["remote", "add", sanitized_remote_name, remote_url])

            # Fetch from the remote
            print(f"Fetching from remote '{sanitized_remote_name}'")
            self._run_git_command(["fetch", sanitized_remote_name])

            # Create new branch tracking the remote branch
            remote_ref = f"{sanitized_remote_name}/{remote_branch}"
            print(f"Creating branch '{branch_name}' from '{remote_ref}'")
            self._run_git_command(["branch", branch_name, remote_ref])

            # Create worktree
            print(f"Creating worktree at '{worktree_path}'")
            self._run_git_command(["worktree", "add", str(worktree_path), branch_name])

            # Handle folder filtering if specified
            if folder_in_repo:
                target_path = worktree_path / folder_in_repo
                if target_path.exists():
                    print(f"Target folder '{folder_in_repo}' found at: {target_path}")
                    worktree_path = target_path
                else:
                    print(f"Warning: Folder '{folder_in_repo}' not found in repository")

            print(f"Workspace '{workspace_name}' created successfully at: {worktree_path}")

            # Run rockerc if requested and rockerc.yaml exists
            if run_rockerc:
                rockerc_file = worktree_path / "rockerc.yaml"
                if rockerc_file.exists():
                    print("Found rockerc.yaml, running rockerc...")
                    self._run_rockerc_command(worktree_path)
                else:
                    print("No rockerc.yaml found in workspace, skipping rockerc execution")

            print(f"To open in VS Code, run: code {worktree_path}")

        except subprocess.CalledProcessError as e:
            print(f"Failed to create workspace: {e}")
            # Clean up on failure
            if worktree_path.exists():
                self._run_git_command(["worktree", "remove", str(worktree_path)])
            try:
                self._run_git_command(["branch", "-D", branch_name])
            except subprocess.CalledProcessError:
                pass  # Branch might not have been created
            raise

    def open_workspace(self, workspace_name):
        """Open an existing workspace worktree."""
        worktree_path = self.worktrees_dir / workspace_name

        # Check if worktree exists
        if not worktree_path.exists():
            existing_worktrees = self._get_existing_worktrees()
            print(f"Worktree '{workspace_name}' not found.")
            if existing_worktrees:
                print("Available worktrees:")
                for wt in existing_worktrees:
                    print(f"  - {wt}")
            else:
                print("No worktrees found. Use 'renv add' to create one.")
            return

        # Open in VS Code
        print(f"Opening workspace '{workspace_name}' in VS Code...")
        try:
            subprocess.run(["code", str(worktree_path)], check=True)
        except subprocess.CalledProcessError:
            print(f"Failed to open VS Code. You can manually navigate to: {worktree_path}")
        except FileNotFoundError:
            print(f"VS Code not found in PATH. You can manually navigate to: {worktree_path}")

    def run_workspace(self, workspace_name):
        """Run rockerc in an existing workspace."""
        worktree_path = self.worktrees_dir / workspace_name

        if not worktree_path.exists():
            print(f"Workspace '{workspace_name}' not found.")
            return

        print(f"Running rockerc in workspace '{workspace_name}'...")
        success = self._run_rockerc_command(worktree_path)
        if not success:
            print("Failed to run rockerc in workspace")

    def list_workspaces(self):
        """List all available workspaces."""
        if not self.worktrees_dir.exists():
            print(f"Renv home directory not found: {self.worktrees_dir}")
            print("Run 'renv install' to set up renv.")
            return

        # Filter out .git directory and only include actual workspaces
        workspaces = [d for d in self.worktrees_dir.iterdir() if d.is_dir() and d.name != ".git"]

        if not workspaces:
            print("No workspaces found.")
            return

        print(f"Available workspaces (in {self.worktrees_dir}):")
        for ws in workspaces:
            rockerc_file = ws / "rockerc.yaml"
            has_rockerc = "✓" if rockerc_file.exists() else "✗"
            print(f"  - {ws.name} ({ws}) [rockerc: {has_rockerc}]")

    def remove_workspace(self, workspace_name):
        """Remove a workspace and its associated branch."""
        worktree_path = self.worktrees_dir / workspace_name

        if not worktree_path.exists():
            print(f"Workspace '{workspace_name}' not found.")
            return

        # Confirm removal
        response = input(f"Are you sure you want to remove workspace '{workspace_name}'? [y/N]: ")
        if response.lower() != "y":
            print("Cancelled.")
            return

        try:
            # Remove worktree
            print(f"Removing worktree '{workspace_name}'...")
            self._run_git_command(["worktree", "remove", str(worktree_path)])

            # Remove branch
            print(f"Removing branch '{workspace_name}'...")
            self._run_git_command(["branch", "-D", workspace_name])

            print(f"Workspace '{workspace_name}' removed successfully.")

        except subprocess.CalledProcessError as e:
            print(f"Failed to remove workspace: {e}")

    def is_repo_spec(self, target):
        """Determine if target looks like a repo specification.

        Repo specs can be:
        - user/repo (defaults to main branch)
        - user/repo:branch
        - https://github.com/user/repo.git
        - https://github.com/user/repo.git:branch

        Not repo specs:
        - plain workspace names (no slashes, no dots, no protocol)
        - file paths (start with / or ~)
        """
        # File paths are not repo specs
        if target.startswith("/") or target.startswith("~"):
            return False

        # If it contains a protocol (http, git, ssh), it's a repo
        if "://" in target:
            return True

        # If it contains a slash, it's likely user/repo format
        if "/" in target:
            return True

        # If it ends with .git, it's a repo
        if target.endswith(".git"):
            return True

        # Otherwise, treat as workspace name
        return False


def main():
    """Main entry point for the renv tool."""
    # First, try to parse just to see if we have a command
    import sys

    # Check if first argument (after script name) is a known command
    known_commands = {"install", "add", "open", "run", "list", "remove"}

    if len(sys.argv) > 1 and sys.argv[1] in known_commands:
        # Use normal subcommand parsing
        parser = argparse.ArgumentParser(
            description=f"Rocker Environment (renv) v{__version__} - Workspace management tool for rockerc repositories",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  renv bencher_main                                     # Open workspace (or add repo if format matches)
  renv blooop/bencher:main                             # Add repo and open workspace
  renv install                                          # Set up renv home directory
  renv install ~/my-renv                               # Set up renv in custom location
  renv add https://github.com/user/repo.git:main my-workspace
  renv add user/repo:develop:src/package my-dev-workspace
  renv open my-workspace                               # Open workspace in VS Code
  renv run my-workspace                                # Run rockerc in workspace
  renv list                                            # List all workspaces
  renv remove my-workspace                             # Remove workspace
            """,
        )

        # Add version argument
        parser.add_argument("--version", action="version", version=f"renv {__version__}")

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Install command
        install_parser = subparsers.add_parser("install", help="Set up renv home directory")
        install_parser.add_argument(
            "path", nargs="?", help="Custom path for renv home directory (default: ~/renv)"
        )

        # Add command
        add_parser = subparsers.add_parser("add", help="Add a new workspace")
        add_parser.add_argument(
            "repo_spec", help="Repository specification: repo_name:branch[:folder_in_repo]"
        )
        add_parser.add_argument(
            "workspace_name",
            nargs="?",
            help="Name for the new workspace (auto-generated if not provided)",
        )
        add_parser.add_argument(
            "--no-rockerc",
            action="store_true",
            help="Skip running rockerc after creating workspace",
        )

        # Open command
        open_parser = subparsers.add_parser("open", help="Open an existing workspace")
        open_parser.add_argument("workspace_name", help="Name of the workspace to open")

        # Run command
        run_parser = subparsers.add_parser("run", help="Run rockerc in an existing workspace")
        run_parser.add_argument("workspace_name", help="Name of the workspace to run rockerc in")

        # List command
        subparsers.add_parser("list", help="List all available workspaces")

        # Remove command
        remove_parser = subparsers.add_parser("remove", help="Remove a workspace")
        remove_parser.add_argument("workspace_name", help="Name of the workspace to remove")

        args = parser.parse_args()

        # Handle explicit commands
        try:
            if args.command == "install":
                # For install command, create manager with the target renv home
                install_path = args.path if args.path else Path.home() / "renv"
                manager = RenvManager(renv_home=install_path)
                manager.install(args.path)
            else:
                manager = RenvManager()

                if args.command == "add":
                    run_rockerc = not args.no_rockerc
                    manager.add_workspace(args.repo_spec, args.workspace_name, run_rockerc)
                elif args.command == "open":
                    manager.open_workspace(args.workspace_name)
                elif args.command == "run":
                    manager.run_workspace(args.workspace_name)
                elif args.command == "list":
                    manager.list_workspaces()
                elif args.command == "remove":
                    manager.remove_workspace(args.workspace_name)

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        # Handle default behavior (target as first argument)
        parser = argparse.ArgumentParser(
            description=f"Rocker Environment (renv) v{__version__} - Workspace management tool for rockerc repositories",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  renv bencher_main                                     # Open workspace (or add repo if format matches)
  renv blooop/bencher:main                             # Add repo and open workspace
  renv install                                          # Set up renv home directory
  renv install ~/my-renv                               # Set up renv in custom location
  renv add https://github.com/user/repo.git:main my-workspace
  renv add user/repo:develop:src/package my-dev-workspace
  renv open my-workspace                               # Open workspace in VS Code
  renv run my-workspace                                # Run rockerc in workspace
  renv list                                            # List all workspaces
  renv remove my-workspace                             # Remove workspace
            """,
        )

        # Add version argument
        parser.add_argument("--version", action="version", version=f"renv {__version__}")

        # Add positional argument for target
        parser.add_argument(
            "target",
            nargs="?",
            help="Workspace name to open, or repo specification to add (repo_name:branch[:folder])",
        )

        args = parser.parse_args()

        # Handle default behavior when no command is specified
        if args.target:
            try:
                # Auto-setup renv if not initialized
                try:
                    manager = RenvManager()
                except RuntimeError:
                    print("Renv not initialized. Setting up...")
                    manager = RenvManager(renv_home=Path.home() / "renv")
                    manager.install()

                # Always treat target as repo spec for default command
                # This ensures `renv user/repo` always works
                if manager.is_repo_spec(args.target):
                    # Target is a repo spec, add it (or update if exists) and open
                    print(f"Setting up workspace for: {args.target}")
                    repo_name, branch, _ = manager.parse_repo_spec(args.target)
                    workspace_name = manager.generate_workspace_name(repo_name, branch)

                    # Check if workspace already exists
                    worktree_path = manager.worktrees_dir / workspace_name
                    if worktree_path.exists():
                        print(f"Workspace '{workspace_name}' already exists. Opening...")
                        manager.open_workspace(workspace_name)
                    else:
                        print(f"Creating new workspace: {workspace_name}")
                        manager.add_workspace(args.target, workspace_name)
                        manager.open_workspace(workspace_name)
                else:
                    # Target looks like a workspace name, try to open it
                    print(f"Opening workspace: {args.target}")
                    manager.open_workspace(args.target)

            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
