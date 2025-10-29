"""Test renv extension persistence and change detection.

This test verifies that renv properly stores and retrieves extension lists
to avoid unnecessary container rebuilds when extensions haven't changed.
"""

from unittest.mock import Mock, patch
from rockerc.renv import build_rocker_config, RepoSpec
from rockerc.core import get_container_extensions, extensions_changed, prepare_launch_plan


class TestRenvExtensionPersistence:
    """Test renv's extension persistence functionality."""

    def test_build_rocker_config_processes_extensions_correctly(self):
        """Test that build_rocker_config properly processes extensions for storage."""
        repo_spec = RepoSpec.parse("blooop/bencher@main")

        # Mock the config loading and directory checks
        with (
            patch("rockerc.renv.load_renv_rockerc_config") as mock_global_config,
            patch("rockerc.renv.get_worktree_dir") as mock_worktree,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            # Setup mocks
            import pathlib

            fake_path = pathlib.Path("/fake/worktree")
            mock_worktree.return_value = fake_path
            mock_exists.return_value = True

            # Mock config with extensions that match the real user output
            expected_extensions = [
                "persist-image",
                "fzf",
                "auto",
                "deps-devtools",
                "pull",
                "x11",
                "user",
                "cwd",
                "git",
                "git-clone",
                "ssh",
                "ssh-client",
                "jquery",
                "pixi",
            ]
            mock_global_config.return_value = {"args": expected_extensions}

            # Call build_rocker_config
            config, _ = build_rocker_config(repo_spec)

            # Verify extensions are processed correctly
            processed_extensions = config.get("args", [])

            # Should have 'auto' converted to proper path
            auto_extensions = [ext for ext in processed_extensions if ext.startswith("auto=")]
            assert len(auto_extensions) == 1
            assert "~/renv/blooop/bencher/main/bencher" in auto_extensions[0]

            # Should not have 'cwd' extension (filtered out)
            assert "cwd" not in processed_extensions

            # Should have all other expected extensions
            expected_final = [
                "persist-image",
                "fzf",
                "deps-devtools",
                "pull",
                "x11",
                "user",
                "git",
                "git-clone",
                "ssh",
                "ssh-client",
                "jquery",
                "pixi",
            ]
            for ext in expected_final:
                assert ext in processed_extensions

    def test_prepare_launch_plan_extension_comparison(self):
        """Test that prepare_launch_plan properly compares current vs stored extensions."""
        container_name = "bencher.main"

        # Current extensions (what we want to use)
        current_extensions = [
            "auto=~/renv/blooop/bencher/main/bencher",
            "deps-devtools",
            "fzf",
            "git",
            "git-clone",
            "jquery",
            "persist-image",
            "pixi",
            "pull",
            "ssh",
            "ssh-client",
            "user",
            "x11",
        ]

        # Stored extensions (what's in the container) - missing jquery and pixi
        stored_extensions = [
            "auto=~/renv/blooop/bencher/main/bencher",
            "deps-devtools",
            "fzf",
            "git",
            "git-clone",
            "persist-image",
            "pull",
            "ssh",
            "ssh-client",
            "user",
            "x11",
        ]

        # Mock container operations
        with (
            patch("rockerc.core.container_exists") as mock_exists,
            patch("rockerc.core.get_container_extensions") as mock_get_ext,
            patch("rockerc.core.container_is_running") as mock_running,
            patch("rockerc.core.stop_and_remove_container") as mock_remove,
            patch("rockerc.core.render_extension_comparison_table") as mock_table,
        ):
            mock_exists.return_value = True
            mock_get_ext.return_value = stored_extensions
            mock_running.return_value = True
            mock_table.return_value = "Extensions changed table"

            # Call prepare_launch_plan
            args_dict = {"image": "ubuntu:20.04"}
            _ = prepare_launch_plan(
                args_dict=args_dict,
                extra_cli="",
                container_name=container_name,
                vscode=False,
                force=False,
                path="/fake/path",
                extensions=current_extensions,
                extra_volumes=[],
                mount_target="/workspace",
            )

            # Should detect changes and remove container
            mock_remove.assert_called_once_with(container_name)

            # Should detect the extensions as changed
            assert extensions_changed(current_extensions, stored_extensions)

    def test_renv_auto_extension_mismatch_issue(self):
        """Test the specific issue where auto extension path causes rebuild mismatch."""
        # This reproduces the user's issue where stored shows "" but current shows "auto=path"

        # Current extensions as processed by renv (what the user sees in "Current" column)
        current_extensions = [
            "auto=~/renv/blooop/bencher/main/bencher",
            "deps-devtools",
            "fzf",
            "git",
            "git-clone",
            "jquery",
            "persist-image",
            "pixi",
            "pull",
            "ssh",
            "ssh-client",
            "user",
            "x11",
        ]

        # Stored extensions as they appear in the container (the issue is here)
        # The problem is likely that "auto" gets stored without the path, causing a mismatch
        stored_extensions = [
            "auto",
            "deps-devtools",
            "fzf",
            "git",
            "git-clone",
            "jquery",
            "persist-image",
            "pixi",
            "pull",
            "ssh",
            "ssh-client",
            "user",
            "x11",
        ]

        # This should detect as changed because "auto" != "auto=~/renv/blooop/bencher/main/bencher"
        assert extensions_changed(current_extensions, stored_extensions)

        # This demonstrates the core issue: auto extension path handling
        # The stored version has "auto" but current has "auto=path"
        current_auto = [ext for ext in current_extensions if ext.startswith("auto")]
        stored_auto = [ext for ext in stored_extensions if ext.startswith("auto")]

        assert current_auto == ["auto=~/renv/blooop/bencher/main/bencher"]
        assert stored_auto == ["auto"]

        # When sorted for comparison, these are different
        assert sorted(current_extensions) != sorted(stored_extensions)

    def test_renv_extension_environment_variable_format(self):
        """Test that the ROCKERC_EXTENSIONS environment variable is properly formatted."""
        # Test the format matches what get_container_extensions expects
        extensions = ["nvidia", "user", "x11", "git"]

        # Should be sorted and comma-separated
        expected = "git,nvidia,user,x11"

        # Mock subprocess to simulate docker inspect output
        mock_result = Mock()
        mock_result.stdout = f"PATH=/usr/bin\nROCKERC_EXTENSIONS={expected}\nHOME=/root\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            retrieved = get_container_extensions("test_container")

        # Should retrieve the same sorted list
        assert retrieved == ["git", "nvidia", "user", "x11"]

        # Should not detect changes when the same
        assert not extensions_changed(extensions, retrieved)

    def test_renv_missing_container_extensions(self):
        """Test behavior when container has no stored extensions."""
        # Simulate container without ROCKERC_EXTENSIONS
        mock_result = Mock()
        mock_result.stdout = "PATH=/usr/bin\nHOME=/root\n"  # No ROCKERC_EXTENSIONS
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            retrieved = get_container_extensions("test_container")

        # Should return None
        assert retrieved is None

        # Should detect as changed (missing extensions treated as changed)
        current = ["git", "nvidia"]
        assert extensions_changed(current, retrieved)

    def test_exact_user_scenario_missing_stored_extensions(self):
        """Test the exact scenario from user's output: container exists but has no stored extensions."""
        # This reproduces the exact user output where "Stored" column is empty for all extensions
        current_extensions = [
            "auto=~/renv/blooop/bencher/main/bencher",
            "deps-devtools",
            "fzf",
            "git",
            "git-clone",
            "jquery",
            "persist-image",
            "pixi",
            "pull",
            "ssh",
            "ssh-client",
            "user",
            "x11",
        ]

        # Container exists but has no ROCKERC_EXTENSIONS (empty stored extensions)
        stored_extensions = (
            None  # This is what get_container_extensions returns when env var is missing
        )

        # This should always trigger a rebuild when stored is None
        assert extensions_changed(current_extensions, stored_extensions)

        # Test with container_exists returning True but get_container_extensions returning None
        with (
            patch("rockerc.core.container_exists") as mock_exists,
            patch("rockerc.core.get_container_extensions") as mock_get_ext,
            patch("rockerc.core.container_is_running") as mock_running,
            patch("rockerc.core.stop_and_remove_container") as mock_remove,
            patch("rockerc.core.render_extension_comparison_table") as mock_table,
        ):
            mock_exists.return_value = True
            mock_get_ext.return_value = None  # No stored extensions
            mock_running.return_value = True
            mock_table.return_value = "Extensions changed table"

            # Call prepare_launch_plan - this should trigger a rebuild
            args_dict = {"image": "ubuntu:20.04"}
            _ = prepare_launch_plan(
                args_dict=args_dict,
                extra_cli="",
                container_name="bencher.main",
                vscode=False,
                force=False,
                path="/fake/path",
                extensions=current_extensions,
                extra_volumes=[],
                mount_target="/workspace",
            )

            # Should detect changes and remove container for rebuild
            mock_remove.assert_called_once_with("bencher.main")

    def test_extensions_stored_correctly_after_rebuild(self):
        """Test that after a rebuild, extensions are stored and no further rebuilds occur."""
        current_extensions = [
            "auto=~/renv/blooop/bencher/main/bencher",
            "deps-devtools",
            "fzf",
            "git",
            "git-clone",
            "jquery",
            "persist-image",
            "pixi",
            "pull",
            "ssh",
            "ssh-client",
            "user",
            "x11",
        ]

        # Test second run: container now has stored extensions that match current
        with (
            patch("rockerc.core.container_exists") as mock_exists,
            patch("rockerc.core.get_container_extensions") as mock_get_ext,
            patch("rockerc.core.container_is_running") as mock_running,
            patch("rockerc.core.stop_and_remove_container") as mock_remove,
        ):
            mock_exists.return_value = True
            # Now container has the correct stored extensions
            mock_get_ext.return_value = current_extensions.copy()
            mock_running.return_value = True

            # Call prepare_launch_plan again - this should NOT trigger a rebuild
            args_dict = {"image": "ubuntu:20.04"}
            _ = prepare_launch_plan(
                args_dict=args_dict,
                extra_cli="",
                container_name="bencher.main",
                vscode=False,
                force=False,
                path="/fake/path",
                extensions=current_extensions,
                extra_volumes=[],
                mount_target="/workspace",
            )

            # Should NOT remove container (no rebuild needed)
            mock_remove.assert_not_called()

            # Extensions should not be detected as changed
            assert not extensions_changed(current_extensions, current_extensions)

    def test_add_extension_env_handles_auto_with_path(self):
        """Test that add_extension_env correctly handles auto=path extensions after the fix."""
        from rockerc.core import add_extension_env

        # This reproduces the user's scenario
        extensions_with_auto_path = ["auto=~/renv/blooop/bencher/main/bencher", "git", "user"]
        base_args = "--name test"

        # After the fix, this should add the environment variable correctly
        result = add_extension_env(base_args, extensions_with_auto_path)

        # Should now contain ROCKERC_EXTENSIONS with all extensions
        assert "ROCKERC_EXTENSIONS" in result
        # Should have all extensions sorted
        expected_extensions = "auto=~/renv/blooop/bencher/main/bencher,git,user"
        assert f"ROCKERC_EXTENSIONS={expected_extensions}" in result

        # Test that simple extensions still work fine
        simple_extensions = ["git", "user", "x11"]
        result_simple = add_extension_env(base_args, simple_extensions)
        assert "ROCKERC_EXTENSIONS=git,user,x11" in result_simple
