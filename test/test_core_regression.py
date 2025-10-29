"""Regression and edge case tests for core infrastructure."""

import pytest
from unittest.mock import Mock, patch

from rockerc.rockerc import yaml_dict_to_args
from rockerc.core import add_extension_env, ensure_volume_binding, get_container_extensions


class TestCoreInfrastructureRegression:
    """Regression tests for critical infrastructure components."""

    @pytest.mark.parametrize("is_detached", [True, False])
    def test_yaml_dict_to_args_keep_alive_injection(self, is_detached):
        """Verify that detached containers automatically receive a keep-alive command.

        Regression test to ensure yaml_dict_to_args continues to inject keep-alive logic
        for detached containers, preventing silent breakage of container lifecycle.
        """
        config = {"name": "test-container", "image": "ubuntu:latest", "detach": is_detached}

        rocker_cmd = yaml_dict_to_args(config)

        if is_detached:
            # Ensure keep-alive command is present
            assert "tail -f /dev/null" in rocker_cmd, (
                "Detached containers must include a keep-alive command to prevent immediate exit"
            )
            # Ensure only one keep-alive command is added
            assert rocker_cmd.count("tail -f /dev/null") == 1
        else:
            # Non-detached containers should not have keep-alive
            assert "tail -f /dev/null" not in rocker_cmd

    @pytest.mark.parametrize(
        "extensions,expected_warning",
        [
            (["valid-ext", "another-valid"], False),
            (["ext with space"], True),
            (["!invalid-symbol"], True),
            (["ext,with,comma"], True),
        ],
    )
    def test_add_extension_env_validation(self, extensions, expected_warning):
        """Test extension name validation in add_extension_env.

        Verifies that extensions with invalid characters are skipped and warnings logged.
        """
        base_args = "--name test-container"

        with patch("rockerc.core.LOGGER.warning") as mock_warning:
            result = add_extension_env(base_args, extensions)

            if expected_warning:
                mock_warning.assert_called_once_with(
                    "Extension name '%s' contains invalid characters. Skipping environment storage.",
                    pytest.approx(extensions[0], rel=1.0),
                )
                # Warning should prevent env var from being added
                assert "ROCKERC_EXTENSIONS" not in result
            else:
                # Valid extensions should be added
                assert "ROCKERC_EXTENSIONS" in result

    @pytest.mark.parametrize(
        "volume_variations",
        [
            # Path variations to test duplicate detection
            (
                "/path/to/mount:/container/mount:Z",
                ["/path/to/mount:/container/mount", "/path/to/mount:/container/mount:Z"],
            ),
            # Different flag formats
            (
                "/host/path:/container/path",
                ["-v /host/path:/container/path", "--volume /host/path:/container/path"],
            ),
            # Whitespace and quote variations
            (
                "/path with space:/container/path",
                [
                    '--volume "/path with space":/container/path',
                    "-v '/path with space':/container/path",
                ],
            ),
        ],
    )
    def test_ensure_volume_binding_duplicate_detection(self, volume_variations):
        """Comprehensive test for volume binding duplicate detection.

        Validates that ensure_volume_binding correctly identifies and prevents
        duplicate volume mounts across various flag formats and path variations.
        """
        base_path, duplicate_paths = volume_variations
        base_args = ""

        # First volume mount should be added
        result = ensure_volume_binding(base_args, "test-container", base_path)
        assert "--volume" in result or "-v" in result

        # Subsequent mounts with same path should be skipped
        for dup_path in duplicate_paths:
            result = ensure_volume_binding(result, "test-container", dup_path)
            # Ensure no additional volume mounts are added
            assert result.count("--volume") <= 1
            assert result.count("-v") <= 1

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
