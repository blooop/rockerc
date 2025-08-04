"""
Comprehensive test suite for the new renv implementation with Docker Compose + Buildx/Bake
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from worktree_docker.renv import (
    RepoSpec,
    Extension,
    RenvConfig,
    ExtensionManager,
    ComposeConfig,
    LaunchConfig,
    get_cache_dir,
    get_workspaces_dir,
    get_repo_dir,
    get_worktree_dir,
    auto_detect_extensions,
    setup_bare_repo,
    setup_worktree,
    ensure_buildx_builder,
    generate_dockerfile,
    generate_compose_file,
    generate_bake_file,
    should_rebuild_image,
    build_image_with_bake,
    run_compose_service,
    list_active_containers,
    destroy_environment,
    launch_environment,
    cmd_launch,
    cmd_list,
    cmd_prune,
    cmd_ext,
    cmd_doctor,
    main,
)


class TestRepoSpec:
    """Test RepoSpec parsing and behavior."""

    def test_parse_simple(self):
        """Test simple repo specification parsing."""
        spec = RepoSpec.parse("blooop/test_renv")
        assert spec.owner == "blooop"
        assert spec.repo == "test_renv"
        assert spec.branch == "main"
        assert spec.subfolder is None

    def test_parse_with_branch(self):
        """Test repo specification with branch."""
        spec = RepoSpec.parse("blooop/test_renv@feature/new")
        assert spec.owner == "blooop"
        assert spec.repo == "test_renv"
        assert spec.branch == "feature/new"
        assert spec.subfolder is None

    def test_parse_with_subfolder(self):
        """Test repo specification with subfolder."""
        spec = RepoSpec.parse("blooop/test_renv#src/core")
        assert spec.owner == "blooop"
        assert spec.repo == "test_renv"
        assert spec.branch == "main"
        assert spec.subfolder == "src/core"

    def test_parse_with_branch_and_subfolder(self):
        """Test repo specification with both branch and subfolder."""
        spec = RepoSpec.parse("blooop/test_renv@feature/new#src/core")
        assert spec.owner == "blooop"
        assert spec.repo == "test_renv"
        assert spec.branch == "feature/new"
        assert spec.subfolder == "src/core"

    def test_str_representation(self):
        """Test string representation."""
        spec = RepoSpec("blooop", "test_renv", "feature/new", "src")
        assert str(spec) == "blooop/test_renv@feature/new#src"

    def test_compose_project_name(self):
        """Test Docker Compose project name generation."""
        spec = RepoSpec("blooop", "test_renv", "feature/new")
        assert spec.compose_project_name == "test_renv-feature-new"


class TestExtension:
    """Test Extension class behavior."""

    def test_extension_hash(self):
        """Test extension hash generation."""
        ext = Extension(
            name="test",
            dockerfile_content="FROM ubuntu",
            compose_fragment={"environment": {"TEST": "value"}},
            files={"config.txt": "content"},
        )

        # Hash should be consistent
        hash1 = ext.hash
        hash2 = ext.hash
        assert hash1 == hash2
        assert len(hash1) == 12

    def test_extension_hash_changes_with_content(self):
        """Test that hash changes when content changes."""
        ext1 = Extension("test", "FROM ubuntu:20.04", {})
        ext2 = Extension("test", "FROM ubuntu:22.04", {})

        assert ext1.hash != ext2.hash


class TestRenvConfig:
    """Test RenvConfig functionality."""

    def test_load_yaml_config(self):
        """Test loading YAML configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".renv.yml"
            config_data = {
                "extensions": ["git", "x11"],
                "base_image": "ubuntu:20.04",
                "platforms": ["linux/amd64", "linux/arm64"],
            }

            with open(config_path, "w", encoding="utf-8") as f:
                import yaml

                yaml.dump(config_data, f)

            config = RenvConfig(Path(tmpdir))
            assert config.extensions == ["git", "x11"]
            assert config.base_image == "ubuntu:20.04"
            assert config.platforms == ["linux/amd64", "linux/arm64"]

    def test_load_json_config(self):
        """Test loading JSON configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".renv.json"
            config_data = {"extensions": ["fzf", "uv"], "base_image": "debian:bullseye"}

            with open(config_path, "w", encoding="utf-8") as f:
                import json

                json.dump(config_data, f)

            config = RenvConfig(Path(tmpdir))
            assert config.extensions == ["fzf", "uv"]
            assert config.base_image == "debian:bullseye"

    def test_default_config(self):
        """Test default configuration when no file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RenvConfig(Path(tmpdir))
            assert config.extensions == []
            assert config.base_image == "ubuntu:22.04"
            assert config.platforms == ["linux/amd64"]


