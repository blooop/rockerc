"""
worktree_docker - Development environment launcher using Docker, Git worktrees, and Buildx/Bake

A tool that combines git worktrees with Docker Compose and Buildx to provide
isolated development environments for each repository branch.
"""

import sys
import subprocess
import logging
import argparse
import time
import json
import yaml
import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from .completion_scripts import bash_completion, zsh_completion, fish_completion


@dataclass
class RepoSpec:
    """Repository specification parser and container."""

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

    @property
    def compose_project_name(self) -> str:
        """Generate Docker Compose project name."""
        safe_branch = self.branch.replace("/", "-").replace("_", "-")
        return f"{self.repo}-{safe_branch}"


@dataclass
class Extension:
    """Represents a worktree_docker extension with its configuration."""

    name: str
    dockerfile_content: str
    compose_fragment: Dict[str, Any]
    files: Dict[str, str] = field(default_factory=dict)  # Additional files to copy

    @property
    def hash(self) -> str:
        """Generate SHA256 hash for cache tagging."""
        content = f"{self.dockerfile_content}{json.dumps(self.compose_fragment, sort_keys=True)}"
        for filename, file_content in sorted(self.files.items()):
            content += f"{filename}:{file_content}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]


class worktree_dockerConfig:
    """Manages worktree_docker configuration from .worktree_docker.yml/.worktree_docker.json files."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from repo directory."""
        for config_file in [
            ".worktree_docker.yml",
            ".worktree_docker.yaml",
            ".worktree_docker.json",
        ]:
            config_path = self.repo_path / config_file
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        if config_file.endswith(".json"):
                            return json.load(f)
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    logging.warning(f"Failed to load {config_file}: {e}")
        return {}

    @property
    def extensions(self) -> List[str]:
        """Get list of default extensions."""
        return self.config.get("extensions", [])

    @property
    def base_image(self) -> str:
        """Get base image for containers."""
        return self.config.get("base_image", "ubuntu:22.04")

    @property
    def platforms(self) -> List[str]:
        """Get target platforms for multi-arch builds."""
        return self.config.get("platforms", ["linux/amd64"])


