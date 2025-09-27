#!/usr/bin/env python3
"""
rockervsc - VS Code integration for rocker containers
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def find_vscode_settings() -> Path:
    """Find VS Code settings directory"""
    # Common VS Code settings locations
    possible_paths = [
        Path.home() / ".vscode",
        Path.home() / ".config" / "Code" / "User",
        Path.home() / "Library" / "Application Support" / "Code" / "User",
        Path.home() / "AppData" / "Roaming" / "Code" / "User",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    # Create default if none found
    default_path = Path.home() / ".vscode"
    default_path.mkdir(exist_ok=True)
    return default_path


def generate_devcontainer_config(workspace_path: Path) -> dict:
    """Generate devcontainer configuration for rocker"""
    return {
        "name": f"Rocker Dev Container - {workspace_path.name}",
        "dockerComposeFile": ["docker-compose.yml"],
        "service": "rocker-dev",
        "workspaceFolder": "/workspace",
        "settings": {
            "terminal.integrated.defaultProfile.linux": "bash"
        },
        "extensions": [
            "ms-python.python",
            "ms-python.pylint",
            "ms-python.black-formatter"
        ],
        "forwardPorts": [],
        "postCreateCommand": "",
        "remoteUser": "developer"
    }


def create_devcontainer(workspace_path: Path) -> None:
    """Create .devcontainer directory and configuration"""
    devcontainer_dir = workspace_path / ".devcontainer"
    devcontainer_dir.mkdir(exist_ok=True)

    # Create devcontainer.json
    config = generate_devcontainer_config(workspace_path)
    devcontainer_file = devcontainer_dir / "devcontainer.json"

    with open(devcontainer_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    logging.info(f"Created devcontainer configuration at {devcontainer_file}")


def setup_vscode_workspace(workspace_path: Path) -> None:
    """Setup VS Code workspace for rocker development"""
    workspace_file = workspace_path / f"{workspace_path.name}.code-workspace"

    workspace_config = {
        "folders": [
            {"path": "."}
        ],
        "settings": {
            "python.defaultInterpreterPath": "/usr/bin/python3",
            "terminal.integrated.cwd": "${workspaceFolder}"
        },
        "extensions": {
            "recommendations": [
                "ms-python.python",
                "ms-vscode-remote.remote-containers"
            ]
        }
    }

    with open(workspace_file, 'w', encoding='utf-8') as f:
        json.dump(workspace_config, f, indent=2)

    logging.info(f"Created VS Code workspace file at {workspace_file}")


def main() -> None:
    """Main entry point for rockervsc"""
    parser = argparse.ArgumentParser(
        description="VS Code integration for rocker containers"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace directory (default: current directory)"
    )
    parser.add_argument(
        "--setup-devcontainer",
        action="store_true",
        help="Setup devcontainer configuration"
    )
    parser.add_argument(
        "--setup-workspace",
        action="store_true",
        help="Setup VS Code workspace file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    workspace_path = args.workspace.resolve()

    if not workspace_path.exists():
        logging.error(f"Workspace directory does not exist: {workspace_path}")
        sys.exit(1)

    logging.info(f"Working with workspace: {workspace_path}")

    if args.setup_devcontainer:
        create_devcontainer(workspace_path)

    if args.setup_workspace:
        setup_vscode_workspace(workspace_path)

    if not args.setup_devcontainer and not args.setup_workspace:
        logging.info("No action specified. Use --help for available options.")
        logging.info("Available actions:")
        logging.info("  --setup-devcontainer: Create devcontainer configuration")
        logging.info("  --setup-workspace: Create VS Code workspace file")


if __name__ == "__main__":
    main()