class TestExtensionManager:
    """Test ExtensionManager functionality."""

    def test_builtin_extensions(self):
        """Test that built-in extensions are loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExtensionManager(Path(tmpdir))

            # Check that base extensions exist
            assert manager.get_extension("base") is not None
            assert manager.get_extension("git") is not None
            assert manager.get_extension("user") is not None
            assert manager.get_extension("x11") is not None
            assert manager.get_extension("nvidia") is not None
            assert manager.get_extension("uv") is not None
            assert manager.get_extension("fzf") is not None

    def test_local_extension_loading(self):
        """Test loading repo-local extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "repo"
            ext_dir = repo_dir / ".renv" / "exts" / "custom"
            ext_dir.mkdir(parents=True)

            # Create extension files
            dockerfile = ext_dir / "Dockerfile"
            dockerfile.write_text("FROM custom:latest", encoding="utf-8")

            compose_fragment = ext_dir / "docker-compose.fragment.yml"
            compose_fragment.write_text("environment:\n  CUSTOM: true", encoding="utf-8")

            manager = ExtensionManager(Path(tmpdir))
            ext = manager.get_extension("custom", repo_dir)

            assert ext is not None
            assert ext.name == "custom"
            assert "FROM custom:latest" in ext.dockerfile_content
            assert ext.compose_fragment["environment"]["CUSTOM"] is True

    def test_list_extensions(self):
        """Test listing available extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExtensionManager(Path(tmpdir))
            extensions = manager.list_extensions()

            # Should include built-in extensions
            assert "base" in extensions
            assert "git" in extensions
            assert "user" in extensions


class TestPathHelpers:
    """Test path helper functions."""

    @patch.dict("os.environ", {"RENV_CACHE_DIR": "/custom/cache"})
    def test_get_cache_dir_custom(self):
        """Test custom cache directory from environment."""
        assert get_cache_dir() == Path("/custom/cache")

    @patch.dict("os.environ", {}, clear=True)
    def test_get_cache_dir_default(self):
        """Test default cache directory."""
        assert get_cache_dir() == Path.home() / ".renv"

    def test_get_workspaces_dir(self):
        """Test workspaces directory."""
        with patch("worktree_docker.renv.get_cache_dir", return_value=Path("/cache")):
            assert get_workspaces_dir() == Path("/cache/workspaces")

    def test_get_repo_dir(self):
        """Test repository directory path."""
        spec = RepoSpec("owner", "repo", "main")
        with patch("worktree_docker.renv.get_workspaces_dir", return_value=Path("/workspaces")):
            assert get_repo_dir(spec) == Path("/workspaces/owner/repo")

    def test_get_worktree_dir(self):
        """Test worktree directory path."""
        spec = RepoSpec("owner", "repo", "feature/new")
        with patch("worktree_docker.renv.get_repo_dir", return_value=Path("/repo")):
            assert get_worktree_dir(spec) == Path("/repo/worktree-feature-new")


class TestGitOperations:
    """Test Git operations."""

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_bare_repo_clone(self, mock_exists, mock_run):
        """Test cloning a new bare repository."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        spec = RepoSpec("owner", "repo", "main")
        setup_bare_repo(spec)

        # Should call git clone
        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "clone" in call_args
        assert "--bare" in call_args
        assert "git@github.com:owner/repo.git" in call_args

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_bare_repo_fetch(self, mock_exists, mock_run):
        """Test fetching updates for existing bare repository."""
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0)

        spec = RepoSpec("owner", "repo", "main")
        setup_bare_repo(spec)

        # Should call git fetch
        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "fetch" in call_args
        assert "--all" in call_args

    @patch("worktree_docker.renv.setup_bare_repo")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_worktree_create(self, mock_exists, mock_run, mock_setup_bare):
        """Test creating a new worktree."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        spec = RepoSpec("owner", "repo", "feature")
        setup_worktree(spec)

        # Should set up bare repo first
        mock_setup_bare.assert_called_once_with(spec)

        # Should call git worktree add
        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "worktree" in call_args
        assert "add" in call_args


class TestBuildxOperations:
    """Test Docker Buildx operations."""

    @patch("subprocess.run")
    def test_ensure_buildx_builder_create(self, mock_run):
        """Test creating a new Buildx builder."""
        # First call (inspect) fails, second call (create) succeeds
        mock_run.side_effect = [
            Mock(returncode=1),  # inspect fails
            Mock(returncode=0),  # create succeeds
        ]

        result = ensure_buildx_builder("test_builder")
        assert result is True

        # Should call inspect then create
        assert mock_run.call_count == 2
        create_call = mock_run.call_args_list[1][0][0]
        assert "docker" in create_call
        assert "buildx" in create_call
        assert "create" in create_call
        assert "test_builder" in create_call

    @patch("subprocess.run")
    def test_ensure_buildx_builder_exists(self, mock_run):
        """Test using existing Buildx builder."""
        mock_run.return_value = Mock(returncode=0)

        result = ensure_buildx_builder("test_builder")
        assert result is True

        # Should call inspect then use
        assert mock_run.call_count == 2
        use_call = mock_run.call_args_list[1][0][0]
        assert "docker" in use_call
        assert "buildx" in use_call
        assert "use" in use_call


class TestFileGeneration:
    """Test file generation functions."""

    def test_generate_dockerfile(self):
        """Test Dockerfile generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            extensions = [
                Extension("base", "FROM ubuntu:22.04\nRUN apt-get update", {}),
                Extension("git", "RUN apt-get install -y git", {}),
            ]

            content = generate_dockerfile(extensions, "ubuntu:22.04", work_dir)

            assert "FROM ubuntu:22.04 as base" in content
            assert "Extension: base" in content
            assert "Extension: git" in content
            assert "apt-get update" in content
            assert "apt-get install -y git" in content
            assert "WORKDIR /workspace" in content

            # Check file was written
            dockerfile = work_dir / "Dockerfile"
            assert dockerfile.exists()

    def test_generate_compose_file(self):
        """Test docker-compose.yml generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            worktree_dir = Path(tmpdir) / "worktree"
            repo_dir = Path(tmpdir) / "repo.git"

            spec = RepoSpec("owner", "repo", "main", "src")
            extensions = [
                Extension("base", "", {}),
                Extension(
                    "x11",
                    "",
                    {
                        "environment": {"DISPLAY": "${DISPLAY}"},
                        "volumes": ["/tmp/.X11-unix:/tmp/.X11-unix:rw"],
                    },
                ),
            ]

            compose_config_obj = ComposeConfig(
                repo_spec=spec,
                extensions=extensions,
                image_name="test:image",
                work_dir=work_dir,
                worktree_dir=worktree_dir,
                repo_dir=repo_dir,
            )
            compose_config = generate_compose_file(compose_config_obj)

            service = compose_config["services"]["dev"]
            assert service["image"] == "test:image"
            assert service["container_name"] == "repo-main"
            assert service["working_dir"] == "/workspace/repo/src"
            assert service["environment"]["REPO_NAME"] == "repo"
            assert service["environment"]["BRANCH_NAME"] == "main"
            assert service["environment"]["DISPLAY"] == "${DISPLAY}"
            assert "/tmp/.X11-unix:/tmp/.X11-unix:rw" in service["volumes"]
            # Should have 4 volumes: worktree, repo.git, worktree git metadata, and x11
            assert (
                len(
                    [
                        v
                        for v in service["volumes"]
                        if "worktree" in v or "repo.git" in v or "X11" in v
                    ]
                )
                >= 4
            )

            # Check file was written
            compose_file = work_dir / "docker-compose.yml"
            assert compose_file.exists()

    def test_generate_bake_file(self):
        """Test docker-bake.hcl generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            extensions = [
                Extension("base", "FROM ubuntu", {}),
                Extension("git", "RUN apt-get install git", {}),
            ]

            content = generate_bake_file(extensions, "ubuntu:22.04", ["linux/amd64"], work_dir)

            assert 'target "ext-base"' in content
            assert 'target "ext-git"' in content
            assert 'target "final"' in content
            assert '"linux/amd64"' in content

            # Check individual Dockerfiles were created
            assert (work_dir / "Dockerfile.base").exists()
            assert (work_dir / "Dockerfile.git").exists()

            # Check bake file was written
            bake_file = work_dir / "docker-bake.hcl"
            assert bake_file.exists()


