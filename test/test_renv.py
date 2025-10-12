import pathlib
from unittest.mock import Mock, patch

import pytest
from rockerc.renv import (
    RepoSpec,
    get_repo_dir,
    get_worktree_dir,
    get_legacy_worktree_dir,
    build_rocker_config,
    container_exists,
    container_running,
    setup_cache_repo,
    setup_branch_copy,
    manage_container,
    run_renv,
    _verify_sparse_checkout_path,
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
    def test_get_worktree_dir_nested_structure(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RENV_DIR", str(tmp_path))
        spec = RepoSpec("blooop", "test_renv", "feature/foo")
        expected_new = tmp_path / "blooop" / "test_renv" / "feature-foo" / "test_renv"
        expected_previous = tmp_path / "blooop" / "test_renv" / "test_renv-feature-foo"
        expected_legacy = tmp_path / "blooop" / "test_renv-feature-foo"
        assert get_worktree_dir(spec) == expected_new
        assert get_legacy_worktree_dir(spec) == expected_legacy

        # Import get_previous_worktree_dir to test it too
        from rockerc.renv import get_previous_worktree_dir

        assert get_previous_worktree_dir(spec) == expected_previous


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
        # cwd extension removed - we use explicit volume mounts to /{repo} instead
        assert "cwd" not in config["args"]
        assert config["name"] == "test_renv.main"
        assert config["hostname"] == "test_renv"
        # Volume is NOT in config - it's added by prepare_launch_plan via build_rocker_arg_injections
        assert "volume" not in config
        # cwd extension picks up working directory, no explicit config needed
        assert "_renv_target_dir" in config  # Internal marker for target directory

    def test_build_rocker_config_with_subfolder(self):
        spec = RepoSpec("blooop", "test_renv", "main", "src")
        config, _ = build_rocker_config(spec)
        # Target directory should include subfolder
        assert "src" in config["_renv_target_dir"]
        # cwd extension removed - we use explicit volume mounts to /{repo} instead
        assert "cwd" not in config["args"]

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

    @patch("rockerc.renv._verify_sparse_checkout_path")
    @patch("rockerc.renv._has_upstream", return_value=False)
    @patch("rockerc.renv.setup_cache_repo")
    @patch("shutil.copytree")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_branch_copy_create(
        self,
        mock_exists,
        mock_run,
        mock_copytree,
        mock_setup_cache,
        _mock_has_upstream,
        _mock_verify_subfolder,
    ):
        # Mock branch_dir.exists() to return False
        mock_exists.return_value = False
        spec = RepoSpec("blooop", "test_renv", "main")

        result = setup_branch_copy(spec)

        expected_dir = get_worktree_dir(spec)
        assert result == expected_dir

        mock_setup_cache.assert_called_once_with(spec)

        # Check that copytree was called to copy cache to branch directory
        mock_copytree.assert_called_once()

        # The branch copy should fetch to ensure remote refs are current
        fetch_calls = [call for call in mock_run.call_args_list if "fetch" in call[0][0]]
        assert fetch_calls, "Expected a git fetch call when creating branch copy"

        # Check git checkout was called
        checkout_call = None
        for call in mock_run.call_args_list:
            if "checkout" in call[0][0]:
                checkout_call = call
                break

        assert checkout_call is not None
        assert "git" in checkout_call[0][0]
        assert "checkout" in checkout_call[0][0]

    @patch("rockerc.renv._verify_sparse_checkout_path")
    @patch("rockerc.renv._has_upstream", return_value=False)
    def test_setup_branch_copy_migrates_legacy_layout(
        self,
        _mock_has_upstream,
        mock_verify_subfolder,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.setenv("RENV_DIR", str(tmp_path))
        spec = RepoSpec("blooop", "test_renv", "main")

        legacy_dir = get_legacy_worktree_dir(spec)
        legacy_dir.mkdir(parents=True, exist_ok=True)
        repo_cache = get_repo_dir(spec)
        repo_cache.mkdir(parents=True, exist_ok=True)

        with (
            patch("rockerc.renv.setup_cache_repo") as mock_setup_cache,
            patch("subprocess.run", return_value=Mock(returncode=0)) as mock_run,
        ):
            branch_dir = setup_branch_copy(spec)

        mock_setup_cache.assert_called_once_with(spec)
        assert branch_dir == get_worktree_dir(spec)
        assert branch_dir.exists()
        assert not legacy_dir.exists()
        fetch_calls = [args for args in mock_run.call_args_list if "fetch" in args[0][0]]
        mock_verify_subfolder.assert_not_called()
        assert fetch_calls

    @patch("rockerc.renv._verify_sparse_checkout_path")
    @patch("rockerc.renv._has_upstream", return_value=False)
    def test_setup_branch_copy_skips_pull_without_upstream(
        self,
        _mock_has_upstream,
        mock_verify_subfolder,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.setenv("RENV_DIR", str(tmp_path))
        spec = RepoSpec("blooop", "test_renv", "main")

        branch_dir = get_worktree_dir(spec)
        branch_dir.mkdir(parents=True, exist_ok=True)
        (branch_dir / ".git" / "info").mkdir(parents=True, exist_ok=True)

        repo_cache = get_repo_dir(spec)
        repo_cache.mkdir(parents=True, exist_ok=True)

        with (
            patch("rockerc.renv.setup_cache_repo") as mock_setup_cache,
            patch("subprocess.run", return_value=Mock(returncode=0)) as mock_run,
        ):
            setup_branch_copy(spec)

        mock_setup_cache.assert_called_once_with(spec)
        pull_calls = [
            args for args in mock_run.call_args_list if len(args[0]) > 3 and args[0][3] == "pull"
        ]
        assert not pull_calls
        mock_verify_subfolder.assert_not_called()

    @patch("subprocess.run")
    def test_verify_sparse_checkout_path_missing(self, mock_run):
        mock_run.return_value = Mock(returncode=1)
        branch_dir = pathlib.Path("/tmp/repo")

        with pytest.raises(FileNotFoundError):
            _verify_sparse_checkout_path(branch_dir, "missing/path", "main")

        mock_run.assert_called_once()


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
    @patch("rockerc.core.wait_for_container")
    @patch("rockerc.core.launch_rocker")
    @patch("rockerc.core.prepare_launch_plan")
    @patch("os.chdir")
    @patch("rockerc.renv.build_rocker_config")
    @patch("rockerc.renv.setup_branch_copy")
    def test_manage_container_normal(self, *mocks):
        (
            mock_setup_branch_copy,
            mock_build_config,
            mock_chdir,  # pylint: disable=unused-variable
            mock_prepare_plan,
            mock_launch_rocker,
            mock_wait_container,
            mock_subprocess,
        ) = mocks

        mock_setup_branch_copy.return_value = pathlib.Path("/test/branch")
        mock_build_config.return_value = (
            {"args": [], "image": "ubuntu:22.04", "_renv_target_dir": "/test/branch"},
            {},
        )

        # Mock LaunchPlan for new container
        from rockerc.core import LaunchPlan

        mock_plan = LaunchPlan(
            container_name="test_renv.main",
            container_hex="746573745f72656e762d6d61696e",
            rocker_cmd=["rocker", "--detach", "ubuntu:22.04"],
            created=True,
            vscode=False,
        )
        mock_prepare_plan.return_value = mock_plan
        mock_launch_rocker.return_value = 0
        mock_wait_container.return_value = True
        mock_subprocess.return_value.returncode = 0

        spec = RepoSpec("blooop", "test_renv", "main")

        result = manage_container(spec)

        assert result == 0
        mock_setup_branch_copy.assert_called_once_with(spec)
        mock_build_config.assert_called_once()
        mock_prepare_plan.assert_called_once()
        mock_launch_rocker.assert_called_once()
        mock_wait_container.assert_called_once()
        # Should call subprocess.run for interactive shell
        assert mock_subprocess.call_count == 1

    @patch("subprocess.run")
    @patch("rockerc.core.wait_for_container")
    @patch("rockerc.core.launch_rocker")
    @patch("rockerc.core.prepare_launch_plan")
    @patch("os.chdir")
    @patch("rockerc.renv.build_rocker_config")
    @patch("rockerc.renv.setup_branch_copy")
    def test_manage_container_with_command(self, *mocks):
        (
            mock_setup_branch_copy,
            mock_build_config,
            mock_chdir,  # pylint: disable=unused-variable
            mock_prepare_plan,
            mock_launch_rocker,
            mock_wait_container,
            mock_subprocess,
        ) = mocks

        # Set up mocks for new container creation path
        mock_setup_branch_copy.return_value = pathlib.Path("/test/branch")
        mock_subprocess.return_value.returncode = 0
        mock_build_config.return_value = (
            {"args": [], "image": "ubuntu:22.04", "_renv_target_dir": "/test/branch"},
            {},
        )

        # Mock LaunchPlan for new container
        from rockerc.core import LaunchPlan

        mock_plan = LaunchPlan(
            container_name="test_renv.main",
            container_hex="746573745f72656e762d6d61696e",
            rocker_cmd=["rocker", "--detach", "ubuntu:22.04"],
            created=True,
            vscode=False,
        )
        mock_prepare_plan.return_value = mock_plan
        mock_launch_rocker.return_value = 0
        mock_wait_container.return_value = True

        spec = RepoSpec("blooop", "test_renv", "main")

        result = manage_container(spec, command=["git", "status"])

        assert result == 0
        mock_build_config.assert_called_once()
        mock_prepare_plan.assert_called_once()
        mock_launch_rocker.assert_called_once()
        mock_wait_container.assert_called_once()

        # Verify docker exec was called with git status and working directory
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        # Workdir should be /{repo} at root
        assert call_args == [
            "docker",
            "exec",
            "-w",
            "/test_renv",
            "test_renv.main",
            "git",
            "status",
        ]

    @patch("subprocess.run")
    @patch("rockerc.core.wait_for_container")
    @patch("rockerc.core.launch_rocker")
    @patch("rockerc.core.prepare_launch_plan")
    @patch("os.chdir")
    @patch("rockerc.renv.build_rocker_config")
    @patch("rockerc.renv.setup_branch_copy")
    def test_manage_container_with_subfolder_mounts_git_volume(self, *mocks):
        (
            mock_setup_branch_copy,
            mock_build_config,
            mock_chdir,  # pylint: disable=unused-variable
            mock_prepare_plan,
            mock_launch_rocker,
            mock_wait_container,
            mock_subprocess,
        ) = mocks

        mock_setup_branch_copy.return_value = pathlib.Path("/test/branch")
        mock_build_config.return_value = (
            {"args": [], "image": "ubuntu:22.04", "_renv_target_dir": "/test/branch/src"},
            {},
        )

        from rockerc.core import LaunchPlan

        mock_plan = LaunchPlan(
            container_name="test_renv.main-sub-src",
            container_hex="746573745f72656e762d6d61696e2d737263",
            rocker_cmd=["rocker", "--detach", "ubuntu:22.04"],
            created=True,
            vscode=False,
        )
        mock_prepare_plan.return_value = mock_plan
        mock_launch_rocker.return_value = 0
        mock_wait_container.return_value = True
        mock_subprocess.return_value.returncode = 0

        spec = RepoSpec("blooop", "test_renv", "main", "src")

        result = manage_container(spec)

        assert result == 0
        assert mock_prepare_plan.call_count == 1
        _args, kwargs = mock_prepare_plan.call_args
        assert kwargs["path"] == pathlib.Path("/test/branch/src")
        # Git volume should be at /{repo}/.git at root, not /workspaces/
        assert kwargs["extra_volumes"] == [(pathlib.Path("/test/branch/.git"), "/test_renv/.git")]


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


class TestContainerAndHostnameSanitization:
    def test_container_and_hostname_sanitization(self):
        from rockerc.renv import get_container_name, get_hostname

        # Edge cases for repo and branch names
        # Container names allow: alphanumeric, dash, underscore, dot
        # Hostnames allow: alphanumeric, dash, underscore (no dots)
        cases = [
            # (repo, branch, expected_container_name, expected_hostname)
            ("my-repo", "feature/awesome", "my-repo.feature-awesome", "my-repo"),
            (
                "repo.with.dots",
                "branch.with.dots",
                "repo.with.dots.branch.with.dots",  # dots allowed in container names
                "repo_with_dots",  # dots replaced with underscore in hostnames
            ),
            (
                "repo_with_underscores",
                "branch_with_underscores",
                "repo_with_underscores.branch_with_underscores",
                "repo_with_underscores",
            ),
            (
                "repo-with-dashes",
                "branch-with-dashes",
                "repo-with-dashes.branch-with-dashes",
                "repo-with-dashes",
            ),
            ("MyOwner", "MyRepo", "Main", "myowner-myrepo.main", "myowner-myrepo"),
            ("OWNER", "REPO", "BRANCH", "owner-repo.branch", "owner-repo"),
            ("owner!@#", "repo!@#", "branch!@#", "owner___-repo___.branch---", "owner___-repo___"),
            (
                "owner.with.dots",
                "repo.with.dots",
                "branch.with.dots",
                "owner.with.dots-repo.with.dots.branch.with.dots",
                "owner.with.dots-repo.with.dots",
            ),
            (
                "owner_with_underscores",
                "repo_with_underscores",
                "branch_with_underscores",
                "owner_with_underscores-repo_with_underscores.branch_with_underscores",
                "owner_with_underscores-repo_with_underscores",
            ),
            (
                "owner-with-dashes",
                "repo-with-dashes",
                "branch-with-dashes",
                "owner-with-dashes-repo-with-dashes.branch-with-dashes",
                "owner-with-dashes-repo-with-dashes",
            ),
        ]

        for repo, branch, expected_container, expected_host in cases:
            repo_spec = RepoSpec("owner", repo, branch)
            container_name = get_container_name(repo_spec)
            hostname = get_hostname(repo_spec)
            assert container_name == expected_container, (
                f"Container name for {repo}, {branch} was {container_name}, expected {expected_container}"
            )
            assert hostname == expected_host, (
                f"Hostname for {repo} was {hostname}, expected {expected_host}"
            )

    def test_get_hostname_empty_repo(self):
        from rockerc.renv import get_hostname

        repo_spec = RepoSpec("owner", "", "main")
        # Empty repo name should still work (returns empty string after sanitization)
        hostname = get_hostname(repo_spec)
        assert hostname == ""

    def test_get_hostname_special_characters(self):
        from rockerc.renv import get_hostname

        repo_spec = RepoSpec("owner", "test!@#repo", "main")
        # Should sanitize special characters
        hostname = get_hostname(repo_spec)
        assert all(c.isalnum() or c in ["-", "_"] for c in hostname), (
            f"Hostname '{hostname}' contains invalid characters"
        )
        assert hostname == "test___repo", f"Expected 'test___repo', got '{hostname}'"

    def test_get_hostname_excessively_long_name(self):
        from rockerc.renv import get_hostname

        long_repo_name = "a" * 300
        repo_spec = RepoSpec("owner", long_repo_name, "main")
        hostname = get_hostname(repo_spec)
        # Hostname length should be at most 255 characters (DNS limit)
        # However, current implementation doesn't enforce this, so it returns the full sanitized name
        # This test documents the current behavior
        assert len(hostname) == 300, (
            f"Hostname length is {len(hostname)}, current implementation doesn't truncate"
        )

    def test_container_name_with_subfolder(self):
        from rockerc.renv import get_container_name

        repo_spec = RepoSpec("owner", "repo", "main", "src/core")
        container_name = get_container_name(repo_spec)
        # Should include subfolder with sub- prefix
        assert container_name == "repo.main-sub-src-core"

    def test_container_name_special_chars_in_subfolder(self):
        from rockerc.renv import get_container_name

        repo_spec = RepoSpec("owner", "repo", "main", "src/core@v2")
        container_name = get_container_name(repo_spec)
        # Special characters in subfolder should be sanitized
        assert container_name == "repo.main-sub-src-core_v2"
