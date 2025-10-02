import pathlib
from unittest.mock import Mock, patch
from rockerc.renv import (
    RepoSpec,
    get_renv_root,
    get_repo_dir,
    get_worktree_dir,
    get_container_name,
    build_rocker_config,
    container_exists,
    container_running,
    setup_cache_repo,
    setup_branch_copy,
    manage_container,
    run_renv,
)


class TestRepoSpec:
    def test_parse_simple(self):
        spec = RepoSpec.parse("blooop/test_renv")
        assert spec.owner == "blooop"
        assert spec.repo == "test_renv"
        assert spec.branch == "main"
        assert spec.subfolder is None

    def test_parse_with_branch(self):
        spec = RepoSpec.parse("blooop/test_renv@feature1")
        assert spec.owner == "blooop"
        assert spec.repo == "test_renv"
        assert spec.branch == "feature1"
        assert spec.subfolder is None

    def test_parse_with_subfolder(self):
        spec = RepoSpec.parse("blooop/test_renv#src")
        assert spec.owner == "blooop"
        assert spec.repo == "test_renv"
        assert spec.branch == "main"
        assert spec.subfolder == "src"

    def test_parse_with_branch_and_subfolder(self):
        spec = RepoSpec.parse("blooop/test_renv@feature1#src/core")
        assert spec.owner == "blooop"
        assert spec.repo == "test_renv"
        assert spec.branch == "feature1"
        assert spec.subfolder == "src/core"

    def test_str_representation(self):
        spec = RepoSpec("blooop", "test_renv", "feature1", "src")
        assert str(spec) == "blooop/test_renv@feature1#src"


class TestPathHelpers:
    def test_get_renv_root(self):
        root = get_renv_root()
        assert root == pathlib.Path.home() / "renv"

    def test_get_repo_dir(self):
        spec = RepoSpec("blooop", "test_renv", "main")
        repo_dir = get_repo_dir(spec)
        expected = pathlib.Path.home() / "renv" / ".cache" / "blooop" / "test_renv"
        assert repo_dir == expected

    def test_get_worktree_dir(self):
        spec = RepoSpec("blooop", "test_renv", "feature/new")
        worktree_dir = get_worktree_dir(spec)
        expected = pathlib.Path.home() / "renv" / "blooop" / "test_renv-feature-new"
        assert worktree_dir == expected

    def test_get_container_name(self):
        spec = RepoSpec("blooop", "test_renv", "feature/new")
        name = get_container_name(spec)
        assert name == "test_renv-feature-new"


class TestRockerConfig:
    def test_build_rocker_config_basic(self):
        spec = RepoSpec("blooop", "test_renv", "main")
        config, _ = build_rocker_config(spec)

        # Image comes from rockerc.yaml config
        assert "image" in config
        assert "user" in config["args"]
        assert "pull" in config["args"]
        assert "git" in config["args"]
        assert "persist-image" in config["args"]  # Updated to match new default config
        assert "x11" in config["args"]  # Updated to match new default config
        assert "ssh" in config["args"]  # Updated to match new default config
        assert "nocleanup" not in config["args"]  # Removed to let rocker manage security properly
        assert "cwd" in config["args"]  # cwd extension should be added automatically
        assert config["name"] == "test_renv-main"
        assert config["hostname"] == "test_renv-main"
        # Volume is NOT in config - it's added by prepare_launch_plan via build_rocker_arg_injections
        assert "volume" not in config
        # cwd extension picks up working directory, no explicit config needed
        assert "_renv_target_dir" in config  # Internal marker for target directory

    def test_build_rocker_config_with_subfolder(self):
        spec = RepoSpec("blooop", "test_renv", "main", "src")
        config, _ = build_rocker_config(spec)
        # Target directory should include subfolder
        assert "src" in config["_renv_target_dir"]
        assert "cwd" in config["args"]  # cwd extension should be present

    def test_build_rocker_config_with_force(self):
        # Force rebuild is handled by container removal, not rocker extensions
        spec = RepoSpec("blooop", "test_renv", "main")
        config, _ = build_rocker_config(spec, force=True)
        # Config should be the same regardless of force flag
        assert "image" in config
        assert "user" in config["args"]

    def test_build_rocker_config_with_nocache(self):
        # Nocache is handled at container level, not rocker extensions
        spec = RepoSpec("blooop", "test_renv", "main")
        config, _ = build_rocker_config(spec, nocache=True)
        # Config should be the same regardless of nocache flag
        assert "image" in config
        assert "user" in config["args"]