class TestDockerOperations:
    """Test Docker operations."""

    @patch("subprocess.run")
    def test_should_rebuild_image_not_exists(self, mock_run):
        """Test rebuild when image doesn't exist."""
        mock_run.return_value = Mock(returncode=1)  # Image doesn't exist

        result = should_rebuild_image("test:image", [])
        assert result is True

    @patch("subprocess.run")
    def test_should_rebuild_image_exists(self, mock_run):
        """Test no rebuild when image exists."""
        mock_run.return_value = Mock(returncode=0)  # Image exists

        result = should_rebuild_image("test:image", [])
        assert result is False

    @patch("subprocess.run")
    def test_build_image_with_bake_success(self, mock_run):
        """Test successful image build with bake."""
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_image_with_bake(Path(tmpdir), "test_builder")
            assert result is True

            call_args = mock_run.call_args[0][0]
            assert "docker" in call_args
            assert "buildx" in call_args
            assert "bake" in call_args
            assert "--builder" in call_args
            assert "test_builder" in call_args
            assert "--load" in call_args

    @patch("subprocess.run")
    def test_list_active_containers(self, mock_run):
        """Test listing active containers."""
        mock_run.return_value = Mock(
            returncode=0, stdout="NAMES\tSTATUS\tIMAGE\ntest-main\tUp 5 minutes\ttest:latest\n"
        )

        containers = list_active_containers()
        assert len(containers) == 1
        assert containers[0]["name"] == "test-main"
        assert containers[0]["status"] == "Up 5 minutes"
        assert containers[0]["image"] == "test:latest"


