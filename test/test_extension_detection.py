"""Tests for extension change detection functionality."""

import subprocess
from unittest.mock import Mock, patch


from rockerc.core import (
    add_extension_env,
    extensions_changed,
    get_container_extensions,
)


class TestAddExtensionEnv:
    """Tests for add_extension_env function."""

    def test_add_env_with_extensions(self):
        """Test adding extension env var with extensions."""
        base = "--detach --name test"
        extensions = ["nvidia", "x11", "user"]
        result = add_extension_env(base, extensions)
        # Extensions should be sorted
        assert "--env ROCKERC_EXTENSIONS=nvidia,user,x11" in result
        assert "--detach" in result
        assert "--name test" in result

    def test_add_env_empty_extensions(self):
        """Test adding env var with empty extension list."""
        base = "--detach --name test"
        extensions = []
        result = add_extension_env(base, extensions)
        assert result == base
        assert "ROCKERC_EXTENSIONS" not in result

    def test_add_env_normalizes_order(self):
        """Test that extension order is normalized by sorting."""
        base = "--detach"
        extensions1 = ["z", "a", "m"]
        extensions2 = ["a", "m", "z"]
        result1 = add_extension_env(base, extensions1)
        result2 = add_extension_env(base, extensions2)
        # Both should produce same sorted order
        assert "ROCKERC_EXTENSIONS=a,m,z" in result1
        assert "ROCKERC_EXTENSIONS=a,m,z" in result2


class TestGetContainerExtensions:
    """Tests for get_container_extensions function."""

    def test_get_extensions_success(self):
        """Test successfully retrieving extensions from container."""
        mock_result = Mock()
        mock_result.stdout = "PATH=/usr/bin\nROCKERC_EXTENSIONS=nvidia,user,x11\nHOME=/root\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = get_container_extensions("test_container")

        assert result == ["nvidia", "user", "x11"]
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "inspect" in call_args
        assert "test_container" in call_args

    def test_get_extensions_no_env_var(self):
        """Test retrieving extensions when env var is missing."""
        mock_result = Mock()
        mock_result.stdout = "PATH=/usr/bin\nHOME=/root\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = get_container_extensions("test_container")

        assert result is None

    def test_get_extensions_container_not_found(self):
        """Test retrieving extensions when container doesn't exist."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "docker")):
            result = get_container_extensions("nonexistent")

        assert result is None

    def test_get_extensions_empty_output(self):
        """Test retrieving extensions with empty output."""
        mock_result = Mock()
        mock_result.stdout = "\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = get_container_extensions("test_container")

        assert result is None


class TestExtensionsChanged:
    """Tests for extensions_changed function."""

    def test_extensions_unchanged(self):
        """Test when extensions haven't changed."""
        current = ["nvidia", "x11", "user"]
        stored = ["nvidia", "x11", "user"]
        assert not extensions_changed(current, stored)

    def test_extensions_changed_different_items(self):
        """Test when extensions have different items."""
        current = ["nvidia", "x11", "user"]
        stored = ["nvidia", "x11"]
        assert extensions_changed(current, stored)

    def test_extensions_changed_different_order(self):
        """Test when extensions have same items but different order."""
        current = ["user", "nvidia", "x11"]
        stored = ["nvidia", "x11", "user"]
        # Should NOT be considered changed (order normalized)
        assert not extensions_changed(current, stored)

    def test_extensions_changed_stored_none(self):
        """Test when stored extensions is None."""
        current = ["nvidia", "x11", "user"]
        stored = None
        # Should be considered changed (old container or missing label)
        assert extensions_changed(current, stored)

    def test_extensions_changed_both_empty(self):
        """Test when both lists are empty."""
        current = []
        stored = []
        assert not extensions_changed(current, stored)

    def test_extensions_changed_current_empty(self):
        """Test when current is empty but stored has items."""
        current = []
        stored = ["nvidia"]
        assert extensions_changed(current, stored)

    def test_extensions_changed_stored_empty(self):
        """Test when stored is empty but current has items."""
        current = ["nvidia"]
        stored = []
        assert extensions_changed(current, stored)


class TestIntegration:
    """Integration tests for extension detection."""

    def test_full_workflow(self):
        """Test the full workflow of storing and retrieving extensions."""
        extensions = ["nvidia", "x11", "user", "git"]
        base_args = "--detach --name test"

        # Add env var
        env_args = add_extension_env(base_args, extensions)
        assert "ROCKERC_EXTENSIONS=" in env_args

        # Simulate storing in container
        expected_value = "git,nvidia,user,x11"  # sorted
        assert f"ROCKERC_EXTENSIONS={expected_value}" in env_args

        # Simulate retrieving
        mock_result = Mock()
        mock_result.stdout = f"PATH=/usr/bin\nROCKERC_EXTENSIONS={expected_value}\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            retrieved = get_container_extensions("test")

        # Should match (both sorted)
        assert not extensions_changed(extensions, retrieved)

    def test_detect_added_extension(self):
        """Test detecting when an extension is added."""
        updated = ["nvidia", "x11", "user"]

        # Original stored in container
        mock_result = Mock()
        mock_result.stdout = "ROCKERC_EXTENSIONS=nvidia,x11\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            stored = get_container_extensions("test")

        # Check if changed
        assert extensions_changed(updated, stored)

    def test_detect_removed_extension(self):
        """Test detecting when an extension is removed."""
        updated = ["nvidia", "x11"]

        # Original stored in container
        mock_result = Mock()
        mock_result.stdout = "ROCKERC_EXTENSIONS=nvidia,user,x11\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            stored = get_container_extensions("test")

        # Check if changed
        assert extensions_changed(updated, stored)
