import pathlib
from unittest.mock import patch
from rockerc.renv import (
    RepoSpec,
    get_workspaces_dir,
    get_repo_dir,
    get_worktree_dir,
    setup_bare_repo,
    setup_worktree,
    main as run_renv,
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
    def test_get_workspaces_dir(self):
        with patch("rockerc.renv.get_cache_dir", return_value=pathlib.Path("/cache")):
            workspaces = get_workspaces_dir()
            assert workspaces == pathlib.Path("/cache/workspaces")

    def test_get_repo_dir(self):
        spec = RepoSpec("blooop", "test_renv", "main")
        with patch("rockerc.renv.get_workspaces_dir", return_value=pathlib.Path("/workspaces")):
            repo_dir = get_repo_dir(spec)
            expected = pathlib.Path("/workspaces/blooop/test_renv")
            assert repo_dir == expected

    def test_get_worktree_dir(self):
        spec = RepoSpec("blooop", "test_renv", "feature/new")
        with patch("rockerc.renv.get_repo_dir", return_value=pathlib.Path("/repo")):
            worktree_dir = get_worktree_dir(spec)
            expected = pathlib.Path("/repo/worktree-feature-new")
            assert worktree_dir == expected

    def test_compose_project_name(self):
        spec = RepoSpec("blooop", "test_renv", "feature/new")
        name = spec.compose_project_name
        assert name == "test_renv-feature-new"


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
        assert "git@github.com:blooop/test_renv.git" in clone_call[0][0]

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
    @patch("sys.argv", ["renv", "blooop/test_renv@main"])
    @patch("rockerc.renv.launch_environment")
    def test_run_renv_basic(self, mock_launch):
        mock_launch.return_value = 0

        result = run_renv()

        assert result == 0
        mock_launch.assert_called_once()
