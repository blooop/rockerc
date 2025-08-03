"""
renv - Development environment launcher using Docker, Git worktrees, and Buildx/Bake

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
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


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
    """Represents a renv extension with its configuration."""

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


class RenvConfig:
    """Manages renv configuration from .renv.yml/.renv.json files."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from repo directory."""
        for config_file in [".renv.yml", ".renv.yaml", ".renv.json"]:
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
                "volumes": ["~/.gitconfig:/home/renv/.gitconfig:ro", "~/.ssh:/home/renv/.ssh:ro"]
            },
        )

        # User setup
        extensions["user"] = Extension(
            name="user",
            dockerfile_content="""
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} renv && \\
    useradd -u ${USER_ID} -g renv -m -s /bin/bash renv && \\
    echo 'renv ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER renv
WORKDIR /workspace
""",
            compose_fragment={
                "build": {"args": {"USER_ID": "${USER_ID:-1000}", "GROUP_ID": "${GROUP_ID:-1000}"}},
                "environment": {"USER": "renv", "HOME": "/home/renv"},
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
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/renv/.cargo/bin:$PATH"
""",
            compose_fragment={},
        )

        # Fuzzy finder
        extensions["fzf"] = Extension(
            name="fzf",
            dockerfile_content="""
RUN git clone --depth 1 https://github.com/junegunn/fzf.git /home/renv/.fzf && \\
    chown -R renv:renv /home/renv/.fzf && \\
    /home/renv/.fzf/install --all
""",
            compose_fragment={},
        )

        return extensions

    def get_extension(self, name: str, repo_path: Optional[Path] = None) -> Optional[Extension]:
        """Get extension by name, checking repo-local first, then built-in."""
        # Check repo-local extensions first
        if repo_path:
            local_ext_dir = repo_path / ".renv" / "exts" / name
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
            local_exts_dir = repo_path / ".renv" / "exts"
            if local_exts_dir.exists():
                extensions.update(d.name for d in local_exts_dir.iterdir() if d.is_dir())

        return sorted(extensions)


def get_cache_dir() -> Path:
    """Get renv cache directory."""
    cache_dir = os.getenv("RENV_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir)
    return Path.home() / ".renv"


def get_workspaces_dir() -> Path:
    """Get workspaces directory."""
    return get_cache_dir() / "workspaces"


def get_repo_dir(repo_spec: RepoSpec) -> Path:
    """Get bare repository directory."""
    return get_workspaces_dir() / repo_spec.owner / repo_spec.repo


def get_worktree_dir(repo_spec: RepoSpec) -> Path:
    """Get worktree directory for a specific branch."""
    safe_branch = repo_spec.branch.replace("/", "-")
    return get_repo_dir(repo_spec) / f"worktree-{safe_branch}"


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
        subprocess.run(
            ["git", "-C", str(repo_dir), "worktree", "add", str(worktree_dir), repo_spec.branch],
            check=True,
        )
        time.sleep(0.1)  # Allow filesystem to sync
    else:
        logging.info(f"Worktree already exists: {worktree_dir}")

    return worktree_dir


def ensure_buildx_builder(builder_name: str = "renv_builder") -> bool:
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


def generate_dockerfile(extensions: List[Extension], base_image: str, work_dir: Path) -> str:
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

    # Write Dockerfile to work directory
    dockerfile_path = work_dir / "Dockerfile"
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

    # Write compose file
    compose_path = config.work_dir / "docker-compose.yml"
    with open(compose_path, "w", encoding="utf-8") as f:
        yaml.dump(compose_config, f, default_flow_style=False)

    return compose_config


def generate_bake_file(
    extensions: List[Extension], base_image: str, platforms: List[str], work_dir: Path
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
    tags = ["renv/{ext.name}:{ext.hash}"]
    platforms = {platforms_hcl}
    cache-from = ["type=local,src=.buildx-cache"]
    cache-to = ["type=local,dest=.buildx-cache,mode=max"]
}}"""
        targets.append(target)

        # Write individual Dockerfile for this extension
        ext_dockerfile = f"FROM {current_image}\n{ext.dockerfile_content}"
        dockerfile_path = work_dir / f"Dockerfile.{ext.name}"
        dockerfile_path.write_text(ext_dockerfile, encoding="utf-8")

        current_image = f"renv/{ext.name}:{ext.hash}"

    # Final target combining all extensions
    final_target = f"""
target "final" {{
    context = "."
    dockerfile = "Dockerfile"
    tags = ["renv/final:{'-'.join(ext.hash for ext in extensions)}"]
    platforms = {platforms_hcl}
    cache-from = ["type=local,src=.buildx-cache"]
    cache-to = ["type=local,dest=.buildx-cache,mode=max"]
}}"""
    targets.append(final_target)

    bake_content = "\n".join(targets)

    # Write bake file
    bake_path = work_dir / "docker-bake.hcl"
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
    work_dir: Path, builder_name: str = "renv_builder", load: bool = True
) -> bool:
    """Build images using docker buildx bake."""
    try:
        cmd = ["docker", "buildx", "bake", "--builder", builder_name]
        if load:
            cmd.append("--load")
        cmd.append("final")

        logging.info(f"Building with bake: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=work_dir, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to build with bake: {e}")
        return False


def cleanup_stale_container(repo_spec: RepoSpec) -> None:
    """Clean up stale containers that may have invalid mount points."""
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
    work_dir: Path, repo_spec: RepoSpec, command: Optional[List[str]] = None
) -> int:
    """Run Docker Compose service and optionally execute command."""
    env = os.environ.copy()
    env["COMPOSE_PROJECT_NAME"] = repo_spec.compose_project_name
    env["USER_ID"] = str(os.getuid())
    env["GROUP_ID"] = str(os.getgid())

    try:
        # Clean up any stale containers that might have invalid mount points
        cleanup_stale_container(repo_spec)

        # Start the service
        subprocess.run(["docker", "compose", "up", "-d"], cwd=work_dir, env=env, check=True)

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
        subprocess.run(fix_git_cmd, cwd=work_dir, env=env, check=False)

        if command:
            # Execute command in running container
            if len(command) == 1 and any(char in command[0] for char in [";", "&&", "||", "|"]):
                # Complex shell command
                exec_cmd = ["docker", "compose", "exec", "dev", "bash", "-c", command[0]]
            else:
                # Simple command
                exec_cmd = ["docker", "compose", "exec", "dev"] + command

            return subprocess.run(exec_cmd, cwd=work_dir, env=env, check=False).returncode
        # Interactive shell
        exec_cmd = ["docker", "compose", "exec", "dev", "bash"]
        return subprocess.run(exec_cmd, cwd=work_dir, env=env, check=False).returncode

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to run compose service: {e}")
        return e.returncode


