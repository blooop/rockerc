"""Tests for dl (DevLaunch CLI) functionality."""

import json
from unittest.mock import patch, MagicMock

from rockerc.dl import (
    expand_workspace_spec,
    is_path_spec,
    is_git_spec,
    validate_workspace_spec,
    parse_owner_repo_from_url,
    discover_repos_from_workspaces,
    get_known_repos,
    Workspace,
    list_workspaces,
    get_workspace_ids,
    OWNER_REPO_PATTERN,
)


class TestIsPathSpec:
    """Tests for is_path_spec function."""

    def test_dot_slash_is_path(self):
        """Test ./path is recognized as path."""
        assert is_path_spec("./my-project")

    def test_absolute_is_path(self):
        """Test /path is recognized as path."""
        assert is_path_spec("/home/user/project")

    def test_tilde_is_path(self):
        """Test ~/path is recognized as path."""
        assert is_path_spec("~/projects/test")

    def test_simple_name_not_path(self):
        """Test simple name is not a path."""
        assert not is_path_spec("myworkspace")

    def test_owner_repo_not_path(self):
        """Test owner/repo is not a path."""
        assert not is_path_spec("owner/repo")


class TestIsGitSpec:
    """Tests for is_git_spec function."""

    def test_owner_repo_is_git(self):
        """Test owner/repo is recognized as git."""
        assert is_git_spec("owner/repo")

    def test_owner_repo_with_branch_is_git(self):
        """Test owner/repo@branch is recognized as git."""
        assert is_git_spec("blooop/rockerc@main")

    def test_github_url_is_git(self):
        """Test github.com URL is recognized as git."""
        assert is_git_spec("github.com/owner/repo")

    def test_gitlab_url_is_git(self):
        """Test gitlab.com URL is recognized as git."""
        assert is_git_spec("gitlab.com/owner/repo")

    def test_https_url_is_git(self):
        """Test https URL is recognized as git."""
        assert is_git_spec("https://github.com/owner/repo")

    def test_simple_name_not_git(self):
        """Test simple name is not git."""
        assert not is_git_spec("myworkspace")

    def test_path_not_git(self):
        """Test path is not git."""
        assert not is_git_spec("./my-project")


class TestValidateWorkspaceSpec:
    """Tests for validate_workspace_spec function."""

    def test_existing_workspace_valid(self):
        """Test existing workspace name is valid."""
        error = validate_workspace_spec("myws", ["myws", "other"])
        assert error is None

    def test_owner_repo_valid(self):
        """Test owner/repo is valid even if not existing."""
        error = validate_workspace_spec("owner/repo", [])
        assert error is None

    def test_owner_repo_with_branch_valid(self):
        """Test owner/repo@branch is valid."""
        error = validate_workspace_spec("blooop/rockerc@main", [])
        assert error is None

    def test_path_valid(self):
        """Test path is valid even if not existing."""
        error = validate_workspace_spec("./my-project", [])
        assert error is None

    def test_unknown_name_invalid(self):
        """Test unknown simple name returns error."""
        error = validate_workspace_spec("blo", ["myws", "other"])
        assert error is not None
        assert "Unknown workspace 'blo'" in error

    def test_partial_name_invalid(self):
        """Test partial match is not valid."""
        error = validate_workspace_spec("my", ["myws", "myother"])
        assert error is not None