class ExtensionManager:
    """Manages extensions and their definitions."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.extensions_dir = cache_dir / "extensions"
        self.extensions_dir.mkdir(parents=True, exist_ok=True)
        self._builtin_extensions = self._load_builtin_extensions()

    def _load_builtin_extensions(self) -> Dict[str, Extension]:
        """Load built-in extension definitions."""
        extensions = {}

        # Base development tools
        extensions["base"] = Extension(
            name="base",
            dockerfile_content="""
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \\
    git curl wget unzip build-essential \\
    ca-certificates gnupg lsb-release \\
    && rm -rf /var/lib/apt/lists/*
""",
            compose_fragment={},
        )

        # Git configuration
        extensions["git"] = Extension(
            name="git",
            dockerfile_content="""
# Git is already installed in base, just configure
RUN git config --global --add safe.directory '*'
""",
            compose_fragment={
                "volumes": [
                    "~/.gitconfig:/home/worktree_docker/.gitconfig:ro",
                    "~/.ssh:/home/worktree_docker/.ssh:ro",
                ]
            },
        )

        # User setup
        extensions["user"] = Extension(
            name="user",
            dockerfile_content="""
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} worktree_docker && \\
    useradd -u ${USER_ID} -g worktree_docker -m -s /bin/bash worktree_docker && \\
    echo 'worktree_docker ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER worktree_docker
WORKDIR /workspace
""",
            compose_fragment={
                "build": {"args": {"USER_ID": "${USER_ID:-1000}", "GROUP_ID": "${GROUP_ID:-1000}"}},
                "environment": {"USER": "worktree_docker", "HOME": "/home/worktree_docker"},
            },
        )

        # X11 GUI support
        extensions["x11"] = Extension(
            name="x11",
            dockerfile_content="""
RUN apt-get update && apt-get install -y \\
    xauth x11-apps libgl1-mesa-glx libgl1-mesa-dri \\
    && rm -rf /var/lib/apt/lists/*
""",
            compose_fragment={
                "environment": {"DISPLAY": "${DISPLAY}", "XAUTHORITY": "/tmp/.Xauth"},
                "volumes": ["/tmp/.X11-unix:/tmp/.X11-unix:rw", "/tmp/.Xauth:/tmp/.Xauth:rw"],
                "network_mode": "host",
            },
        )

        # NVIDIA GPU support
        extensions["nvidia"] = Extension(
            name="nvidia",
            dockerfile_content="""
# NVIDIA runtime will be handled by Docker Compose
""",
            compose_fragment={
                "runtime": "nvidia",
                "environment": {
                    "NVIDIA_VISIBLE_DEVICES": "all",
                    "NVIDIA_DRIVER_CAPABILITIES": "all",
                },
            },
        )

        # Python/UV package manager
        extensions["uv"] = Extension(
            name="uv",
            dockerfile_content="""
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \\
    mv /root/.local/bin/uv /usr/local/bin/uv && \\
    mv /root/.local/bin/uvx /usr/local/bin/uvx
""",
            compose_fragment={},
        )

        # Pixi package manager
        extensions["pixi"] = Extension(
            name="pixi",
            dockerfile_content="""
# Install pixi as the worktree_docker user if user exists, otherwise as root
RUN if id worktree_docker >/dev/null 2>&1; then \\
        su - worktree_docker -c "curl -fsSL https://pixi.sh/install.sh | bash"; \\
    else \\
        curl -fsSL https://pixi.sh/install.sh | bash; \\
    fi
# Add pixi to PATH for both root and worktree_docker user
ENV PATH="/root/.pixi/bin:/home/worktree_docker/.pixi/bin:$PATH"
""",
            compose_fragment={},
        )

        # Fuzzy finder
        extensions["fzf"] = Extension(
            name="fzf",
            dockerfile_content="""
RUN git clone --depth 1 https://github.com/junegunn/fzf.git /home/worktree_docker/.fzf && \\
    chown -R worktree_docker:worktree_docker /home/worktree_docker/.fzf && \\
    /home/worktree_docker/.fzf/install --all
""",
            compose_fragment={},
        )

        return extensions

    def get_extension(self, name: str, repo_path: Optional[Path] = None) -> Optional[Extension]:
        """Get extension by name, checking repo-local first, then built-in."""
        # Check repo-local extensions first
        if repo_path:
            local_ext_dir = repo_path / ".worktree_docker" / "exts" / name
            if local_ext_dir.exists():
                return self._load_local_extension(name, local_ext_dir)

        # Check built-in extensions
        return self._builtin_extensions.get(name)

    def _load_local_extension(self, name: str, ext_dir: Path) -> Extension:
        """Load extension from local repository directory."""
        dockerfile_path = ext_dir / "Dockerfile"
        compose_path = ext_dir / "docker-compose.fragment.yml"

        dockerfile_content = ""
        if dockerfile_path.exists():
            dockerfile_content = dockerfile_path.read_text(encoding="utf-8")

        compose_fragment = {}
        if compose_path.exists():
            with open(compose_path, "r", encoding="utf-8") as f:
                compose_fragment = yaml.safe_load(f) or {}

        # Load any additional files
        files = {}
        for file_path in ext_dir.glob("*"):
            if file_path.name not in ["Dockerfile", "docker-compose.fragment.yml"]:
                files[file_path.name] = file_path.read_text(encoding="utf-8")

        return Extension(
            name=name,
            dockerfile_content=dockerfile_content,
            compose_fragment=compose_fragment,
            files=files,
        )

    def list_extensions(self, repo_path: Optional[Path] = None) -> List[str]:
        """List all available extensions."""
        extensions = set(self._builtin_extensions.keys())

        if repo_path:
            local_exts_dir = repo_path / ".worktree_docker" / "exts"
            if local_exts_dir.exists():
                extensions.update(d.name for d in local_exts_dir.iterdir() if d.is_dir())

        return sorted(extensions)


def get_cache_dir() -> Path:
    """Get worktree_docker cache directory."""
    cache_dir = os.getenv("worktree_docker_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir)
    return Path.home() / ".worktree_docker"


def get_workspaces_dir() -> Path:
    """Get workspaces directory."""
    return get_cache_dir() / "workspaces"


def get_build_cache_dir(repo_spec: RepoSpec) -> Path:
    """Get build cache directory for a specific repo spec."""
    safe_branch = repo_spec.branch.replace("/", "-")
    return get_cache_dir() / "builds" / repo_spec.owner / repo_spec.repo / safe_branch


def get_repo_dir(repo_spec: RepoSpec) -> Path:
    """Get bare repository directory."""
    return get_workspaces_dir() / repo_spec.owner / repo_spec.repo


def get_worktree_dir(repo_spec: RepoSpec) -> Path:
    """Get worktree directory for a specific branch."""
    safe_branch = repo_spec.branch.replace("/", "-")
    return get_repo_dir(repo_spec) / f"worktree-{safe_branch}"


def auto_detect_extensions(repo_path: Path) -> List[str]:
    """Auto-detect extensions based on files present in the repository."""
    detected_extensions = []

    # Extension detection patterns: (file_pattern, extension_name)
    detection_patterns = [
        (r"^pixi\.toml$", "pixi"),
        (r"^pyproject\.toml$", "uv"),
        (r"^package\.json$", "uv"),  # Could use uv for Node.js too
        (r"^Cargo\.toml$", "uv"),  # Rust projects can benefit from uv
        (r"^poetry\.lock$", "uv"),
        (r"^requirements.*\.txt$", "uv"),
        (r"^\.python-version$", "uv"),
        (r"^environment\.ya?ml$", "uv"),  # conda env files
        (r"^conda\.ya?ml$", "uv"),
        (r"^Dockerfile$", "base"),
        (r"^docker-compose\.ya?ml$", "base"),
    ]

    try:
        # Get all files in the repository root
        if not repo_path.exists():
            return detected_extensions

        for item in repo_path.iterdir():
            if item.is_file():
                filename = item.name
                for pattern, extension in detection_patterns:
                    if re.match(pattern, filename, re.IGNORECASE):
                        if extension not in detected_extensions:
                            detected_extensions.append(extension)
                            logging.info(
                                f"Auto-detected extension '{extension}' from file '{filename}'"
                            )

    except Exception as e:
        logging.warning(f"Failed to auto-detect extensions: {e}")

    return detected_extensions


def setup_bare_repo(repo_spec: RepoSpec) -> Path:
    """Clone or update bare repository."""
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


def setup_worktree(repo_spec: RepoSpec) -> Path:
    """Set up git worktree for the specified branch."""
    repo_dir = get_repo_dir(repo_spec)
    worktree_dir = get_worktree_dir(repo_spec)

    # Ensure bare repo exists
    setup_bare_repo(repo_spec)

    if not worktree_dir.exists():
        logging.info(f"Creating worktree for branch: {repo_spec.branch}")

        # Check if branch exists, if not create it
        try:
            # Try to create worktree with existing branch
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_dir),
                    "worktree",
                    "add",
                    str(worktree_dir),
                    repo_spec.branch,
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            # Branch doesn't exist, create new branch and worktree
            logging.info(f"Branch {repo_spec.branch} doesn't exist, creating new branch")
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_dir),
                    "worktree",
                    "add",
                    "-b",
                    repo_spec.branch,
                    str(worktree_dir),
                ],
                check=True,
            )

        time.sleep(0.1)  # Allow filesystem to sync
    else:
        logging.info(f"Worktree already exists: {worktree_dir}")

    return worktree_dir


def ensure_buildx_builder(builder_name: str = "worktree_docker_builder") -> bool:
    """Ensure Buildx builder exists and is active."""
    try:
        # Check if builder exists
        result = subprocess.run(
            ["docker", "buildx", "inspect", builder_name],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # Create builder
            logging.info(f"Creating Buildx builder: {builder_name}")
            subprocess.run(
                [
                    "docker",
                    "buildx",
                    "create",
                    "--name",
                    builder_name,
                    "--driver",
                    "docker-container",
                    "--use",
                ],
                check=True,
            )
        else:
            # Use existing builder
            subprocess.run(["docker", "buildx", "use", builder_name], check=True)

        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to set up Buildx builder: {e}")
        return False


def generate_dockerfile(extensions: List[Extension], base_image: str, build_dir: Path) -> str:
    """Generate Dockerfile combining all extensions."""
    lines = [f"FROM {base_image} as base"]

    # Add each extension's Dockerfile content
    for ext in extensions:
        if ext.dockerfile_content.strip():
            lines.append(f"\n# Extension: {ext.name}")
            lines.append(ext.dockerfile_content.strip())

    # Ensure we end up in the right working directory
    lines.append("\nWORKDIR /workspace")
    lines.append('CMD ["bash"]')

    dockerfile_content = "\n".join(lines)

    # Ensure build directory exists
    build_dir.mkdir(parents=True, exist_ok=True)

    # Write Dockerfile to build directory
    dockerfile_path = build_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content, encoding="utf-8")

    return dockerfile_content


@dataclass
class ComposeConfig:
    """Configuration for generating compose files."""

    repo_spec: RepoSpec
    extensions: List[Extension]
    image_name: str
    work_dir: Path
    worktree_dir: Path
    repo_dir: Path
    build_dir: Optional[Path] = None


def generate_compose_file(config: ComposeConfig) -> Dict[str, Any]:
    """Generate docker-compose.yml for the environment."""
    # For git worktrees, we need to mount the worktree git metadata directory as well
    safe_branch = config.repo_spec.branch.replace("/", "-")
    worktree_git_dir = config.repo_dir / "worktrees" / f"worktree-{safe_branch}"

    # Start with base service
    service = {
        "image": config.image_name,
        "container_name": config.repo_spec.compose_project_name,
        "hostname": config.repo_spec.compose_project_name,
        "working_dir": f"/workspace/{config.repo_spec.repo}",
        "volumes": [
            f"{config.worktree_dir}:/workspace/{config.repo_spec.repo}",
            f"{config.repo_dir}:/workspace/{config.repo_spec.repo}.git",
            f"{worktree_git_dir}:/workspace/{config.repo_spec.repo}.git/worktrees/worktree-{safe_branch}",
        ],
        "environment": {
            "REPO_NAME": config.repo_spec.repo,
            "BRANCH_NAME": config.repo_spec.branch.replace("/", "-"),
        },
        "labels": {"worktree_docker.managed": "true"},
        "stdin_open": True,
        "tty": True,
        "command": ["tail", "-f", "/dev/null"],
    }

    # Apply subfolder if specified
    if config.repo_spec.subfolder:
        service["working_dir"] = f"/workspace/{config.repo_spec.repo}/{config.repo_spec.subfolder}"

    # Merge extension compose fragments
    for ext in config.extensions:
        fragment = ext.compose_fragment
        if not fragment:
            continue

        # Merge volumes
        if "volumes" in fragment:
            service.setdefault("volumes", []).extend(fragment["volumes"])

        # Merge environment
        if "environment" in fragment:
            service.setdefault("environment", {}).update(fragment["environment"])

        # Set runtime if specified
        if "runtime" in fragment:
            service["runtime"] = fragment["runtime"]

        # Set network mode if specified
        if "network_mode" in fragment:
            service["network_mode"] = fragment["network_mode"]

        # Merge build args if specified
        if "build" in fragment:
            if "build" not in service:
                service["build"] = {"context": ".", "dockerfile": "Dockerfile"}
            if "args" in fragment["build"]:
                service["build"].setdefault("args", {}).update(fragment["build"]["args"])

    # If we have build args, enable building
    if any(ext.compose_fragment.get("build", {}).get("args") for ext in config.extensions):
        service["build"] = service.get("build", {"context": ".", "dockerfile": "Dockerfile"})

    compose_config = {"services": {"dev": service}}

    # Write compose file to build directory to keep worktree clean
    # Use work_dir as fallback for cases where we don't have a separate build dir
    compose_dir = config.build_dir if config.build_dir is not None else config.work_dir
    if config.build_dir is not None:
        config.build_dir.mkdir(parents=True, exist_ok=True)

    compose_path = compose_dir / "docker-compose.yml"
    with open(compose_path, "w", encoding="utf-8") as f:
        yaml.dump(compose_config, f, default_flow_style=False)

    return compose_config


def generate_bake_file(
    extensions: List[Extension], base_image: str, platforms: List[str], build_dir: Path
) -> str:
    """Generate docker-bake.hcl file for Buildx."""
    # Create targets for each extension layer
    targets = []

    # Convert platforms list to proper HCL array syntax
    platforms_hcl = "[" + ", ".join(f'"{platform}"' for platform in platforms) + "]"

    current_image = base_image
    for ext in extensions:
        if not ext.dockerfile_content.strip():
            continue

        target_name = f"ext-{ext.name}"
        target = f"""
target "{target_name}" {{
    context = "."
    dockerfile = "Dockerfile.{ext.name}"
    tags = ["worktree_docker/{ext.name}:{ext.hash}"]
    platforms = {platforms_hcl}
    cache-from = ["type=local,src=.buildx-cache"]
    cache-to = ["type=local,dest=.buildx-cache,mode=max"]
}}"""
        targets.append(target)

        # Ensure build directory exists
        build_dir.mkdir(parents=True, exist_ok=True)

        # Write individual Dockerfile for this extension
        ext_dockerfile = f"FROM {current_image}\n{ext.dockerfile_content}"
        dockerfile_path = build_dir / f"Dockerfile.{ext.name}"
        dockerfile_path.write_text(ext_dockerfile, encoding="utf-8")

        current_image = f"worktree_docker/{ext.name}:{ext.hash}"

    # Final target combining all extensions
    final_target = f"""
target "final" {{
    context = "."
    dockerfile = "Dockerfile"
    tags = ["worktree_docker/final:{'-'.join(ext.hash for ext in extensions)}"]
    platforms = {platforms_hcl}
    cache-from = ["type=local,src=.buildx-cache"]
    cache-to = ["type=local,dest=.buildx-cache,mode=max"]
}}"""
    targets.append(final_target)

    bake_content = "\n".join(targets)

    # Write bake file
    bake_path = build_dir / "docker-bake.hcl"
    bake_path.write_text(bake_content, encoding="utf-8")

    return bake_content


def should_rebuild_image(
    image_name: str, extensions: List[Extension]  # pylint: disable=unused-argument
) -> bool:
    """Check if image needs rebuilding based on extension hashes."""
    try:
        # Check if image exists
        result = subprocess.run(
            ["docker", "image", "inspect", image_name], capture_output=True, text=True, check=False
        )

        if result.returncode != 0:
            return True  # Image doesn't exist

        # Check if any extension hash changed
        # This is a simplified check - in production you'd want to store metadata
        return False

    except subprocess.CalledProcessError:
        return True


def build_image_with_bake(
    build_dir: Path,
    builder_name: str = "worktree_docker_builder",
    load: bool = True,
    nocache: bool = False,
) -> bool:
    """Build images using docker buildx bake."""
    try:
        cmd = ["docker", "buildx", "bake", "--builder", builder_name]
        if load:
            cmd.append("--load")
        if nocache:
            cmd.append("--no-cache")
        cmd.append("final")

        logging.info(f"Building with bake: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=build_dir, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to build with bake: {e}")
        return False


def is_container_usable(repo_spec: RepoSpec, work_dir: Path) -> bool:
    """Check if the existing container is usable and accessible."""
    container_name = repo_spec.compose_project_name

    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False  # Container doesn't exist

        status = result.stdout.strip()
        if status != "running":
            logging.info(f"Container {container_name} exists but is not running (status: {status})")
            return False

        # Try to execute a simple command to test accessibility
        env = os.environ.copy()
        env["COMPOSE_PROJECT_NAME"] = repo_spec.compose_project_name

        test_cmd = ["docker", "compose", "exec", "-T", "dev", "echo", "test"]
        test_result = subprocess.run(
            test_cmd, cwd=work_dir, env=env, capture_output=True, check=False, timeout=5
        )

        if test_result.returncode == 0:
            logging.info(f"Reusing existing container: {container_name}")
            return True
        logging.info(f"Container {container_name} is not accessible, will recreate")
        return False

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        logging.info(f"Failed to check container {container_name} accessibility")
        return False


def cleanup_stale_container(repo_spec: RepoSpec) -> None:
    """Clean up stale containers that are not usable."""
    container_name = repo_spec.compose_project_name
    try:
        # Check if container exists
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            logging.info(f"Removing stale container: {container_name}")
            # Stop and remove the container
            subprocess.run(["docker", "stop", container_name], check=False, capture_output=True)
            subprocess.run(["docker", "rm", container_name], check=False, capture_output=True)
    except subprocess.CalledProcessError:
        pass  # Container doesn't exist or already removed


def run_compose_service(
    compose_dir: Path, repo_spec: RepoSpec, command: Optional[List[str]] = None
) -> int:
    """Run Docker Compose service and optionally execute command."""
    env = os.environ.copy()
    env["COMPOSE_PROJECT_NAME"] = repo_spec.compose_project_name
    env["USER_ID"] = str(os.getuid())
    env["GROUP_ID"] = str(os.getgid())

    try:
        # Check if we can reuse existing container
        # Use compose_dir for container accessibility test since that's where compose file is
        container_is_usable = is_container_usable(repo_spec, compose_dir)

        if not container_is_usable:
            # Clean up stale container if it exists but is not usable
            cleanup_stale_container(repo_spec)

            # Start the service
            subprocess.run(["docker", "compose", "up", "-d"], cwd=compose_dir, env=env, check=True)

            # Fix git worktree configuration in the container
            safe_branch = repo_spec.branch.replace("/", "-")
            fix_git_cmd = [
                "docker",
                "compose",
                "exec",
                "-T",
                "dev",
                "bash",
                "-c",
                f"echo 'gitdir: /workspace/{repo_spec.repo}.git/worktrees/worktree-{safe_branch}' > /workspace/{repo_spec.repo}/.git",
            ]
            subprocess.run(fix_git_cmd, cwd=compose_dir, env=env, check=False)

        if command:
            # Execute command in running container
            if len(command) == 1 and (
                any(char in command[0] for char in [";", "&&", "||", "|"])
                or command[0].startswith("bash -c")
                or "'" in command[0]
                or '"' in command[0]
            ):
                # Complex shell command or bash -c format
                exec_cmd = ["docker", "compose", "exec", "dev", "bash", "-c", command[0]]
            else:
                # Simple command
                exec_cmd = ["docker", "compose", "exec", "dev"] + command

            return subprocess.run(exec_cmd, cwd=compose_dir, env=env, check=False).returncode
        # Interactive shell
        exec_cmd = ["docker", "compose", "exec", "dev", "bash"]
        return subprocess.run(exec_cmd, cwd=compose_dir, env=env, check=False).returncode

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to run compose service: {e}")
        return e.returncode


def list_active_containers() -> List[Dict[str, str]]:
    """List active worktree_docker containers."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "label=com.docker.compose.project",
                "--format",
                "table {{.Names}}\\t{{.Status}}\\t{{.Image}}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        containers = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 3:
                    containers.append({"name": parts[0], "status": parts[1], "image": parts[2]})
        return containers
    except subprocess.CalledProcessError:
        return []


def destroy_environment(repo_spec: RepoSpec) -> bool:
    """Destroy Docker Compose environment for repo/branch."""
    build_dir = get_build_cache_dir(repo_spec)
    if not build_dir.exists():
        logging.warning(f"Environment not found: {repo_spec}")
        return False

    env = os.environ.copy()
    env["COMPOSE_PROJECT_NAME"] = repo_spec.compose_project_name

    try:
        subprocess.run(["docker", "compose", "down", "-v"], cwd=build_dir, env=env, check=True)
        logging.info(f"Destroyed environment: {repo_spec}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to destroy environment: {e}")
        return False


@dataclass
class LaunchConfig:
    """Configuration for launching environments."""

    repo_spec: RepoSpec
    extensions: List[str]
    command: Optional[List[str]] = None
    rebuild: bool = False
    nocache: bool = False
    no_gui: bool = False
    no_gpu: bool = False
    platforms: Optional[List[str]] = None
    builder_name: str = "worktree_docker_builder"


def launch_environment(config: LaunchConfig) -> int:
    """Launch development environment for repository/branch."""
    platforms = config.platforms or ["linux/amd64"]

    # Set up worktree
    worktree_dir = setup_worktree(config.repo_spec)
    repo_dir = get_repo_dir(config.repo_spec)

    # Load repo configuration
    repo_config = worktree_dockerConfig(worktree_dir)

    # Auto-detect extensions based on repository contents
    auto_detected = auto_detect_extensions(worktree_dir)
    if auto_detected:
        print(f"Auto-detected extensions: {', '.join(auto_detected)}")

    # Merge extensions: manual config + repo config + auto-detected
    # Remove duplicates while preserving order
    all_extensions = []
    for ext in list(config.extensions) + repo_config.extensions + auto_detected:
        if ext not in all_extensions:
            all_extensions.append(ext)

    if config.no_gui and "x11" in all_extensions:
        all_extensions.remove("x11")
    if config.no_gpu and "nvidia" in all_extensions:
        all_extensions.remove("nvidia")

    # Add required base extensions
    if "base" not in all_extensions:
        all_extensions.insert(0, "base")
    if "user" not in all_extensions:
        all_extensions.append("user")

    # Load extension definitions
    ext_manager = ExtensionManager(get_cache_dir())
    loaded_extensions = []
    print(f"Loading extensions: {', '.join(all_extensions)}")
    for ext_name in all_extensions:
        ext = ext_manager.get_extension(ext_name, worktree_dir)
        if ext:
            loaded_extensions.append(ext)
            print(f"✓ Loaded extension: {ext_name}")
        else:
            logging.warning(f"Extension not found: {ext_name}")
            print(f"✗ Extension not found: {ext_name}")

    # Generate combined hash for image name
    combined_hash = hashlib.sha256(
        "".join(ext.hash for ext in loaded_extensions).encode()
    ).hexdigest()[:12]

    image_name = f"worktree_docker/{config.repo_spec.repo}:{combined_hash}"
    base_image = repo_config.base_image

    # Check if rebuild needed
    if config.rebuild or should_rebuild_image(image_name, loaded_extensions):
        # Ensure Buildx builder
        if not ensure_buildx_builder(config.builder_name):
            return 1

        # Get build cache directory to keep worktree clean
        build_dir = get_build_cache_dir(config.repo_spec)

        # Generate build files in build cache directory
        generate_dockerfile(loaded_extensions, base_image, build_dir)
        generate_bake_file(loaded_extensions, base_image, platforms, build_dir)

        # Build image
        if not build_image_with_bake(build_dir, config.builder_name, nocache=config.nocache):
            return 1

        logging.info(f"Built image: {image_name}")

    # Get build cache directory for compose file
    build_dir = get_build_cache_dir(config.repo_spec)

    # Generate compose file
    compose_config = ComposeConfig(
        repo_spec=config.repo_spec,
        extensions=loaded_extensions,
        image_name=image_name,
        work_dir=worktree_dir,
        worktree_dir=worktree_dir,
        repo_dir=repo_dir,
        build_dir=build_dir,
    )
    generate_compose_file(compose_config)

    # Run environment using build directory for compose file
    return run_compose_service(build_dir, config.repo_spec, config.command)


def cmd_launch(args) -> int:
    """Launch command implementation."""
    repo_spec = RepoSpec.parse(args.repo_spec)
    config = LaunchConfig(
        repo_spec=repo_spec,
        extensions=args.extensions or [],
        command=args.command if args.command else None,
        rebuild=args.rebuild,
        nocache=args.nocache,
        no_gui=args.no_gui,
        no_gpu=args.no_gpu,
        platforms=args.platforms.split(",") if args.platforms else None,
        builder_name=args.builder,
    )
    return launch_environment(config)


def cmd_list(args) -> int:  # pylint: disable=unused-argument
    """List active environments."""
    del args  # Unused parameter
    containers = list_active_containers()
    if not containers:
        print("No active environments found.")
        return 0

    print("Active environments:")
    for container in containers:
        print(f"  {container['name']}: {container['status']}")
    return 0


def cmd_install(args) -> int:  # pylint: disable=unused-argument
    import os  # pylint: disable=reimported,redefined-outer-name

    shell = os.environ.get("SHELL", "").split("/")[-1]
    home = os.path.expanduser("~")
    success = False
    if shell == "bash":
        bash_completion_dir = f"{home}/.bash_completion.d"
        os.makedirs(bash_completion_dir, exist_ok=True)
        completion_file = f"{bash_completion_dir}/wtd"
        with open(completion_file, "w", encoding="utf-8") as f:
            f.write(bash_completion)
        print(f"✓ Bash completion installed to {completion_file}")
        print("Run 'source ~/.bashrc' or restart your terminal to enable completion")
        success = True
    elif shell == "zsh":
        zsh_completion_dir = f"{home}/.zsh/completions"
        os.makedirs(zsh_completion_dir, exist_ok=True)
        completion_file = f"{zsh_completion_dir}/_wtd"
        with open(completion_file, "w", encoding="utf-8") as f:
            f.write(zsh_completion)
        print(f"✓ Zsh completion installed to {completion_file}")
        print("Add 'fpath=(~/.zsh/completions $fpath)' to your ~/.zshrc if not already present")
        print("Run 'autoload -U compinit && compinit' or restart your terminal")
        success = True
    elif shell == "fish":
        fish_completion_dir = f"{home}/.config/fish/completions"
        os.makedirs(fish_completion_dir, exist_ok=True)
        completion_file = f"{fish_completion_dir}/wtd.fish"
        with open(completion_file, "w", encoding="utf-8") as f:
            f.write(fish_completion)
        print(f"✓ Fish completion installed to {completion_file}")
        print("Restart your fish shell to enable completion")
        success = True
    else:
        print(f"✗ Unknown shell: {shell}")
        print("Supported shells: bash, zsh, fish")
        print("You can manually install completion scripts:")
        print("\nBash completion script:")
        print(bash_completion)
        print("\nZsh completion script:")
        print(zsh_completion)
        print("\nFish completion script:")
        print(fish_completion)
    return 0 if success else 1


def cmd_prune(args) -> int:
    """Prune containers, images, volumes, and worktree_docker folders."""
    try:
        if hasattr(args, "repo_spec") and args.repo_spec:
            # Selective pruning for specific repo spec
            repo_spec = RepoSpec.parse(args.repo_spec)
            return prune_repo_environment(repo_spec)
        # Prune everything
        return prune_all()
    except Exception as e:
        logging.error(f"Failed to prune: {e}")
        return 1


def prune_repo_environment(repo_spec: RepoSpec) -> int:
    """Prune containers, images, and worktree for a specific repo spec."""
    try:
        container_name = repo_spec.compose_project_name
        worktree_dir = get_worktree_dir(repo_spec)

        # Stop and remove container
        print(f"Removing container: {container_name}")
        subprocess.run(["docker", "stop", container_name], check=False, capture_output=True)
        subprocess.run(["docker", "rm", container_name], check=False, capture_output=True)

        # Remove associated images (worktree_docker images for this repo)
        removed_images = []
        try:
            result = subprocess.run(
                [
                    "docker",
                    "images",
                    "--filter",
                    f"reference=worktree_docker/{repo_spec.repo}*",
                    "-q",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                image_ids = result.stdout.strip().split("\n")
                # Get image names before removing
                for image_id in image_ids:
                    name_result = subprocess.run(
                        ["docker", "inspect", "--format", "{{.RepoTags}}", image_id],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if name_result.stdout.strip():
                        removed_images.append(name_result.stdout.strip())

                subprocess.run(
                    ["docker", "rmi", "-f"] + image_ids, check=False, capture_output=True
                )
                for image in removed_images:
                    print(f"Removed image: {image}")
        except subprocess.CalledProcessError:
            pass

        # Clean up compose volumes first from build directory
        build_dir = get_build_cache_dir(repo_spec)
        if build_dir.exists():
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = repo_spec.compose_project_name
            subprocess.run(
                ["docker", "compose", "down", "-v"],
                cwd=build_dir,
                env=env,
                check=False,
                capture_output=True,
            )

        # Remove worktree directory
        if worktree_dir.exists():
            print(f"Removing worktree: {worktree_dir}")
            subprocess.run(["rm", "-rf", str(worktree_dir)], check=False)

        # Remove build cache directory
        if build_dir.exists():
            print(f"Removing build cache: {build_dir}")
            subprocess.run(["rm", "-rf", str(build_dir)], check=False)

        # Clean up git worktree registration if repo exists
        repo_dir = get_repo_dir(repo_spec)
        if repo_dir.exists():
            safe_branch = repo_spec.branch.replace("/", "-")
            worktree_name = f"worktree-{safe_branch}"
            subprocess.run(
                ["git", "-C", str(repo_dir), "worktree", "remove", worktree_name],
                check=False,
                capture_output=True,
            )

        logging.info(f"Pruned environment for {repo_spec}")
        return 0
    except Exception as e:
        logging.error(f"Failed to prune repo environment: {e}")
        return 1


def prune_all() -> int:
    """Prune all worktree_docker-related containers, images, and folders."""
    try:
        removed_containers = []
        removed_images = []

        # Get all worktree_docker-related containers and remove them
        try:
            # Only prune containers with the worktree_docker.managed label
            result = subprocess.run(
                ["docker", "ps", "-aq", "--filter", "label=worktree_docker.managed=true"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                container_ids = result.stdout.strip().split("\n")
                for container_id in container_ids:
                    inspect_result = subprocess.run(
                        ["docker", "inspect", "--format", "{{.Name}}", container_id],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if inspect_result.stdout.strip():
                        container_name = inspect_result.stdout.strip().lstrip("/")
                        print(f"Removing container: {container_name}")
                        subprocess.run(
                            ["docker", "stop", container_id], check=False, capture_output=True
                        )
                        subprocess.run(
                            ["docker", "rm", "-f", container_id],
                            check=False,
                            capture_output=True,
                        )
                        removed_containers.append(container_name)
        except subprocess.CalledProcessError:
            pass

        # Get worktree_docker-related images and remove them
        try:
            # Remove images with worktree_docker/test prefixes
            result = subprocess.run(
                ["docker", "images", "-q"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                image_ids = result.stdout.strip().split("\n")
                for image_id in image_ids:
                    name_result = subprocess.run(
                        ["docker", "inspect", "--format", "{{.RepoTags}}", image_id],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if name_result.stdout.strip():
                        image_tags = name_result.stdout.strip()
                        # Remove images that match worktree_docker/test naming patterns
                        if (
                            "worktree_docker/" in image_tags
                            or "test_worktree_docker" in image_tags
                            or "test_wtd" in image_tags
                        ):
                            print(f"Removing image: {image_tags}")
                            removed_images.append(image_tags)
                            subprocess.run(
                                ["docker", "rmi", "-f", image_id], check=False, capture_output=True
                            )
        except subprocess.CalledProcessError:
            pass

        # Remove worktree_docker cache and workspaces folders
        cache_dir = str(get_cache_dir())
        workspaces_dir = str(get_workspaces_dir())
        for folder in [cache_dir, workspaces_dir]:
            if os.path.exists(folder):
                print(f"Removing directory: {folder}")
                subprocess.run(["rm", "-rf", folder], check=False)

        # Print summary
        if removed_containers or removed_images:
            print(f"Pruned {len(removed_containers)} containers and {len(removed_images)} images")
        else:
            print("No worktree_docker resources found to prune")

        logging.info("Pruned all worktree_docker-related containers, images, and folders")
        return 0
    except Exception as e:
        logging.error(f"Failed to prune all worktree_docker resources: {e}")
        return 1


def cmd_ext(args) -> int:
    """Extension management command."""
    ext_manager = ExtensionManager(get_cache_dir())

    if args.ext_action == "list":
        extensions = ext_manager.list_extensions()
        print("Available extensions:")
        for ext in extensions:
            print(f"  {ext}")
        return 0

    # TODO: Implement add/remove functionality
    logging.error("Extension add/remove not yet implemented")
    return 1


def cmd_doctor(args) -> int:  # pylint: disable=unused-argument
    """Run environment diagnostics."""
    del args  # Unused parameter
    checks = [
        (
            "Docker",
            lambda: subprocess.run(["docker", "--version"], capture_output=True, check=True),
        ),
        (
            "Docker Compose",
            lambda: subprocess.run(
                ["docker", "compose", "version"], capture_output=True, check=True
            ),
        ),
        (
            "Docker Buildx",
            lambda: subprocess.run(
                ["docker", "buildx", "version"], capture_output=True, check=True
            ),
        ),
        ("Git", lambda: subprocess.run(["git", "--version"], capture_output=True, check=True)),
    ]

    all_good = True
    for name, check_func in checks:
        try:
            check_func()
            print(f"✓ {name}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"✗ {name}")
            all_good = False

    return 0 if all_good else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="wtd",
        usage="wtd [OPTIONS] [-e ext1 ext2 ...] <owner>/<repo>[@<branch>][#<subfolder>] [command...]",
        description="""A development environment launcher using Docker, Git worktrees, and Buildx/Bake.

Clones and manages repositories in isolated git worktrees, builds cached container environments using Docker Buildx + Bake, and launches fully configured shells or commands inside each branch-specific container workspace.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  wtd blooop/test_wtd@main
  wtd -e uv bloop
""",
    )

    parser.add_argument(
        "-e",
        "--extensions",
        nargs="+",
        help="Specify extensions to use (overrides config/auto-detection)",
    )
    parser.add_argument(
        "-c",
        "--command",
        nargs=argparse.REMAINDER,
        help="Command to run in the environment (defaults to interactive shell)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild of the environment image",
    )
    parser.add_argument(
        "--nocache",
        action="store_true",
        help="Do not use cache when building the image",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Disable GUI (X11) support",
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Disable GPU (NVIDIA) support",
    )
    parser.add_argument(
        "--platforms",
        help="Comma-separated list of platforms for multi-arch builds",
    )
    parser.add_argument(
        "--builder",
        default="wtd_builder",
        help="Name of the Buildx builder to use",
    )
    parser.add_argument(
        "repo_spec",
        nargs="?",
        help="GitHub repo specifier: <owner>/<repo>[@<branch>][#<subfolder>]",
    )

    args = parser.parse_args()

    # Command dispatch
    if args.command_name == "launch":
        return cmd_launch(args)
    elif args.command_name == "list":
        return cmd_list(args)
    elif args.command_name == "install":
        return cmd_install(args)
    elif args.command_name == "prune":
        return cmd_prune(args)
    elif args.command_name == "ext":
        return cmd_ext(args)
    elif args.command_name == "doctor":
        return cmd_doctor(args)

    # Default to launch if no command given
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ["-h", "--help"]):
        parser.print_help()
        return 0

    return cmd_launch(args)