class TestComposeOperations:
    """Test Docker Compose operations."""

    @patch("subprocess.run")
    @patch("os.getuid", return_value=1000)
    @patch("os.getgid", return_value=1000)
    def test_run_compose_service_interactive(
        self, mock_getgid, mock_getuid, mock_run
    ):  # pylint: disable=unused-argument
        """Test running compose service interactively."""
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            spec = RepoSpec("owner", "repo", "main")
            result = run_compose_service(Path(tmpdir), spec)

            assert result == 0
            # Now includes: inspect + stop + rm + up + git fix + exec = 6 calls
            assert mock_run.call_count >= 4  # At least up + git fix + exec + cleanup calls

            # Find the compose up call (should be after cleanup calls)
            up_calls = [
                call
                for call in mock_run.call_args_list
                if len(call[0]) > 0 and "compose" in call[0][0] and "up" in call[0][0]
            ]
            assert len(up_calls) == 1
            up_call = up_calls[0][0][0]
            assert "docker" in up_call
            assert "compose" in up_call
            assert "up" in up_call
            assert "-d" in up_call

            # Find the git fix call
            git_fix_calls = [
                call
                for call in mock_run.call_args_list
                if len(call[0]) > 0 and "exec" in call[0][0] and "-T" in call[0][0]
            ]
            assert len(git_fix_calls) == 1
            git_fix_call = git_fix_calls[0][0][0]
            assert "docker" in git_fix_call
            assert "compose" in git_fix_call
            assert "exec" in git_fix_call
            assert "-T" in git_fix_call

            # Find the interactive exec call
            exec_calls = [
                call
                for call in mock_run.call_args_list
                if len(call[0]) > 0
                and "exec" in call[0][0]
                and "bash" in call[0][0]
                and "-T" not in call[0][0]
            ]
            assert len(exec_calls) == 1
            exec_call = exec_calls[0][0][0]
            assert "docker" in exec_call
            assert "compose" in exec_call
            assert "exec" in exec_call
            assert "dev" in exec_call
            assert "bash" in exec_call

    @patch("subprocess.run")
    @patch("os.getuid", return_value=1000)
    @patch("os.getgid", return_value=1000)
    def test_run_compose_service_with_command(
        self, mock_getgid, mock_getuid, mock_run
    ):  # pylint: disable=unused-argument
        """Test running compose service with command."""
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            spec = RepoSpec("owner", "repo", "main")
            result = run_compose_service(Path(tmpdir), spec, ["git", "status"])

            assert result == 0

            # Find the command exec call (should have git and status)
            cmd_exec_calls = [
                call
                for call in mock_run.call_args_list
                if len(call[0]) > 0 and "git" in call[0][0] and "status" in call[0][0]
            ]
            assert len(cmd_exec_calls) == 1
            exec_call = cmd_exec_calls[0][0][0]
            assert "git" in exec_call
            assert "status" in exec_call

    @patch("subprocess.run")
    def test_destroy_environment(self, mock_run):
        """Test destroying an environment."""
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create build cache directory
            build_dir = Path(tmpdir) / "build-cache"
            build_dir.mkdir()

            with patch("worktree_docker.renv.get_build_cache_dir", return_value=build_dir):
                spec = RepoSpec("owner", "repo", "main")
                result = destroy_environment(spec)

                assert result is True
                call_args = mock_run.call_args[0][0]
                assert "docker" in call_args
                assert "compose" in call_args
                assert "down" in call_args
                assert "-v" in call_args