class TestExpandWorkspaceSpec:
    """Tests for expand_workspace_spec function."""

    def test_expand_owner_repo(self):
        """Test owner/repo expands to github.com/owner/repo."""
        assert expand_workspace_spec("loft-sh/devpod") == "github.com/loft-sh/devpod"

    def test_expand_owner_repo_with_branch(self):
        """Test owner/repo@branch expands correctly."""
        assert expand_workspace_spec("blooop/rockerc@main") == "github.com/blooop/rockerc@main"

    def test_expand_owner_repo_with_feature_branch(self):
        """Test owner/repo@feature/branch expands correctly."""
        assert (
            expand_workspace_spec("owner/repo@feature/my-branch")
            == "github.com/owner/repo@feature/my-branch"
        )

    def test_no_expand_local_path_dot(self):
        """Test ./path is not expanded."""
        assert expand_workspace_spec("./my-project") == "./my-project"

    def test_no_expand_local_path_absolute(self):
        """Test /path is not expanded."""
        assert expand_workspace_spec("/home/user/project") == "/home/user/project"

    def test_no_expand_local_path_tilde(self):
        """Test ~/path is not expanded."""
        assert expand_workspace_spec("~/projects/test") == "~/projects/test"

    def test_no_expand_github_url(self):
        """Test github.com/ URLs are not double-expanded."""
        assert expand_workspace_spec("github.com/owner/repo") == "github.com/owner/repo"

    def test_no_expand_gitlab_url(self):
        """Test gitlab.com/ URLs are not expanded."""
        assert expand_workspace_spec("gitlab.com/owner/repo") == "gitlab.com/owner/repo"

    def test_no_expand_full_url(self):
        """Test full URLs with protocol are not expanded."""
        assert (
            expand_workspace_spec("https://github.com/owner/repo")
            == "https://github.com/owner/repo"
        )

    def test_no_expand_workspace_name(self):
        """Test simple workspace names are not expanded."""
        assert expand_workspace_spec("myworkspace") == "myworkspace"

    def test_no_expand_workspace_with_dashes(self):
        """Test workspace names with dashes are not expanded."""
        assert expand_workspace_spec("my-workspace") == "my-workspace"


class TestOwnerRepoPattern:
    """Tests for the OWNER_REPO_PATTERN regex."""

    def test_matches_simple(self):
        """Test simple owner/repo matches."""
        assert OWNER_REPO_PATTERN.match("owner/repo")

    def test_matches_with_dashes(self):
        """Test owner/repo with dashes matches."""
        assert OWNER_REPO_PATTERN.match("loft-sh/devpod")

    def test_matches_with_dots(self):
        """Test owner/repo with dots matches."""
        assert OWNER_REPO_PATTERN.match("user.name/repo.name")

    def test_matches_with_underscores(self):
        """Test owner/repo with underscores matches."""
        assert OWNER_REPO_PATTERN.match("my_user/my_repo")

    def test_matches_with_branch(self):
        """Test owner/repo@branch matches."""
        assert OWNER_REPO_PATTERN.match("owner/repo@main")

    def test_matches_with_feature_branch(self):
        """Test owner/repo@feature/branch matches."""
        assert OWNER_REPO_PATTERN.match("owner/repo@feature/my-feature")

    def test_no_match_single_word(self):
        """Test single word doesn't match."""
        assert not OWNER_REPO_PATTERN.match("workspace")

    def test_no_match_path(self):
        """Test path doesn't match."""
        assert not OWNER_REPO_PATTERN.match("./path/to/project")

    def test_no_match_absolute_path(self):
        """Test absolute path doesn't match."""
        assert not OWNER_REPO_PATTERN.match("/home/user/project")