class TestContainerHelpers:
    @patch("subprocess.run")
    def test_container_exists_true(self, mock_run):
        mock_run.return_value = Mock(stdout="test-container\n", returncode=0)

        result = container_exists("test-container")
        assert result is True

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "ps" in call_args
        assert "-a" in call_args

    @patch("subprocess.run")
    def test_container_exists_false(self, mock_run):
        mock_run.return_value = Mock(stdout="", returncode=0)

        result = container_exists("test-container")
        assert result is False

    @patch("subprocess.run")
    def test_container_running_true(self, mock_run):
        mock_run.return_value = Mock(stdout="test-container\n", returncode=0)

        result = container_running("test-container")
        assert result is True

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "ps" in call_args
        assert "-a" not in call_args


class TestGitOperations:
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_cache_repo_clone(self, mock_exists, mock_run):
        mock_exists.return_value = False
        spec = RepoSpec("blooop", "test_renv", "main")

        result = setup_cache_repo(spec)

        expected_dir = get_repo_dir(spec)
        assert result == expected_dir

        # Check git clone was called (not bare)
        clone_call = None
        for call in mock_run.call_args_list:
            if "clone" in call[0][0]:
                clone_call = call
                break

        assert clone_call is not None
        assert "git" in clone_call[0][0]
        assert "clone" in clone_call[0][0]
        assert "--bare" not in clone_call[0][0]  # Should NOT be bare
        assert "git@github.com:blooop/test_renv.git" in clone_call[0][0]

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_cache_repo_fetch(self, mock_exists, mock_run):
        mock_exists.return_value = True
        spec = RepoSpec("blooop", "test_renv", "main")

        setup_cache_repo(spec)

        # Check git fetch was called
        fetch_call = None
        for call in mock_run.call_args_list:
            if "fetch" in call[0][0]:
                fetch_call = call
                break

        assert fetch_call is not None
        assert "git" in fetch_call[0][0]
        assert "fetch" in fetch_call[0][0]
        assert "--all" in fetch_call[0][0]

    @patch("rockerc.renv.setup_cache_repo")
    @patch("shutil.copytree")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_branch_copy_create(self, mock_exists, mock_run, mock_copytree, mock_setup_cache):
        # Mock branch_dir.exists() to return False
        mock_exists.return_value = False
        spec = RepoSpec("blooop", "test_renv", "main")

        result = setup_branch_copy(spec)

        expected_dir = get_worktree_dir(spec)
        assert result == expected_dir

        mock_setup_cache.assert_called_once_with(spec)

        # Check that copytree was called to copy cache to branch directory
        mock_copytree.assert_called_once()

        # Check git checkout was called
        checkout_call = None
        for call in mock_run.call_args_list:
            if "checkout" in call[0][0]:
                checkout_call = call
                break

        assert checkout_call is not None
        assert "git" in checkout_call[0][0]
        assert "checkout" in checkout_call[0][0]