class TestCommands:
    """Test CLI command functions."""

    @patch("worktree_docker.renv.launch_environment")
    def test_cmd_launch(self, mock_launch):
        """Test launch command."""
        mock_launch.return_value = 0

        args = Mock()
        args.repo_spec = "owner/repo@main"
        args.extensions = ["git", "x11"]
        args.command = ["bash"]
        args.rebuild = True
        args.no_gui = False
        args.no_gpu = False
        args.platforms = "linux/amd64,linux/arm64"
        args.builder = "custom_builder"

        result = cmd_launch(args)
        assert result == 0

        mock_launch.assert_called_once()
        call_args = mock_launch.call_args[0][0]  # First positional argument (config)
        assert call_args.extensions == ["git", "x11"]
        assert call_args.command == ["bash"]
        assert call_args.rebuild is True
        assert call_args.platforms == ["linux/amd64", "linux/arm64"]
        assert call_args.builder_name == "custom_builder"

    @patch("worktree_docker.renv.list_active_containers")
    def test_cmd_list_empty(self, mock_list_containers):
        """Test list command with no containers."""
        mock_list_containers.return_value = []

        args = Mock()
        result = cmd_list(args)
        assert result == 0

    @patch("worktree_docker.renv.list_active_containers")
    def test_cmd_list_with_containers(self, mock_list_containers):
        """Test list command with containers."""
        mock_list_containers.return_value = [
            {"name": "test-main", "status": "Up", "image": "test:latest"}
        ]

        args = Mock()
        result = cmd_list(args)
        assert result == 0

    @patch("worktree_docker.renv.prune_all")
    @patch("worktree_docker.renv.prune_repo_environment")
    def test_cmd_prune(self, mock_prune_repo, mock_prune_all):
        """Test prune command."""
        mock_prune_all.return_value = 0
        mock_prune_repo.return_value = 0

        # Test general prune (no repo_spec)
        args = Mock()
        args.repo_spec = None
        result = cmd_prune(args)
        assert result == 0
        mock_prune_all.assert_called_once()

        # Test selective prune (with repo_spec)
        mock_prune_all.reset_mock()
        args.repo_spec = "owner/repo"
        result = cmd_prune(args)
        assert result == 0
        mock_prune_repo.assert_called_once()

    @patch("worktree_docker.renv.ExtensionManager")
    def test_cmd_ext_list(self, mock_ext_manager):
        """Test extension list command."""
        mock_manager = Mock()
        mock_manager.list_extensions.return_value = ["base", "git", "x11"]
        mock_ext_manager.return_value = mock_manager

        args = Mock()
        args.ext_action = "list"

        result = cmd_ext(args)
        assert result == 0

    @patch("subprocess.run")
    def test_cmd_doctor_all_good(self, mock_run):
        """Test doctor command when all tools are available."""
        mock_run.return_value = Mock(returncode=0)

        args = Mock()
        result = cmd_doctor(args)
        assert result == 0
        assert mock_run.call_count == 4  # docker, compose, buildx, git

    @patch("subprocess.run")
    def test_cmd_doctor_missing_tools(self, mock_run):
        """Test doctor command when tools are missing."""
        mock_run.side_effect = FileNotFoundError()

        args = Mock()
        result = cmd_doctor(args)
        assert result == 1


class TestMainFunction:
    """Test main entry point."""

    @patch("sys.argv", ["renv", "blooop/test_renv@main"])
    @patch("worktree_docker.renv.cmd_launch")
    def test_main_launch_command(self, mock_cmd_launch):
        """Test main function with launch command."""
        mock_cmd_launch.return_value = 0

        result = main()
        assert result == 0
        mock_cmd_launch.assert_called_once()

    @patch("sys.argv", ["renv", "--list"])
    @patch("worktree_docker.renv.cmd_list")
    def test_main_list_command(self, mock_cmd_list):
        """Test main function with list command."""
        mock_cmd_list.return_value = 0

        result = main()
        assert result == 0
        mock_cmd_list.assert_called_once()

    @patch("sys.argv", ["renv", "--help"])
    def test_main_help(self):
        """Test main function with help."""
        with pytest.raises(SystemExit):
            main()


