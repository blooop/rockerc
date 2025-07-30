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
    setup_bare_repo,
    setup_worktree,
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
        expected = pathlib.Path.home() / "renv" / "blooop" / "test_renv"
        assert repo_dir == expected

    def test_get_worktree_dir(self):
        spec = RepoSpec("blooop", "test_renv", "feature/new")
        worktree_dir = get_worktree_dir(spec)
        expected = pathlib.Path.home() / "renv" / "blooop" / "test_renv" / "worktree-feature-new"
        assert worktree_dir == expected

    def test_get_container_name(self):
        spec = RepoSpec("blooop", "test_renv", "feature/new")
        name = get_container_name(spec)
        assert name == "test_renv-feature-new"


class TestRockerConfig:
    def test_build_rocker_config_basic(self):
        spec = RepoSpec("blooop", "test_renv", "main")
        config = build_rocker_config(spec)

        assert config["image"] == "ubuntu:22.04"
        assert "user" in config["args"]
        assert "pull" in config["args"]
        assert "git" in config["args"]
        assert "git-clone" in config["args"]
        assert config["name"] == "test_renv-main"
        assert config["hostname"] == "test_renv-main"
        assert "/tmp/test_renv.git" in config["volume"]
        assert "/tmp/test_renv" in config["volume"]
        assert "--workdir=/tmp/test_renv" in config["oyr-run-arg"]

    def test_build_rocker_config_with_subfolder(self):
        spec = RepoSpec("blooop", "test_renv", "main", "src")
        config = build_rocker_config(spec)
        assert "--workdir=/tmp/test_renv/src" in config["oyr-run-arg"]

    def test_build_rocker_config_with_force(self):
        # Force rebuild is handled by container removal, not rocker extensions
        spec = RepoSpec("blooop", "test_renv", "main")
        config = build_rocker_config(spec, force=True)
        # Config should be the same regardless of force flag
        assert config["image"] == "ubuntu:22.04"
        assert "user" in config["args"]

    def test_build_rocker_config_with_nocache(self):
        # Nocache is handled at container level, not rocker extensions
        spec = RepoSpec("blooop", "test_renv", "main")
        config = build_rocker_config(spec, nocache=True)
        # Config should be the same regardless of nocache flag
        assert config["image"] == "ubuntu:22.04"
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
    def test_setup_bare_repo_clone(self, mock_exists, mock_run):
        mock_exists.return_value = False
        spec = RepoSpec("blooop", "test_renv", "main")

        result = setup_bare_repo(spec)

        expected_dir = get_repo_dir(spec)
        assert result == expected_dir

        # Check git clone was called
        clone_call = None
        for call in mock_run.call_args_list:
            if "clone" in call[0][0]:
                clone_call = call
                break

        assert clone_call is not None
        assert "git" in clone_call[0][0]
        assert "clone" in clone_call[0][0]
        assert "--bare" in clone_call[0][0]
        assert "https://github.com/blooop/test_renv.git" in clone_call[0][0]

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_bare_repo_fetch(self, mock_exists, mock_run):
        mock_exists.return_value = True
        spec = RepoSpec("blooop", "test_renv", "main")

        setup_bare_repo(spec)

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

    @patch("rockerc.renv.setup_bare_repo")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_worktree_create(self, mock_exists, mock_run, mock_setup_bare):
        mock_exists.return_value = False
        spec = RepoSpec("blooop", "test_renv", "main")

        result = setup_worktree(spec)

        expected_dir = get_worktree_dir(spec)
        assert result == expected_dir

        mock_setup_bare.assert_called_once_with(spec)

        # Check git worktree add was called
        worktree_call = None
        for call in mock_run.call_args_list:
            if "worktree" in call[0][0]:
                worktree_call = call
                break

        assert worktree_call is not None
        assert "git" in worktree_call[0][0]
        assert "worktree" in worktree_call[0][0]
        assert "add" in worktree_call[0][0]


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

    def test_run_renv_no_args(self):
        result = run_renv([])
        assert result == 1

    def test_run_renv_invalid_spec(self):
        result = run_renv(["invalid-spec"])
        assert result == 1


class TestManageContainer:
    @patch("rockerc.renv.setup_worktree")
    def test_manage_container_no_container(self, mock_setup_worktree):
        spec = RepoSpec("blooop", "test_renv", "main")

        result = manage_container(spec, no_container=True)

        assert result == 0
        mock_setup_worktree.assert_called_once_with(spec)

    @patch("rockerc.renv._wait_for_container_running")
    @patch("rockerc.renv.attach_to_container")
    @patch("rockerc.renv.container_running")
    @patch("rockerc.renv.container_exists")
    @patch("rockerc.renv.run_rocker_command")
    @patch("rockerc.renv.setup_worktree")
    def test_manage_container_normal(self, *mocks):
        (
            mock_setup_worktree,  # pylint: disable=unused-variable
            mock_run_rocker,
            mock_container_exists,
            mock_container_running,
            mock_attach,
            mock_wait,
        ) = mocks

        # Set up mocks for new container creation path
        mock_container_exists.return_value = False
        # Mock container_running to return True after container creation
        mock_container_running.return_value = True
        mock_run_rocker.return_value = 0
        mock_attach.return_value = 0
        mock_wait.return_value = 0
        spec = RepoSpec("blooop", "test_renv", "main")

        result = manage_container(spec)

        assert result == 0
        mock_setup_worktree.assert_called_once_with(spec)
        # Should call run_rocker_command for container creation
        assert mock_run_rocker.call_count >= 1

    @patch("rockerc.renv._wait_for_container_running")
    @patch("rockerc.renv.attach_to_container")
    @patch("rockerc.renv.container_running")
    @patch("rockerc.renv.container_exists")
    @patch("rockerc.renv.run_rocker_command")
    @patch("rockerc.renv.setup_worktree")
    def test_manage_container_with_command(self, *mocks):
        (
            mock_setup_worktree,  # pylint: disable=unused-variable
            mock_run_rocker,
            mock_container_exists,
            mock_container_running,
            mock_attach,
            mock_wait,
        ) = mocks

        # Set up mocks for new container creation path
        mock_container_exists.return_value = False
        # Mock container_running to return True after container creation
        mock_container_running.return_value = True
        mock_run_rocker.return_value = 0
        mock_attach.return_value = 0
        mock_wait.return_value = 0
        spec = RepoSpec("blooop", "test_renv", "main")

        result = manage_container(spec, command=["git", "status"])

        assert result == 0

        # Check that run_rocker_command was called for container creation
        assert mock_run_rocker.call_count >= 1
        # The first call should be for creating the persistent container with tail -f /dev/null
        first_call = mock_run_rocker.call_args_list[0]
        assert first_call[0][1] == ["tail", "-f", "/dev/null"]  # Command argument
        assert first_call[1]["detached"]  # Detached mode