class TestWorkspace:
    """Tests for Workspace dataclass."""

    def test_from_json_local_folder(self):
        """Test parsing workspace with local folder source."""
        data = {
            "id": "myproject",
            "source": {"localFolder": "/home/user/myproject"},
            "lastUsed": "2024-01-01T12:00:00Z",
            "provider": {"name": "docker"},
            "ide": {"name": "vscode"},
        }
        ws = Workspace.from_json(data)
        assert ws.id == "myproject"
        assert ws.source_type == "local"
        assert ws.source == "/home/user/myproject"
        assert ws.provider == "docker"
        assert ws.ide == "vscode"

    def test_from_json_git_repository(self):
        """Test parsing workspace with git repository source."""
        data = {
            "id": "devpod",
            "source": {"gitRepository": "github.com/loft-sh/devpod"},
            "lastUsed": "2024-01-01T12:00:00Z",
            "provider": {"name": "docker"},
            "ide": {"name": "none"},
        }
        ws = Workspace.from_json(data)
        assert ws.id == "devpod"
        assert ws.source_type == "git"
        assert ws.source == "github.com/loft-sh/devpod"

    def test_from_json_unknown_source(self):
        """Test parsing workspace with unknown source type."""
        data = {
            "id": "unknown",
            "source": {"someOther": "value"},
            "lastUsed": "",
            "provider": {},
            "ide": {},
        }
        ws = Workspace.from_json(data)
        assert ws.id == "unknown"
        assert ws.source_type == "unknown"

    def test_from_json_missing_fields(self):
        """Test parsing workspace with missing optional fields."""
        data = {"id": "minimal"}
        ws = Workspace.from_json(data)
        assert ws.id == "minimal"
        assert ws.source_type == "unknown"
        assert ws.last_used == ""
        assert ws.provider == ""
        assert ws.ide == ""


class TestListWorkspaces:
    """Tests for list_workspaces function."""

    @patch("rockerc.dl.run_devpod")
    def test_list_workspaces_success(self, mock_run):
        """Test successful workspace listing."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [
                {
                    "id": "ws1",
                    "source": {"localFolder": "/path/to/ws1"},
                    "lastUsed": "2024-01-01T12:00:00Z",
                    "provider": {"name": "docker"},
                    "ide": {"name": "vscode"},
                },
                {
                    "id": "ws2",
                    "source": {"gitRepository": "github.com/owner/repo"},
                    "lastUsed": "2024-01-02T12:00:00Z",
                    "provider": {"name": "docker"},
                    "ide": {"name": "none"},
                },
            ]
        )
        mock_run.return_value = mock_result

        workspaces = list_workspaces()

        assert len(workspaces) == 2
        assert workspaces[0].id == "ws1"
        assert workspaces[1].id == "ws2"

    @patch("rockerc.dl.run_devpod")
    def test_list_workspaces_empty(self, mock_run):
        """Test empty workspace list."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"
        mock_run.return_value = mock_result

        workspaces = list_workspaces()
        assert workspaces == []

    @patch("rockerc.dl.run_devpod")
    def test_list_workspaces_error(self, mock_run):
        """Test handling of devpod error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        workspaces = list_workspaces()
        assert workspaces == []

    @patch("rockerc.dl.run_devpod")
    def test_list_workspaces_invalid_json(self, mock_run):
        """Test handling of invalid JSON output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_run.return_value = mock_result

        workspaces = list_workspaces()
        assert workspaces == []


class TestGetWorkspaceIds:
    """Tests for get_workspace_ids function."""

    @patch("rockerc.dl.list_workspaces")
    def test_get_workspace_ids(self, mock_list):
        """Test getting workspace IDs."""
        mock_list.return_value = [
            Workspace("ws1", "local", "/path", "", "docker", "vscode"),
            Workspace("ws2", "git", "github.com/o/r", "", "docker", "none"),
        ]

        ids = get_workspace_ids()
        assert ids == ["ws1", "ws2"]

    @patch("rockerc.dl.list_workspaces")
    def test_get_workspace_ids_empty(self, mock_list):
        """Test getting workspace IDs when empty."""
        mock_list.return_value = []

        ids = get_workspace_ids()
        assert ids == []