class TestIntegration:
    """Integration tests for the complete workflow."""

    @patch("subprocess.run")
    @patch("os.getuid", return_value=1000)
    @patch("os.getgid", return_value=1000)
    def test_launch_environment_full_workflow(
        self, mock_getgid, mock_getuid, mock_run
    ):  # pylint: disable=unused-argument
        """Test complete launch environment workflow."""
        # Mock all subprocess calls to succeed
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            worktree_dir = Path(tmpdir) / "worktree"
            repo_dir = Path(tmpdir) / "repo.git"

            # Create directories
            cache_dir.mkdir()
            worktree_dir.mkdir()
            repo_dir.mkdir()

            # Create mock config
            config_file = worktree_dir / ".renv.yml"
            config_file.write_text("extensions: [git, x11]", encoding="utf-8")

            with patch("worktree_docker.renv.get_cache_dir", return_value=cache_dir):
                with patch("worktree_docker.renv.get_worktree_dir", return_value=worktree_dir):
                    with patch("worktree_docker.renv.get_repo_dir", return_value=repo_dir):
                        spec = RepoSpec("owner", "repo", "main")
                        config = LaunchConfig(repo_spec=spec, extensions=["base"], rebuild=True)
                        result = launch_environment(config)

                        assert result == 0

                        # Check that files were created in build cache directory
                        build_dir = cache_dir / "builds" / "owner" / "repo" / "main"
                        assert (build_dir / "Dockerfile").exists()
                        assert (build_dir / "docker-compose.yml").exists()
                        assert (build_dir / "docker-bake.hcl").exists()


class TestCommandParsing:
    """Test command parsing and execution."""

    @patch("subprocess.run")
    @patch("os.getuid", return_value=1000)
    @patch("os.getgid", return_value=1000)
    def test_bash_command_parsing(self, _mock_getgid, _mock_getuid, mock_run):
        """Test that bash -c commands are parsed correctly."""
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            spec = RepoSpec("owner", "repo", "main")
            # Test the problematic command format
            command = ["bash -c 'pixi --version'"]
            result = run_compose_service(Path(tmpdir), spec, command)

            assert result == 0

            # Find the command exec call - should use bash -c format
            # It should be the last call since it's the actual command execution
            user_cmd_calls = [
                call
                for call in mock_run.call_args_list
                if len(call[0]) > 0
                and "exec" in call[0][0]
                and "dev" in call[0][0]
                and "bash -c 'pixi --version'" in call[0][0]
            ]
            assert len(user_cmd_calls) >= 1
            exec_call = user_cmd_calls[-1][0][0]  # Get the last matching call
            assert "docker" in exec_call
            assert "compose" in exec_call
            assert "exec" in exec_call
            assert "dev" in exec_call
            assert "bash" in exec_call
            assert "-c" in exec_call
            assert "bash -c 'pixi --version'" in exec_call

    def test_auto_detect_pixi_extension(self):
        """Test that pixi extension is auto-detected from pixi.toml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            # Create a pixi.toml file
            pixi_toml = repo_path / "pixi.toml"
            pixi_toml.write_text(
                """
[project]
name = "test"
version = "0.1.0"
""",
                encoding="utf-8",
            )

            detected = auto_detect_extensions(repo_path)
            assert "pixi" in detected

    def test_pixi_extension_installation(self):
        """Test that pixi extension has proper installation logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExtensionManager(Path(tmpdir))
            pixi_ext = manager.get_extension("pixi")

            assert pixi_ext is not None
            assert pixi_ext.name == "pixi"
            # Check that the dockerfile includes logic to install as the right user
            assert "if id renv" in pixi_ext.dockerfile_content
            assert "su - renv -c" in pixi_ext.dockerfile_content
            # Check that PATH includes both locations
            assert "/root/.pixi/bin:/home/renv/.pixi/bin" in pixi_ext.dockerfile_content

    @patch("sys.argv", ["renv", "blooop/test_renv", "pixi", "--version"])
    @patch("worktree_docker.renv.cmd_launch")
    def test_command_line_parsing_with_flags(self, mock_cmd_launch):
        """Test that flags in container commands are not parsed as renv flags."""
        mock_cmd_launch.return_value = 0

        result = main()
        assert result == 0
        mock_cmd_launch.assert_called_once()

        # Check that the command includes both pixi and --version
        call_args = mock_cmd_launch.call_args[0][0]  # First positional argument (config)
        assert call_args.command == ["pixi", "--version"]
        assert call_args.repo_spec == "blooop/test_renv"


if __name__ == "__main__":
    pytest.main([__file__])
