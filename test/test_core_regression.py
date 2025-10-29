"""Regression and edge case tests for core infrastructure."""

import pytest
from unittest.mock import Mock, patch

from rockerc.rockerc import yaml_dict_to_args
from rockerc.core import add_extension_env, ensure_volume_binding, get_container_extensions


class TestCoreInfrastructureRegression:
    """Regression tests for critical infrastructure components."""

    def test_yaml_dict_to_args_detached_keep_alive_injection(self):
        """Verify that detached containers automatically receive a keep-alive command."""
        config = {"name": "test-container", "image": "ubuntu:latest", "detach": True}

        rocker_cmd = yaml_dict_to_args(config)

        # Ensure keep-alive command is present
        assert "tail -f /dev/null" in rocker_cmd, (
            "Detached containers must include a keep-alive command to prevent immediate exit"
        )
        # Ensure only one keep-alive command is added
        assert rocker_cmd.count("tail -f /dev/null") == 1

    def test_yaml_dict_to_args_non_detached_no_keep_alive(self):
        """Verify that non-detached containers do not receive a keep-alive command."""
        config = {"name": "test-container", "image": "ubuntu:latest", "detach": False}

        rocker_cmd = yaml_dict_to_args(config)

        # Non-detached containers should not have keep-alive
        assert "tail -f /dev/null" not in rocker_cmd

    def test_add_extension_env_validation_valid_extensions(self):
        """Test that valid extension names are accepted."""
        extensions = ["valid-ext", "another-valid"]
        base_args = "--name test-container"

        with patch("rockerc.core.LOGGER.warning") as mock_warning:
            result = add_extension_env(base_args, extensions)

            mock_warning.assert_not_called()
            assert "ROCKERC_EXTENSIONS" in result

    def test_add_extension_env_validation_invalid_space(self):
        """Test that extensions with spaces are rejected."""
        extensions = ["ext with space"]
        base_args = "--name test-container"

        with patch("rockerc.core.LOGGER.warning") as mock_warning:
            result = add_extension_env(base_args, extensions)

            mock_warning.assert_called_once_with(
                "Extension name %r contains invalid characters. Skipping environment storage.",
                extensions[0],
            )
            assert "ROCKERC_EXTENSIONS" not in result

    def test_add_extension_env_validation_invalid_exclamation(self):
        """Test that extensions with exclamation marks are rejected."""
        extensions = ["!invalid-symbol"]
        base_args = "--name test-container"

        with patch("rockerc.core.LOGGER.warning") as mock_warning:
            result = add_extension_env(base_args, extensions)

            mock_warning.assert_called_once_with(
                "Extension name %r contains invalid characters. Skipping environment storage.",
                extensions[0],
            )
            assert "ROCKERC_EXTENSIONS" not in result

    def test_add_extension_env_validation_comma_allowed(self):
        """Test that extensions with commas are now allowed (for extension args)."""
        extensions = ["ext,with,comma"]
        base_args = "--name test-container"

        with patch("rockerc.core.LOGGER.warning") as mock_warning:
            result = add_extension_env(base_args, extensions)

            mock_warning.assert_not_called()
            assert "ROCKERC_EXTENSIONS" in result

    def test_ensure_volume_binding_basic_functionality(self):
        """Test basic volume binding functionality."""
        import pathlib

        base_path = pathlib.Path("/simple/path")
        base_args = ""

        # First volume mount should be added
        result = ensure_volume_binding(base_args, "test-container", base_path, "/container/path")
        assert "--volume" in result

        # Second call with same path should detect duplicate
        result2 = ensure_volume_binding(result, "test-container", base_path, "/container/path")
        assert result2.count("--volume") == 1

    def test_ensure_volume_binding_with_spaces_no_crash(self):
        """Test that function handles paths with spaces without crashing."""
        import pathlib

        # Test that function handles paths with spaces by at least not crashing
        space_path = pathlib.Path("/path with space")
        try:
            result = ensure_volume_binding("", "test-container", space_path, "/container/path")
            assert "--volume" in result
            # Just ensure it produces valid output without crashing
        except Exception as e:
            pytest.fail(f"Function should handle paths with spaces without crashing: {e}")

    @pytest.mark.parametrize(
        "env_value,expected_parsed",
        [
            ("git,nvidia,user,x11", ["git", "nvidia", "user", "x11"]),
            ("git, nvidia, user, x11", ["git", "nvidia", "user", "x11"]),  # extra spaces
            ("git,,nvidia,user,,x11", ["git", "nvidia", "user", "x11"]),  # empty entries
            ("", []),  # empty string
            (" , , ", []),  # only spaces and commas
        ],
    )
    def test_get_container_extensions_parsing_robustness(self, env_value, expected_parsed):
        """Test robustness of get_container_extensions parsing.

        Verifies the function handles various malformed environment variable formats.
        """
        # Create a mock subprocess result
        mock_result = Mock()
        mock_result.stdout = f"PATH=/usr/bin\nROCKERC_EXTENSIONS={env_value}\nHOME=/root\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            parsed = get_container_extensions("test_container")
            assert sorted(parsed or []) == sorted(expected_parsed), (
                f"Failed for env_value: '{env_value}'"
            )