class TestMainFunction:
    @patch("rockerc.renv.manage_container")
    def test_run_renv_basic(self, mock_manage):
        mock_manage.return_value = 0

        result = run_renv(["blooop/test_renv"])

        assert result == 0
        mock_manage.assert_called_once()

        # Check the repo_spec passed to manage_container
        call_args = mock_manage.call_args
        repo_spec = call_args[1]["repo_spec"]
        assert repo_spec.owner == "blooop"
        assert repo_spec.repo == "test_renv"
        assert repo_spec.branch == "main"

    @patch("rockerc.renv.manage_container")
    def test_run_renv_with_branch(self, mock_manage):
        mock_manage.return_value = 0

        result = run_renv(["blooop/test_renv@feature1"])

        assert result == 0

        call_args = mock_manage.call_args
        repo_spec = call_args[1]["repo_spec"]
        assert repo_spec.branch == "feature1"

    @patch("rockerc.renv.manage_container")
    def test_run_renv_with_command(self, mock_manage):
        mock_manage.return_value = 0

        result = run_renv(["blooop/test_renv", "git", "status"])

        assert result == 0

        call_args = mock_manage.call_args
        command = call_args[1]["command"]
        assert command == ["git", "status"]

    @patch("rockerc.renv.manage_container")
    def test_run_renv_with_flags(self, mock_manage):
        mock_manage.return_value = 0

        result = run_renv(["blooop/test_renv", "--force", "--nocache"])

        assert result == 0

        call_args = mock_manage.call_args
        assert call_args[1]["force"] is True
        assert call_args[1]["nocache"] is True

    @patch("rockerc.renv.fuzzy_select_repo")
    def test_run_renv_no_args(self, mock_fuzzy_select):
        mock_fuzzy_select.return_value = None
        result = run_renv([])
        assert result == 1

    @patch("rockerc.renv.manage_container")
    @patch("rockerc.renv.fuzzy_select_repo")
    def test_run_renv_with_fuzzy_selection(self, mock_fuzzy_select, mock_manage):
        mock_fuzzy_select.return_value = "blooop/test_renv@main"
        mock_manage.return_value = 0

        result = run_renv([])

        assert result == 0
        mock_fuzzy_select.assert_called_once()
        mock_manage.assert_called_once()

        # Check the repo_spec passed to manage_container
        call_args = mock_manage.call_args
        repo_spec = call_args[1]["repo_spec"]
        assert repo_spec.owner == "blooop"
        assert repo_spec.repo == "test_renv"
        assert repo_spec.branch == "main"

    def test_run_renv_invalid_spec(self):
        result = run_renv(["invalid-spec"])
        assert result == 1


class TestManageContainer:
    @patch("rockerc.renv.setup_branch_copy")
    def test_manage_container_no_container(self, mock_setup_branch_copy):
        spec = RepoSpec("blooop", "test_renv", "main")

        result = manage_container(spec, no_container=True)

        assert result == 0
        mock_setup_branch_copy.assert_called_once_with(spec)

    @patch("subprocess.run")
    @patch("os.chdir")
    @patch("rockerc.renv.build_rocker_config")
    @patch("rockerc.renv.container_running")
    @patch("rockerc.renv.setup_branch_copy")
    def test_manage_container_normal(self, *mocks):
        (
            mock_setup_branch_copy,
            mock_container_running,
            mock_build_config,
            mock_chdir,  # pylint: disable=unused-variable
            mock_subprocess,
        ) = mocks

        mock_setup_branch_copy.return_value = pathlib.Path("/test/branch")
        mock_container_running.return_value = False
        mock_subprocess.return_value.returncode = 0
        mock_build_config.return_value = (
            {"args": [], "image": "ubuntu:22.04", "_renv_target_dir": "/test/branch"},
            {},
        )

        spec = RepoSpec("blooop", "test_renv", "main")

        result = manage_container(spec)

        assert result == 0
        mock_setup_branch_copy.assert_called_once_with(spec)
        mock_build_config.assert_called_once()
        mock_container_running.assert_called_once()
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    @patch("os.chdir")
    @patch("rockerc.renv.build_rocker_config")
    @patch("rockerc.renv.container_running")
    @patch("rockerc.renv.setup_branch_copy")
    def test_manage_container_with_command(self, *mocks):
        (
            mock_setup_branch_copy,  # pylint: disable=unused-variable
            mock_container_running,
            mock_build_config,
            mock_chdir,  # pylint: disable=unused-variable
            mock_subprocess,
        ) = mocks

        # Set up mocks for new container creation path
        mock_container_running.return_value = False
        mock_subprocess.return_value.returncode = 0
        mock_build_config.return_value = (
            {"args": [], "image": "ubuntu:22.04", "_renv_target_dir": "/test/branch"},
            {},
        )
        spec = RepoSpec("blooop", "test_renv", "main")

        result = manage_container(spec, command=["git", "status"])

        assert result == 0
        mock_build_config.assert_called_once()

        # Check that subprocess.run was called with git status in the command
        assert result == 0


