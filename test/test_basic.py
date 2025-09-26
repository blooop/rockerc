from unittest import TestCase
import pytest
import tempfile
import pathlib
import yaml
from unittest.mock import patch, mock_open, MagicMock
from rockerc.rockerc import (
    yaml_dict_to_args,
    collect_arguments,
    build_docker,
    save_rocker_cmd,
    run_rockerc,
)


class TestBasicClass(TestCase):

    # Converts dictionary with 'image' and 'args' keys to argument string
    def test_converts_dict_with_image_and_args_to_string(self):
        d = {
            "image": "ubuntu:latest",
            "args": ["x11", "nvidia"],
            "option1": "value1",
            "option2": "value2",
        }
        expected = "--x11 --nvidia --option1 value1 --option2 value2 ubuntu:latest"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_empty(self):
        d = {}
        expected = ""
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_realistic(self):

        d = {
            "args": ["nvidia", "x11", "user", "pull", "deps", "git"],
            "image": "ubuntu:22.04",
        }

        expected = "--nvidia --x11 --user --pull --deps --git ubuntu:22.04"

        result = yaml_dict_to_args(d)
        assert result == expected

    @pytest.mark.skip
    def test_realisic_yaml(self):
        result = collect_arguments(".")

        expected = {
            "args": ["nvidia", "x11", "user", "pull", "deps", "git", "lazygit", "pixi"],
            "image": "ubuntu:22.04",
        }

        assert result == expected

    def test_yaml_dict_to_args_no_image(self):
        """Test yaml_dict_to_args with no image"""
        d = {
            "args": ["x11", "nvidia"],
            "option1": "value1",
        }
        expected = "--x11 --nvidia --option1 value1"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_yaml_dict_to_args_no_args(self):
        """Test yaml_dict_to_args with no args"""
        d = {
            "image": "ubuntu:latest",
            "option1": "value1",
        }
        expected = "--option1 value1 ubuntu:latest"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_yaml_dict_to_args_with_whitespace_args(self):
        """Test yaml_dict_to_args filters out whitespace-only args"""
        d = {
            "args": ["x11", "", "  ", "nvidia", " "],
            "image": "ubuntu:latest",
        }
        expected = "--x11 --nvidia ubuntu:latest"
        result = yaml_dict_to_args(d)
        assert result == expected


class TestCollectArguments(TestCase):
    """Test collect_arguments function"""

    def test_collect_arguments_empty_directory(self):
        """Test collect_arguments with no rockerc.yaml files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir) / "nonexistent"
                result = collect_arguments(tmpdir)
                assert result == {}

    def test_collect_arguments_local_file(self):
        """Test collect_arguments with local rockerc.yaml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_data = {"args": ["x11", "nvidia"], "image": "ubuntu:latest"}
            config_path = pathlib.Path(tmpdir) / "rockerc.yaml"

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            with patch("builtins.print"):  # Suppress print output
                result = collect_arguments(tmpdir)

            assert result == config_data

    def test_collect_arguments_home_fallback(self):
        """Test collect_arguments falls back to ~/.rockerc.yaml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.TemporaryDirectory() as homedir:
                config_data = {"args": ["git"], "image": "alpine:latest"}
                config_path = pathlib.Path(homedir) / ".rockerc.yaml"

                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(config_data, f)

                with patch("pathlib.Path.home") as mock_home:
                    mock_home.return_value = pathlib.Path(homedir)
                    with patch("builtins.print"):  # Suppress print output
                        result = collect_arguments(tmpdir)

                assert result == config_data

    def test_collect_arguments_invalid_yaml(self):
        """Test collect_arguments with invalid YAML"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / "rockerc.yaml"

            with open(config_path, "w", encoding="utf-8") as f:
                f.write("invalid: yaml: content: [")

            with patch("builtins.print"):
                with pytest.raises(SystemExit):
                    collect_arguments(tmpdir)

    def test_collect_arguments_non_dict_yaml(self):
        """Test collect_arguments with non-dict YAML content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / "rockerc.yaml"

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(["list", "instead", "of", "dict"], f)

            with patch("builtins.print"):
                with pytest.raises(SystemExit):
                    collect_arguments(tmpdir)

    def test_collect_arguments_empty_yaml(self):
        """Test collect_arguments with empty YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / "rockerc.yaml"

            with open(config_path, "w", encoding="utf-8") as f:
                f.write("")

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir) / "nonexistent"
                with patch("builtins.print"):
                    result = collect_arguments(tmpdir)

            assert result == {}


