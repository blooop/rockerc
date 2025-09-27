from unittest import TestCase
import pytest
import tempfile
import pathlib
import yaml
from unittest.mock import patch
from rockerc.rockerc import (
    yaml_dict_to_args,
    collect_arguments,
    deduplicate_extensions,
    load_global_config,
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
        expected = "--x11 --nvidia --option1 value1 --option2 value2 -- ubuntu:latest"
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

        expected = "--nvidia --x11 --user --pull --deps --git -- ubuntu:22.04"

        result = yaml_dict_to_args(d)
        assert result == expected

    def test_no_optional_arg_extensions(self):
        d = {
            "args": ["nvidia", "x11", "user", "pull", "git"],
            "image": "ubuntu:22.04",
        }

        expected = "--nvidia --x11 --user --pull --git -- ubuntu:22.04"

        result = yaml_dict_to_args(d)
        assert result == expected

    def test_only_optional_arg_extensions(self):
        d = {
            "args": ["deps"],
            "image": "ubuntu:22.04",
        }

        expected = "--deps -- ubuntu:22.04"

        result = yaml_dict_to_args(d)
        assert result == expected

    def test_with_extra_args(self):
        d = {
            "args": ["nvidia", "x11"],
            "image": "ubuntu:22.04",
        }
        extra_args = "--image-name test --name container"

        expected = "--nvidia --x11 --image-name test --name container -- ubuntu:22.04"

        result = yaml_dict_to_args(d, extra_args)
        assert result == expected

    def test_with_special_char_extra_args(self):
        d = {
            "args": ["nvidia"],
            "image": "ubuntu:22.04",
        }
        extra_args = "--env VAR='value with spaces' --mount type=bind,source=/tmp,target=/tmp"

        expected = "--nvidia --env VAR='value with spaces' --mount type=bind,source=/tmp,target=/tmp -- ubuntu:22.04"

        result = yaml_dict_to_args(d, extra_args)
        assert result == expected

    def test_with_empty_extra_args(self):
        d = {
            "args": ["x11"],
            "image": "ubuntu:22.04",
        }
        extra_args = ""

        expected = "--x11 -- ubuntu:22.04"

        result = yaml_dict_to_args(d, extra_args)
        assert result == expected

    def test_with_none_extra_args(self):
        d = {
            "args": ["user"],
            "image": "ubuntu:22.04",
        }
        extra_args = None

        expected = "--user -- ubuntu:22.04"

        result = yaml_dict_to_args(d, extra_args)
        assert result == expected

    @pytest.mark.skip
    def test_realisic_yaml(self):
        result = collect_arguments(".")

        expected = {
            "args": ["nvidia", "x11", "user", "pull", "deps", "git", "lazygit", "pixi"],
            "image": "ubuntu:22.04",
        }

        assert result == expected

    def test_deduplicate_extensions(self):
        extensions = ["nvidia", "x11", "user", "nvidia", "git", "x11"]
        expected = ["nvidia", "x11", "user", "git"]
        result = deduplicate_extensions(extensions)
        assert result == expected

    def test_deduplicate_extensions_empty(self):
        extensions = []
        expected = []
        result = deduplicate_extensions(extensions)
        assert result == expected

    def test_deduplicate_extensions_no_duplicates(self):
        extensions = ["nvidia", "x11", "user"]
        expected = ["nvidia", "x11", "user"]
        result = deduplicate_extensions(extensions)
        assert result == expected

    def test_load_global_config_no_file(self):
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = pathlib.Path("/nonexistent")
            result = load_global_config()
            assert result == {}

    def test_load_global_config_with_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            config_data = {"args": ["codex", "vim"]}
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = load_global_config()
                assert result == config_data

    def test_load_global_config_with_malformed_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            # Write malformed YAML content
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("args: [codex, vim\nimage: ubuntu:20.04")  # missing closing bracket

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = load_global_config()
                # Should return empty dict when YAML parsing fails
                assert result == {}

    def test_collect_arguments_with_global_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config with image and args
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"args": ["codex", "vim"], "image": "ubuntu:20.04"}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config that overrides image
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {"args": ["nvidia", "x11"], "image": "ubuntu:22.04"}
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Global extensions should come first, then project extensions, deduplicated
                # Project image should override global image
                expected = {"args": ["codex", "vim", "nvidia", "x11"], "image": "ubuntu:22.04"}
                assert result == expected

    def test_collect_arguments_global_image_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config with image and args
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"args": ["codex", "vim"], "image": "ubuntu:20.04"}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config without image
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {"args": ["nvidia", "x11"]}
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should use global image when project doesn't specify one
                expected = {"args": ["codex", "vim", "nvidia", "x11"], "image": "ubuntu:20.04"}
                assert result == expected

    def test_collect_arguments_with_duplicate_extensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config with overlapping extensions
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"args": ["codex", "nvidia", "vim"]}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config with some same extensions
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {"args": ["nvidia", "x11", "codex"], "image": "ubuntu:22.04"}
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should be deduplicated, preserving order (global first, then new from project)
                expected = {"args": ["codex", "nvidia", "vim", "x11"], "image": "ubuntu:22.04"}
                assert result == expected

    def test_collect_arguments_missing_args_and_image(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config without args and image
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"other_setting": "value"}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config without args and image
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {"another_setting": "value2"}
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should merge settings but no args or image
                expected = {"other_setting": "value", "another_setting": "value2"}
                assert result == expected