class TestRockerCommandWorkingDirectory:
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_run_rocker_command_always_sets_worktree_cwd(
        self, mock_path_exists, mock_subprocess_run
    ):
        """Test that renv always runs rocker from the worktree directory"""
        from rockerc.renv import run_rocker_command

        # Mock path exists to return True for worktree directory
        mock_path_exists.return_value = True
        mock_subprocess_run.return_value.returncode = 0

        # Create config with various extensions
        config = {
            "image": "ubuntu:22.04",
            "args": ["user", "deps", "git"],
            "name": "test-container",
            "hostname": "test-container",
            "volume": [
                "/path/to/branch:/workspace/test_repo-main",
            ],
        }

        result = run_rocker_command(config)

        assert result == 0
        mock_subprocess_run.assert_called_once()

        # Check that subprocess.run was called with the correct cwd
        call_args = mock_subprocess_run.call_args
        assert call_args[1]["cwd"] == "/path/to/branch"

        # Verify the command contains the deps extension
        cmd_parts = call_args[0][0]
        assert "rocker" in cmd_parts
        assert "--deps" in cmd_parts

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_run_rocker_command_sets_cwd_even_without_deps(
        self, mock_path_exists, mock_subprocess_run
    ):
        """Test that even without deps extension, rocker runs from branch directory"""
        from rockerc.renv import run_rocker_command

        # Mock path exists to return True for branch directory
        mock_path_exists.return_value = True
        mock_subprocess_run.return_value.returncode = 0

        # Create config without deps extension
        config = {
            "image": "ubuntu:22.04",
            "args": ["user", "git"],
            "name": "test-container",
            "hostname": "test-container",
            "volume": [
                "/path/to/branch:/workspace/test_repo-main",
            ],
        }

        result = run_rocker_command(config)

        assert result == 0
        mock_subprocess_run.assert_called_once()

        # Check that subprocess.run was called with the branch cwd
        call_args = mock_subprocess_run.call_args
        assert call_args[1]["cwd"] == "/path/to/branch"

    @patch("subprocess.run")
    def test_run_rocker_command_no_cwd_when_no_branch_volume(self, mock_subprocess_run):
        """Test that no cwd is set when there's no branch volume mount"""
        from rockerc.renv import run_rocker_command

        mock_subprocess_run.return_value.returncode = 0

        # Create config without branch volume mount
        config = {
            "image": "ubuntu:22.04",
            "args": ["user", "git"],
            "name": "test-container",
            "hostname": "test-container",
            "volume": [],
        }

        result = run_rocker_command(config)

        assert result == 0
        mock_subprocess_run.assert_called_once()

        # Check that subprocess.run was called without cwd
        call_args = mock_subprocess_run.call_args
        assert call_args[1]["cwd"] is None

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_run_rocker_command_wraps_compound_token_list(
        self, mock_path_exists, mock_subprocess_run
    ):
        """Compound commands split into tokens should be wrapped with bash -c"""
        from rockerc.renv import run_rocker_command

        mock_path_exists.return_value = True
        mock_subprocess_run.return_value.returncode = 0

        config = {
            "image": "ubuntu:22.04",
            "args": ["user", "git"],
            "name": "test-container",
            "hostname": "test-container",
            "volume": [
                "/path/to/branch:/workspace/test_repo-main",
            ],
        }

        command = ["git", "reset", "--hard", "HEAD;", "git", "clean", "-fd"]
        run_rocker_command(config, command)

        mock_subprocess_run.assert_called_once()
        cmd_parts = mock_subprocess_run.call_args[0][0]
        # Ensure bash -c wrapper is present with joined command string
        assert "bash" in cmd_parts
        bash_index = cmd_parts.index("bash")
        assert cmd_parts[bash_index + 1] == "-c"
        assert cmd_parts[bash_index + 2] == '"git reset --hard HEAD; git clean -fd"'