class TestBuildDocker(TestCase):
    """Test build_docker function"""

    @patch("subprocess.call")
    @patch("pathlib.Path.absolute")
    def test_build_docker_default_path(self, mock_absolute, mock_subprocess):
        """Test build_docker with default path"""
        mock_absolute.return_value.name = "test-project"
        mock_subprocess.return_value = 0

        result = build_docker()

        expected_tag = "test-project:latest"
        assert result == expected_tag
        mock_subprocess.assert_called_once()

    @patch("subprocess.call")
    @patch("pathlib.Path.absolute")
    def test_build_docker_custom_path(self, mock_absolute, mock_subprocess):
        """Test build_docker with custom dockerfile path"""
        mock_absolute.return_value.name = "my-app"
        mock_subprocess.return_value = 0

        result = build_docker("/custom/path")

        expected_tag = "my-app:latest"
        assert result == expected_tag
        mock_subprocess.assert_called_once()

    def test_collect_arguments_home_yaml_error(self):
        """Test collect_arguments with invalid YAML in home fallback"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.TemporaryDirectory() as homedir:
                config_path = pathlib.Path(homedir) / ".rockerc.yaml"

                with open(config_path, "w", encoding="utf-8") as f:
                    f.write("invalid: yaml: content: [")

                with patch("pathlib.Path.home") as mock_home:
                    mock_home.return_value = pathlib.Path(homedir)
                    with patch("builtins.print"):
                        with pytest.raises(SystemExit):
                            collect_arguments(tmpdir)

    def test_collect_arguments_home_non_dict_yaml(self):
        """Test collect_arguments with non-dict YAML in home fallback"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.TemporaryDirectory() as homedir:
                config_path = pathlib.Path(homedir) / ".rockerc.yaml"

                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump("not a dict", f)

                with patch("pathlib.Path.home") as mock_home:
                    mock_home.return_value = pathlib.Path(homedir)
                    with patch("builtins.print"):
                        with pytest.raises(SystemExit):
                            collect_arguments(tmpdir)


class TestSaveRockerCmd(TestCase):
    """Test save_rocker_cmd function"""

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.chmod")
    def test_save_rocker_cmd_success(self, mock_chmod, mock_file, mock_subprocess):
        """Test save_rocker_cmd with successful execution"""
        # Mock subprocess output
        mock_result = MagicMock()
        mock_result.stdout = """some output
vvvvvv
FROM ubuntu:latest
RUN apt-get update
^^^^^^
Run this command: docker run --rm -it --name test ubuntu:latest
"""
        mock_subprocess.return_value = mock_result

        cmd = ["rocker", "--x11", "ubuntu:latest"]

        with patch("logging.info"):
            save_rocker_cmd(cmd)

        # Verify subprocess was called with dry-run
        expected_cmd = ["rocker", "--x11", "ubuntu:latest", "--mode", "dry-run"]
        mock_subprocess.assert_called_once_with(
            expected_cmd, capture_output=True, text=True, check=True
        )

        # Verify files were written
        assert mock_file.call_count == 2  # Dockerfile.rocker and run_dockerfile.sh
        mock_chmod.assert_called_once_with("run_dockerfile.sh", 0o755)

    @patch("subprocess.run")
    @patch("logging.error")
    def test_save_rocker_cmd_subprocess_error(self, mock_log_error, mock_subprocess):
        """Test save_rocker_cmd with subprocess error"""
        from subprocess import CalledProcessError

        mock_subprocess.side_effect = CalledProcessError(1, "rocker", "stdout", "stderr")

        cmd = ["rocker", "--x11", "ubuntu:latest"]

        with pytest.raises(SystemExit):
            save_rocker_cmd(cmd)

        mock_log_error.assert_called()

    @patch("subprocess.run")
    @patch("logging.error")
    def test_save_rocker_cmd_value_error(self, mock_log_error, mock_subprocess):
        """Test save_rocker_cmd with malformed output"""
        mock_result = MagicMock()
        mock_result.stdout = "malformed output without proper sections"
        mock_subprocess.return_value = mock_result

        cmd = ["rocker", "--x11", "ubuntu:latest"]

        with pytest.raises(SystemExit):
            save_rocker_cmd(cmd)

        mock_log_error.assert_called()