def list_active_containers() -> List[Dict[str, str]]:
    """List active renv containers."""
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
    work_dir = get_worktree_dir(repo_spec)
    if not work_dir.exists():
        logging.warning(f"Environment not found: {repo_spec}")
        return False

    env = os.environ.copy()
    env["COMPOSE_PROJECT_NAME"] = repo_spec.compose_project_name

    try:
        subprocess.run(["docker", "compose", "down", "-v"], cwd=work_dir, env=env, check=True)
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
    no_gui: bool = False
    no_gpu: bool = False
    platforms: Optional[List[str]] = None
    builder_name: str = "renv_builder"


def launch_environment(config: LaunchConfig) -> int:
    """Launch development environment for repository/branch."""
    platforms = config.platforms or ["linux/amd64"]

    # Set up worktree
    worktree_dir = setup_worktree(config.repo_spec)
    repo_dir = get_repo_dir(config.repo_spec)

    # Load repo configuration
    repo_config = RenvConfig(worktree_dir)

    # Merge extensions
    all_extensions = list(config.extensions) + repo_config.extensions
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
    for ext_name in all_extensions:
        ext = ext_manager.get_extension(ext_name, worktree_dir)
        if ext:
            loaded_extensions.append(ext)
        else:
            logging.warning(f"Extension not found: {ext_name}")

    # Generate combined hash for image name
    combined_hash = hashlib.sha256(
        "".join(ext.hash for ext in loaded_extensions).encode()
    ).hexdigest()[:12]

    image_name = f"renv/{config.repo_spec.repo}:{combined_hash}"
    base_image = repo_config.base_image

    # Check if rebuild needed
    if config.rebuild or should_rebuild_image(image_name, loaded_extensions):
        # Ensure Buildx builder
        if not ensure_buildx_builder(config.builder_name):
            return 1

        # Generate build files
        generate_dockerfile(loaded_extensions, base_image, worktree_dir)
        generate_bake_file(loaded_extensions, base_image, platforms, worktree_dir)

        # Build image
        if not build_image_with_bake(worktree_dir, config.builder_name):
            return 1

        logging.info(f"Built image: {image_name}")

    # Generate compose file
    compose_config = ComposeConfig(
        repo_spec=config.repo_spec,
        extensions=loaded_extensions,
        image_name=image_name,
        work_dir=worktree_dir,
        worktree_dir=worktree_dir,
        repo_dir=repo_dir,
    )
    generate_compose_file(compose_config)

    # Run environment
    return run_compose_service(worktree_dir, config.repo_spec, config.command)