class TestParseOwnerRepoFromUrl:
    """Tests for parse_owner_repo_from_url function."""

    def test_parse_ssh_url(self):
        """Test parsing git@github.com:owner/repo.git URL."""
        result = parse_owner_repo_from_url("git@github.com:blooop/python_template.git")
        assert result == ("blooop", "python_template")

    def test_parse_ssh_url_no_git_suffix(self):
        """Test parsing git@github.com:owner/repo URL without .git."""
        result = parse_owner_repo_from_url("git@github.com:blooop/rockerc")
        assert result == ("blooop", "rockerc")

    def test_parse_https_url(self):
        """Test parsing https://github.com/owner/repo.git URL."""
        result = parse_owner_repo_from_url("https://github.com/loft-sh/devpod.git")
        assert result == ("loft-sh", "devpod")

    def test_parse_https_url_no_git_suffix(self):
        """Test parsing https://github.com/owner/repo URL."""
        result = parse_owner_repo_from_url("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_parse_github_com_url(self):
        """Test parsing github.com/owner/repo URL."""
        result = parse_owner_repo_from_url("github.com/blooop/test")
        assert result == ("blooop", "test")

    def test_parse_invalid_url(self):
        """Test parsing non-GitHub URL returns None."""
        result = parse_owner_repo_from_url("https://gitlab.com/owner/repo")
        assert result is None

    def test_parse_random_string(self):
        """Test parsing random string returns None."""
        result = parse_owner_repo_from_url("not a url")
        assert result is None


class TestDiscoverReposFromWorkspaces:
    """Tests for discover_repos_from_workspaces function."""

    def test_discover_from_git_workspace(self):
        """Test discovering repo from git workspace."""
        workspaces = [
            Workspace("ws1", "git", "github.com/owner/repo", "", "docker", "vscode"),
        ]
        repos = discover_repos_from_workspaces(workspaces)
        assert repos == {"owner": ["repo"]}

    @patch("rockerc.dl.get_git_remote_url")
    def test_discover_from_local_workspace(self, mock_remote):
        """Test discovering repo from local workspace with git remote."""
        mock_remote.return_value = "git@github.com:blooop/python_template.git"
        workspaces = [
            Workspace("ws1", "local", "/home/user/project", "", "docker", "vscode"),
        ]
        repos = discover_repos_from_workspaces(workspaces)
        assert repos == {"blooop": ["python_template"]}

    @patch("rockerc.dl.get_git_remote_url")
    def test_discover_multiple_repos(self, mock_remote):
        """Test discovering multiple repos from different owners."""
        mock_remote.side_effect = [
            "git@github.com:owner1/repo1.git",
            "git@github.com:owner2/repo2.git",
            "git@github.com:owner1/repo3.git",
        ]
        workspaces = [
            Workspace("ws1", "local", "/path1", "", "docker", "vscode"),
            Workspace("ws2", "local", "/path2", "", "docker", "vscode"),
            Workspace("ws3", "local", "/path3", "", "docker", "vscode"),
        ]
        repos = discover_repos_from_workspaces(workspaces)
        assert repos == {"owner1": ["repo1", "repo3"], "owner2": ["repo2"]}

    @patch("rockerc.dl.get_git_remote_url")
    def test_discover_no_remote(self, mock_remote):
        """Test workspace without git remote is skipped."""
        mock_remote.return_value = None
        workspaces = [
            Workspace("ws1", "local", "/path", "", "docker", "vscode"),
        ]
        repos = discover_repos_from_workspaces(workspaces)
        assert repos == {}


class TestGetKnownRepos:
    """Tests for get_known_repos function."""

    @patch("rockerc.dl.list_workspaces")
    def test_get_known_repos(self, mock_list):
        """Test getting known repos as sorted list."""
        mock_list.return_value = [
            Workspace("ws1", "git", "github.com/zowner/zrepo", "", "docker", "vscode"),
            Workspace("ws2", "git", "github.com/aowner/arepo", "", "docker", "vscode"),
        ]
        repos = get_known_repos()
        assert repos == ["aowner/arepo", "zowner/zrepo"]

    @patch("rockerc.dl.list_workspaces")
    def test_get_known_repos_empty(self, mock_list):
        """Test getting known repos when no workspaces."""
        mock_list.return_value = []
        repos = get_known_repos()
        assert repos == []