class TestRunRockerc(TestCase):
    """Test run_rockerc function"""

    @patch("rockerc.rockerc.collect_arguments")
    @patch("subprocess.run")
    @patch("logging.basicConfig")
    @patch("logging.info")
    def test_run_rockerc_basic(
        self, _mock_log_info, _mock_log_config, mock_subprocess, mock_collect
    ):
        """Test run_rockerc with basic configuration"""
        mock_collect.return_value = {"args": ["x11"], "image": "ubuntu:latest"}

        with patch("sys.argv", ["rockerc"]):
            run_rockerc()

        expected_cmd = ["rocker", "--x11", "ubuntu:latest"]
        mock_subprocess.assert_called_once_with(expected_cmd, check=True)

    @patch("rockerc.rockerc.collect_arguments")
    @patch("subprocess.call")
    @patch("logging.basicConfig")
    @patch("logging.error")
    def test_run_rockerc_no_args(
        self, mock_log_error, _mock_log_config, mock_subprocess_call, mock_collect
    ):
        """Test run_rockerc with no arguments"""
        mock_collect.return_value = {}

        with patch("sys.argv", ["rockerc"]):
            run_rockerc()

        mock_log_error.assert_called()
        mock_subprocess_call.assert_called_once_with("rocker -h", shell=True)

    @patch("rockerc.rockerc.collect_arguments")
    @patch("rockerc.rockerc.build_docker")
    @patch("subprocess.run")
    @patch("logging.basicConfig")
    @patch("logging.info")
    def test_run_rockerc_with_dockerfile(
        self, _mock_log_info, _mock_log_config, mock_subprocess, mock_build, mock_collect
    ):
        """Test run_rockerc with dockerfile build"""
        mock_collect.return_value = {"args": ["x11", "pull"], "dockerfile": "/path/to/dockerfile"}
        mock_build.return_value = "my-image:latest"

        with patch("sys.argv", ["rockerc"]):
            run_rockerc()

        mock_build.assert_called_once_with("/path/to/dockerfile")
        expected_cmd = ["rocker", "--x11", "my-image:latest"]
        mock_subprocess.assert_called_once_with(expected_cmd, check=True)

    @patch("rockerc.rockerc.collect_arguments")
    @patch("rockerc.rockerc.save_rocker_cmd")
    @patch("subprocess.run")
    @patch("logging.basicConfig")
    def test_run_rockerc_create_dockerfile(
        self, _mock_log_config, mock_subprocess, mock_save, mock_collect
    ):
        """Test run_rockerc with --create-dockerfile flag"""
        mock_collect.return_value = {"args": ["x11"], "image": "ubuntu:latest"}

        with patch("sys.argv", ["rockerc", "--create-dockerfile"]):
            run_rockerc()

        mock_save.assert_called_once()
        expected_cmd = ["rocker", "--x11", "ubuntu:latest"]
        mock_subprocess.assert_called_once_with(expected_cmd, check=True)

    @patch("rockerc.rockerc.collect_arguments")
    @patch("subprocess.run")
    @patch("logging.basicConfig")
    @patch("logging.info")
    def test_run_rockerc_cli_args_with_dashes(
        self, _mock_log_info, _mock_log_config, mock_subprocess, mock_collect
    ):
        """Test run_rockerc with CLI args that have dashes like --gemini"""
        mock_collect.return_value = {"image": "ubuntu:latest"}

        with patch("sys.argv", ["rockerc", "--gemini"]):
            run_rockerc()

        # CLI args should be passed through directly, image comes from config
        expected_cmd = ["rocker", "ubuntu:latest", "--gemini"]
        mock_subprocess.assert_called_once_with(expected_cmd, check=True)

    @patch("rockerc.rockerc.collect_arguments")
    @patch("rockerc.rockerc.save_rocker_cmd")
    @patch("subprocess.run")
    @patch("logging.basicConfig")
    @patch("logging.info")
    def test_run_rockerc_create_dockerfile_in_config(
        self, _mock_log_info, _mock_log_config, mock_subprocess, mock_save, mock_collect
    ):
        """Test run_rockerc with --create-dockerfile in config args"""
        mock_collect.return_value = {
            "args": ["x11", "--create-dockerfile"],
            "image": "ubuntu:latest",
        }

        with patch("sys.argv", ["rockerc"]):
            run_rockerc()

        mock_save.assert_called_once()
        expected_cmd = ["rocker", "--x11", "ubuntu:latest"]
        mock_subprocess.assert_called_once_with(expected_cmd, check=True)
