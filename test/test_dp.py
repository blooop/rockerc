"""Tests for dp (DevPod CLI Wrapper) functionality."""

import json
from unittest.mock import patch, MagicMock

from rockerc.dp import (
    expand_workspace_spec,
    Workspace,
    list_workspaces,
    get_workspace_ids,
    OWNER_REPO_PATTERN,
)


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

    @patch("rockerc.dp.run_devpod")
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

    @patch("rockerc.dp.run_devpod")
    def test_list_workspaces_empty(self, mock_run):
        """Test empty workspace list."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"
        mock_run.return_value = mock_result

        workspaces = list_workspaces()
        assert workspaces == []

    @patch("rockerc.dp.run_devpod")
    def test_list_workspaces_error(self, mock_run):
        """Test handling of devpod error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        workspaces = list_workspaces()
        assert workspaces == []

    @patch("rockerc.dp.run_devpod")
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

    @patch("rockerc.dp.list_workspaces")
    def test_get_workspace_ids(self, mock_list):
        """Test getting workspace IDs."""
        mock_list.return_value = [
            Workspace("ws1", "local", "/path", "", "docker", "vscode"),
            Workspace("ws2", "git", "github.com/o/r", "", "docker", "none"),
        ]

        ids = get_workspace_ids()
        assert ids == ["ws1", "ws2"]

    @patch("rockerc.dp.list_workspaces")
    def test_get_workspace_ids_empty(self, mock_list):
        """Test getting workspace IDs when empty."""
        mock_list.return_value = []

        ids = get_workspace_ids()
        assert ids == []
