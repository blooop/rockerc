from unittest import TestCase
from unittest.mock import patch
import pytest
import tempfile
import pathlib
import yaml
from rockerc.rockerc import (
    yaml_dict_to_args,
    collect_arguments,
    deduplicate_extensions,
)
from rockerc.cli_args import FlagSpec, consume_flags


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

    def test_collect_arguments_missing_args_and_image(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty global config
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"other_setting": "value", "another_setting": "value2"}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config without args and image
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {"some_setting": "value"}
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should merge settings but no args or image
                expected = {
                    "other_setting": "value",
                    "another_setting": "value2",
                    "some_setting": "value",
                }
                assert result == expected

    def test_extension_blacklist_with_list(self):
        d = {
            "image": "ubuntu:24.04",
            "args": [
                "persist-image",
                "x11",
                "user",
                "pull",
                "git",
                "pixi",
                "cwd",
                "claude",
                "codex",
                "fzf",
                "ssh",
                "ssh-client",
                "spec-kit",
            ],
            "extension-blacklist": ["nvidia"],
        }
        # extension-blacklist is removed - it's only for internal filtering
        expected = "--persist-image --x11 --user --pull --git --pixi --cwd --claude --codex --fzf --ssh --ssh-client --spec-kit -- ubuntu:24.04"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_extension_blacklist_with_multiple_items(self):
        d = {
            "image": "ubuntu:22.04",
            "args": ["x11", "user"],
            "extension-blacklist": ["nvidia", "cuda", "opencl"],
        }
        # extension-blacklist is removed - it's only for internal filtering
        expected = "--x11 --user -- ubuntu:22.04"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_extension_blacklist_with_single_string(self):
        d = {"image": "ubuntu:22.04", "args": ["x11", "user"], "extension-blacklist": "nvidia"}
        # extension-blacklist is removed - it's only for internal filtering
        expected = "--x11 --user -- ubuntu:22.04"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_extension_blacklist_with_no_args(self):
        d = {"image": "ubuntu:22.04", "extension-blacklist": ["nvidia"]}
        # extension-blacklist is removed - it's only for internal filtering
        expected = " -- ubuntu:22.04"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_extension_blacklist_empty_list(self):
        d = {"image": "ubuntu:22.04", "args": ["x11"], "extension-blacklist": []}
        expected = "--x11 -- ubuntu:22.04"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_extension_blacklist_none(self):
        d = {"image": "ubuntu:22.04", "args": ["x11"], "extension-blacklist": None}
        expected = "--x11 -- ubuntu:22.04"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_collect_arguments_with_global_extension_blacklist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config with extension-blacklist
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"args": ["codex", "vim"], "extension-blacklist": ["nvidia", "cuda"]}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config with additional extension-blacklist
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {
                "args": ["x11"],
                "extension-blacklist": ["opencl"],
                "image": "ubuntu:22.04",
            }
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should merge extension-blacklists and deduplicate
                expected = {
                    "args": ["codex", "vim", "x11"],
                    "extension-blacklist": ["nvidia", "cuda", "opencl"],
                    "image": "ubuntu:22.04",
                }
                assert result == expected

    def test_collect_arguments_with_duplicate_extension_blacklist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config with extension-blacklist
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"extension-blacklist": ["nvidia", "cuda"]}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config with overlapping extension-blacklist
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {
                "args": ["x11"],
                "extension-blacklist": ["cuda", "opencl"],
                "image": "ubuntu:22.04",
            }
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should deduplicate extension-blacklists
                expected = {
                    "args": ["x11"],
                    "extension-blacklist": ["nvidia", "cuda", "opencl"],
                    "image": "ubuntu:22.04",
                }
                assert result == expected

    def test_collect_arguments_with_string_extension_blacklist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config with string extension-blacklist
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"extension-blacklist": "nvidia"}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config with list extension-blacklist
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {
                "args": ["x11"],
                "extension-blacklist": ["cuda"],
                "image": "ubuntu:22.04",
            }
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should merge string and list extension-blacklists
                expected = {
                    "args": ["x11"],
                    "extension-blacklist": ["nvidia", "cuda"],
                    "image": "ubuntu:22.04",
                }
                assert result == expected

    def test_collect_arguments_global_extension_blacklist_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config with extension-blacklist only
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"extension-blacklist": ["nvidia"]}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config without extension-blacklist
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {"args": ["x11"], "image": "ubuntu:22.04"}
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should use global extension-blacklist
                expected = {
                    "args": ["x11"],
                    "extension-blacklist": ["nvidia"],
                    "image": "ubuntu:22.04",
                }
                assert result == expected

    def test_collect_arguments_project_extension_blacklist_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config without extension-blacklist
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"args": ["vim"]}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config with extension-blacklist
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {
                "args": ["x11"],
                "extension-blacklist": ["nvidia"],
                "image": "ubuntu:22.04",
            }
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Should use project extension-blacklist
                expected = {
                    "args": ["vim", "x11"],
                    "extension-blacklist": ["nvidia"],
                    "image": "ubuntu:22.04",
                }
                assert result == expected

    def test_collect_arguments_filters_blacklisted_extensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config with nvidia in both args and extension-blacklist
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {
                "args": ["x11", "nvidia", "user", "cuda"],
                "extension-blacklist": ["nvidia", "cuda"],
                "image": "ubuntu:22.04",
            }
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # nvidia and cuda should be filtered out of args
                expected = {
                    "args": ["x11", "user"],
                    "extension-blacklist": ["nvidia", "cuda"],
                    "image": "ubuntu:22.04",
                }
                assert result == expected

    def test_collect_arguments_filters_mixed_global_project_blacklist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config with some args and blacklist
            global_config_path = pathlib.Path(tmpdir) / ".rockerc.yaml"
            global_config = {"args": ["nvidia", "codex"], "extension-blacklist": ["nvidia"]}
            with open(global_config_path, "w", encoding="utf-8") as f:
                yaml.dump(global_config, f)

            # Create project config with overlapping args and additional blacklist
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {
                "args": ["x11", "cuda", "user"],
                "extension-blacklist": ["cuda"],
                "image": "ubuntu:22.04",
            }
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # Both nvidia and cuda should be filtered out
                expected = {
                    "args": ["codex", "x11", "user"],
                    "extension-blacklist": ["nvidia", "cuda"],
                    "image": "ubuntu:22.04",
                }
                assert result == expected

    def test_collect_arguments_no_filtering_when_no_blacklist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config without extension-blacklist
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {"args": ["x11", "nvidia", "user"], "image": "ubuntu:22.04"}
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # No filtering should occur
                expected = {"args": ["x11", "nvidia", "user"], "image": "ubuntu:22.04"}
                assert result == expected

    def test_collect_arguments_filters_all_blacklisted_extensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config where all args are blacklisted
            project_dir = pathlib.Path(tmpdir) / "project"
            project_dir.mkdir()
            project_config_path = project_dir / "rockerc.yaml"
            project_config = {
                "args": ["nvidia", "cuda"],
                "extension-blacklist": ["nvidia", "cuda"],
                "image": "ubuntu:22.04",
            }
            with open(project_config_path, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = pathlib.Path(tmpdir)
                result = collect_arguments(str(project_dir))

                # All args should be filtered out
                expected = {
                    "args": [],
                    "extension-blacklist": ["nvidia", "cuda"],
                    "image": "ubuntu:22.04",
                }
                assert result == expected

    def _rockerc_flag_specs(self):
        return [
            FlagSpec("--vsc", key="vsc"),
            FlagSpec("--force", aliases=("-f",), key="force"),
            FlagSpec("--verbose", aliases=("-v",), key="verbose"),
            FlagSpec("--show-dockerfile", key="show_dockerfile"),
        ]

    def test_parse_extra_flags_filters_force_flags(self):
        """Test that --force and -f flags are filtered out from CLI arguments."""
        argv = ["--some-arg", "-f", "--another-arg", "value", "--force"]
        values, remaining = consume_flags(argv, self._rockerc_flag_specs())

        assert values["force"] is True
        assert values["vsc"] is False
        assert values["verbose"] is False
        assert values["show_dockerfile"] is False
        assert remaining == ["--some-arg", "--another-arg", "value"]

    def test_parse_extra_flags_filters_verbose_flags(self):
        """Test that --verbose and -v flags are filtered out from CLI arguments."""
        argv = ["--arg1", "-v", "--arg2", "--verbose"]
        values, remaining = consume_flags(argv, self._rockerc_flag_specs())

        assert values["force"] is False
        assert values["vsc"] is False
        assert values["verbose"] is True
        assert values["show_dockerfile"] is False
        assert remaining == ["--arg1", "--arg2"]

    def test_parse_extra_flags_filters_vsc_flag(self):
        """Test that --vsc flag is filtered out from CLI arguments."""
        argv = ["--arg1", "--vsc", "--arg2"]
        values, remaining = consume_flags(argv, self._rockerc_flag_specs())

        assert values["force"] is False
        assert values["vsc"] is True
        assert values["verbose"] is False
        assert values["show_dockerfile"] is False
        assert remaining == ["--arg1", "--arg2"]

    def test_parse_extra_flags_no_special_flags(self):
        """Test that when no special flags are present, all args remain."""
        argv = ["--arg1", "value1", "--arg2", "value2"]
        values, remaining = consume_flags(argv, self._rockerc_flag_specs())

        assert values["force"] is False
        assert values["vsc"] is False
        assert values["verbose"] is False
        assert values["show_dockerfile"] is False
        assert remaining == ["--arg1", "value1", "--arg2", "value2"]

    def test_parse_extra_flags_filters_show_dockerfile_flag(self):
        """Test that --show-dockerfile flag is filtered out from CLI arguments."""
        argv = ["--arg1", "--show-dockerfile", "--arg2"]
        values, remaining = consume_flags(argv, self._rockerc_flag_specs())

        assert values["force"] is False
        assert values["vsc"] is False
        assert values["verbose"] is False
        assert values["show_dockerfile"] is True
        assert remaining == ["--arg1", "--arg2"]
