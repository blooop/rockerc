from unittest import TestCase
import pytest
from unittest.mock import patch
from rockerc.rockerc import (
    inspect_container,
    generate_container_name,
    merge_container_options_with_config,
)


class TestFromContainerFunctionality(TestCase):
    def test_inspect_container_basic(self):
        """Test basic container inspection with mocked Docker output"""
        mock_docker_output = """[
            {
                "Config": {
                    "Image": "ubuntu:22.04",
                    "Env": ["TERM=xterm", "CUSTOM_VAR=test_value"],
                    "WorkingDir": "/app",
                    "User": "1000:1000"
                },
                "HostConfig": {
                    "Binds": ["/host/path:/container/path:rw"],
                    "PortBindings": {
                        "8080/tcp": [{"HostPort": "3000"}]
                    },
                    "Devices": [
                        {"PathOnHost": "/dev/gpu0", "PathInContainer": "/dev/gpu0"}
                    ],
                    "CapAdd": ["SYS_ADMIN"],
                    "Privileged": false,
                    "NetworkMode": "host"
                }
            }
        ]"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = mock_docker_output
            result = inspect_container("test_container")

            expected = {
                "image": "ubuntu:22.04",
                "env": ["TERM=xterm", "CUSTOM_VAR=test_value"],
                "user": "1000:1000",
                "volume": ["/host/path:/container/path:rw"],
                "port": ["3000:8080/tcp"],
                "device": ["/dev/gpu0:/dev/gpu0"],
                "cap-add": ["SYS_ADMIN"],
                "network": "host",
            }

            assert result == expected

    def test_inspect_container_minimal(self):
        """Test container inspection with minimal Docker output"""
        mock_docker_output = """[
            {
                "Config": {
                    "Image": "nginx:latest"
                },
                "HostConfig": {}
            }
        ]"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = mock_docker_output
            result = inspect_container("minimal_container")

            expected = {"image": "nginx:latest"}

            assert result == expected

    def test_inspect_container_filters_system_env(self):
        """Test that system environment variables are filtered out"""
        mock_docker_output = """[
            {
                "Config": {
                    "Image": "ubuntu:22.04",
                    "Env": [
                        "PATH=/usr/local/sbin:/usr/local/bin",
                        "HOSTNAME=container123",
                        "HOME=/root",
                        "PWD=/app",
                        "CUSTOM_VAR=keep_this"
                    ]
                },
                "HostConfig": {}
            }
        ]"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = mock_docker_output
            result = inspect_container("test_container")

            # Only custom environment variables should be kept
            expected = {"image": "ubuntu:22.04", "env": ["CUSTOM_VAR=keep_this"]}

            assert result == expected

    def test_inspect_container_privileged(self):
        """Test privileged container inspection"""
        mock_docker_output = """[
            {
                "Config": {
                    "Image": "ubuntu:22.04"
                },
                "HostConfig": {
                    "Privileged": true
                }
            }
        ]"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = mock_docker_output
            result = inspect_container("privileged_container")

            expected = {"image": "ubuntu:22.04", "privileged": True}

            assert result == expected

    def test_inspect_container_docker_error(self):
        """Test handling of Docker command errors"""
        from subprocess import CalledProcessError

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = CalledProcessError(
                1, ["docker", "inspect"], stderr="Container not found"
            )

            with pytest.raises(CalledProcessError) as exc_info:
                inspect_container("nonexistent_container")

            # Check that our custom error message is in the exception args
            assert "nonexistent_container" in str(exc_info.value.args[2])

    def test_inspect_container_invalid_json(self):
        """Test handling of invalid JSON output"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "invalid json"

            with pytest.raises(ValueError) as exc_info:
                inspect_container("test_container")

            assert "Failed to parse container data" in str(exc_info.value)

    def test_generate_container_name_no_collision(self):
        """Test container name generation when no collision exists"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""  # No existing containers

            result = generate_container_name("myapp")
            assert result == "myapp-rockerc"

    def test_generate_container_name_with_collision(self):
        """Test container name generation when collision exists"""
        with patch("subprocess.run") as mock_run:
            # First call returns existing container (collision)
            mock_run.return_value.stdout = "myapp-rockerc\n"

            with patch("random.choices") as mock_random:
                mock_random.return_value = ["a", "b", "c", "d"]
                result = generate_container_name("myapp")
                assert result == "myapp-rockerc-abcd"

    def test_generate_container_name_custom_suffix(self):
        """Test container name generation with custom suffix"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""

            result = generate_container_name("myapp", "test")
            assert result == "myapp-test"

    def test_generate_container_name_docker_error(self):
        """Test container name generation when Docker command fails"""
        from subprocess import CalledProcessError

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = CalledProcessError(1, ["docker", "ps"])

            # Should still return the base name
            result = generate_container_name("myapp")
            assert result == "myapp-rockerc"

    def test_merge_container_options_with_config_basic(self):
        """Test basic merging of container options with config"""
        container_options = {
            "image": "ubuntu:22.04",
            "volume": ["/host1:/container1:rw"],
            "env": ["VAR1=value1"],
        }

        config_dict = {
            "args": ["nvidia", "x11"],
            "volume": ["/host2:/container2:rw"],
            "port": ["8080:80"],
        }

        result = merge_container_options_with_config(container_options, config_dict)

        expected = {
            "image": "ubuntu:22.04",
            "volume": ["/host1:/container1:rw", "/host2:/container2:rw"],
            "env": ["VAR1=value1"],
            "args": ["nvidia", "x11"],
            "port": ["8080:80"],
        }

        assert result == expected

    def test_merge_container_options_config_overrides(self):
        """Test that config values override container options for non-list values"""
        container_options = {"image": "ubuntu:20.04", "user": "1000:1000", "workdir": "/app"}

        config_dict = {
            "args": ["nvidia"],
            "image": "ubuntu:22.04",  # Should override
            "user": "root",  # Should override
        }

        result = merge_container_options_with_config(container_options, config_dict)

        expected = {"image": "ubuntu:22.04", "user": "root", "workdir": "/app", "args": ["nvidia"]}

        assert result == expected

    def test_merge_container_options_user_extension_conflict(self):
        """Test that --user extension removes container user setting"""
        container_options = {"image": "ubuntu:22.04", "user": "root", "env": ["VAR1=value1"]}

        config_dict = {
            "args": ["user", "x11"],  # user extension conflicts with container user
            "volume": ["/host:/container:rw"],
        }

        result = merge_container_options_with_config(container_options, config_dict)

        # Container user should be removed because --user extension takes precedence
        expected = {
            "image": "ubuntu:22.04",
            "env": ["VAR1=value1"],
            "args": ["user", "x11"],
            "volume": ["/host:/container:rw"],
        }

        assert result == expected

    def test_merge_container_options_deduplicates_lists(self):
        """Test that list values are deduplicated when merged"""
        container_options = {
            "image": "ubuntu:22.04",
            "env": ["VAR1=value1", "VAR2=value2"],
            "volume": ["/host1:/container1:rw"],
        }

        config_dict = {
            "args": ["nvidia"],
            "env": ["VAR2=value2", "VAR3=value3"],  # VAR2 is duplicate
            "volume": ["/host1:/container1:rw", "/host2:/container2:rw"],  # first is duplicate
        }

        result = merge_container_options_with_config(container_options, config_dict)

        expected = {
            "image": "ubuntu:22.04",
            "env": ["VAR1=value1", "VAR2=value2", "VAR3=value3"],
            "volume": ["/host1:/container1:rw", "/host2:/container2:rw"],
            "args": ["nvidia"],
        }

        assert result == expected

    def test_merge_container_options_empty_config(self):
        """Test merging when config is empty"""
        container_options = {"image": "ubuntu:22.04", "volume": ["/host:/container:rw"]}

        config_dict = {}

        result = merge_container_options_with_config(container_options, config_dict)

        # Should return container options unchanged
        assert result == container_options

    def test_merge_container_options_empty_container(self):
        """Test merging when container options are empty"""
        container_options = {}

        config_dict = {"args": ["nvidia", "x11"], "image": "ubuntu:22.04"}

        result = merge_container_options_with_config(container_options, config_dict)

        # Should return config dict
        assert result == config_dict

    def test_merge_container_options_handles_non_list_existing(self):
        """Test merging when existing value is not a list but config is"""
        container_options = {
            "image": "ubuntu:22.04",
            "env": "SINGLE_VAR=value",  # Not a list
        }

        config_dict = {
            "args": ["nvidia"],
            "env": ["VAR1=value1", "VAR2=value2"],  # List
        }

        result = merge_container_options_with_config(container_options, config_dict)

        expected = {
            "image": "ubuntu:22.04",
            "env": ["VAR1=value1", "VAR2=value2"],  # Config takes precedence
            "args": ["nvidia"],
        }

        assert result == expected