def cmd_launch(args) -> int:
    """Launch command implementation."""
    repo_spec = RepoSpec.parse(args.repo_spec)
    config = LaunchConfig(
        repo_spec=repo_spec,
        extensions=args.extensions or [],
        command=args.command if args.command else None,
        rebuild=args.rebuild,
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


def cmd_destroy(args) -> int:
    """Destroy environment command."""
    repo_spec = RepoSpec.parse(args.repo_spec)
    success = destroy_environment(repo_spec)
    return 0 if success else 1


def cmd_prune(args) -> int:
    """Prune containers, images, volumes, and renv folders."""
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

        # Remove associated images (renv images for this repo)
        removed_images = []
        try:
            result = subprocess.run(
                ["docker", "images", "--filter", f"reference=renv/{repo_spec.repo}*", "-q"],
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

        # Remove worktree and its compose files
        if worktree_dir.exists():
            print(f"Removing worktree: {worktree_dir}")
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = repo_spec.compose_project_name
            # Clean up compose volumes first
            subprocess.run(
                ["docker", "compose", "down", "-v"],
                cwd=worktree_dir,
                env=env,
                check=False,
                capture_output=True,
            )

            # Remove worktree directory
            subprocess.run(["rm", "-rf", str(worktree_dir)], check=False)

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
    """Prune all renv-related containers, images, and folders."""
    try:
        removed_containers = []
        removed_images = []

        # Get all renv-related containers and remove them
        try:
            # Find containers with renv-related project names
            result = subprocess.run(
                ["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                container_ids = result.stdout.strip().split("\n")
                for container_id in container_ids:
                    # Check if container name matches renv patterns
                    inspect_result = subprocess.run(
                        ["docker", "inspect", "--format", "{{.Name}}", container_id],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if inspect_result.stdout.strip():
                        container_name = inspect_result.stdout.strip().lstrip("/")
                        # Remove containers that match renv naming patterns
                        if any(pattern in container_name for pattern in ["renv-", "-main", "-dev"]):
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

        # Get renv-related images and remove them
        try:
            # Remove images with renv prefix
            result = subprocess.run(
                ["docker", "images", "--filter", "reference=renv/*", "-q"],
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
                        image_name = name_result.stdout.strip()
                        print(f"Removing image: {image_name}")
                        removed_images.append(image_name)

                subprocess.run(
                    ["docker", "rmi", "-f"] + image_ids, check=False, capture_output=True
                )
        except subprocess.CalledProcessError:
            pass

        # Remove renv cache and workspaces folders
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
            print("No renv resources found to prune")

        logging.info("Pruned all renv-related containers, images, and folders")
        return 0
    except Exception as e:
        logging.error(f"Failed to prune all renv resources: {e}")
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
        description="A development environment launcher using Docker, Git worktrees, and Buildx/Bake",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  renv blooop/test_renv@main
  renv blooop/test_renv@feature/foo
  renv blooop/test_renv@main#src
  renv blooop/test_renv git status
  renv blooop/test_renv@dev "bash -c 'git pull && make test'"
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Launch command (default)
    launch_parser = subparsers.add_parser("launch", help="Launch container environment")
    launch_parser.add_argument(
        "repo_spec", help="Repository specification: owner/repo[@branch][#subfolder]"
    )
    launch_parser.add_argument("command", nargs="*", help="Command to execute")
    launch_parser.add_argument("--extensions", "-e", nargs="*", help="Extensions to enable")
    launch_parser.add_argument("--rebuild", action="store_true", help="Force rebuild")
    launch_parser.add_argument("--no-gui", action="store_true", help="Disable GUI support")
    launch_parser.add_argument("--no-gpu", action="store_true", help="Disable GPU support")
    launch_parser.add_argument("--builder", default="renv_builder", help="Buildx builder name")
    launch_parser.add_argument("--platforms", help="Target platforms (comma-separated)")
    launch_parser.set_defaults(func=cmd_launch)

    # List command
    list_parser = subparsers.add_parser("list", help="List active environments")
    list_parser.set_defaults(func=cmd_list)

    # Destroy command
    destroy_parser = subparsers.add_parser("destroy", help="Destroy environment")
    destroy_parser.add_argument("repo_spec", help="Repository specification")
    destroy_parser.set_defaults(func=cmd_destroy)

    # Prune command
    prune_parser = subparsers.add_parser("prune", help="Prune unused resources")
    prune_parser.add_argument(
        "repo_spec",
        nargs="?",
        help="Repository specification (optional - prunes everything if not specified)",
    )
    prune_parser.set_defaults(func=cmd_prune)

    # Extension command
    ext_parser = subparsers.add_parser("ext", help="Manage extensions")
    ext_parser.add_argument("ext_action", choices=["list", "add", "remove"])
    ext_parser.add_argument("ext_name", nargs="?", help="Extension name")
    ext_parser.set_defaults(func=cmd_ext)

    # Doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Run diagnostics")
    doctor_parser.set_defaults(func=cmd_doctor)

    # Global options
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warn", "error"],
        default="info",
        help="Set log level",
    )

    # Handle backward compatibility and convert old flags to new format
    args = sys.argv[1:]

    # Check if this looks like the old format: [flags] repo_spec [command]
    if args and args[0] not in ["launch", "list", "destroy", "prune", "ext", "doctor", "help"]:
        # Extract global flags that should be moved to launch subcommand
        launch_flags = []
        remaining_args = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ["--force", "--rebuild"]:
                launch_flags.append("--rebuild")  # Convert --force to --rebuild
            elif arg in ["--nocache"]:
                launch_flags.append("--rebuild")  # For now, treat --nocache as --rebuild
            elif arg in ["--no-gui", "--no-gpu"]:
                launch_flags.append(arg)
            elif arg.startswith("--builder"):
                if "=" in arg:
                    launch_flags.append(arg)
                else:
                    launch_flags.extend([arg, args[i + 1]])
                    i += 1
            elif arg.startswith("--platforms"):
                if "=" in arg:
                    launch_flags.append(arg)
                else:
                    launch_flags.extend([arg, args[i + 1]])
                    i += 1
            elif arg.startswith("--log-level"):
                if "=" in arg:
                    remaining_args.append(arg)
                else:
                    remaining_args.extend([arg, args[i + 1]])
                    i += 1
            else:
                remaining_args.extend(args[i:])
                break
            i += 1

        # Rebuild args in new format: [global_flags] launch [launch_flags] repo_spec [command]
        global_flags = [arg for arg in remaining_args if arg.startswith("--log-level")]
        other_args = [arg for arg in remaining_args if not arg.startswith("--log-level")]

        if other_args:
            args = global_flags + ["launch"] + launch_flags + other_args

    parsed_args = parser.parse_args(args)

    # If no command is provided, and '--prune' is present, treat as prune
    if not args and "--prune" in sys.argv:
        return cmd_prune(argparse.Namespace())

    # Set up logging
    log_level = getattr(logging, parsed_args.log_level.upper())
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if hasattr(parsed_args, "func"):
        return parsed_args.func(parsed_args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
