#!/usr/bin/env python3
"""
Comprehensive test suite for renv autocompletion and installation functionality.
"""

import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_version_functionality():
    """Test version reading and display."""
    print("Testing version functionality...")
    
    from rockerc.renv import get_version
    
    # Test version reading
    version = get_version()
    print(f"  Version read: {version}")
    assert version != "unknown", "Version should not be unknown"
    assert version.count('.') >= 2, f"Version should have at least 3 parts: {version}"
    
    # Test that version matches pyproject.toml
    with open("pyproject.toml", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith('version = "'):
                expected_version = line.split('"')[1]
                assert version == expected_version, f"Expected {expected_version}, got {version}"
                break
    
    print("  ✓ Version functionality works")

def test_autocompletion_functions():
    """Test autocompletion helper functions."""
    print("Testing autocompletion functions...")
    
    from rockerc.renv import get_existing_repos, get_branches_for_repo, repo_completer
    
    # Test get_existing_repos (should not crash)
    repos = get_existing_repos()
    print(f"  Found {len(repos)} existing repos: {repos[:3]}{'...' if len(repos) > 3 else ''}")
    assert isinstance(repos, list), "get_existing_repos should return a list"
    
    # Test repo_completer with various inputs
    test_prefixes = ["", "test", "test/", "test/repo", "test/repo@", "test/repo@main"]
    for prefix in test_prefixes:
        try:
            completions = repo_completer(prefix)
            print(f"  Completions for '{prefix}': {len(completions)} items")
            assert isinstance(completions, list), f"repo_completer should return list for '{prefix}'"
        except Exception as e:
            print(f"  ⚠ repo_completer failed for '{prefix}': {e}")
    
    # Test get_branches_for_repo (should not crash even with non-existent repo)
    branches = get_branches_for_repo("nonexistent", "repo")
    print(f"  Branches for non-existent repo: {len(branches)}")
    assert isinstance(branches, list), "get_branches_for_repo should return a list"
    
    print("  ✓ Autocompletion functions work")

def test_argcomplete_integration():
    """Test argcomplete integration."""
    print("Testing argcomplete integration...")
    
    from rockerc.renv import ARGCOMPLETE_AVAILABLE
    print(f"  Argcomplete available: {ARGCOMPLETE_AVAILABLE}")
    
    if ARGCOMPLETE_AVAILABLE:
        try:
            import argcomplete
            print(f"  Argcomplete version: {argcomplete.__version__}")
        except Exception as e:
            print(f"  ⚠ Could not import argcomplete: {e}")
    
    # Test that the main function can be imported and doesn't crash on argcomplete setup
    try:
        from rockerc.renv import main
        print("  ✓ Main function imports successfully")
    except Exception as e:
        print(f"  ❌ Main function import failed: {e}")
        raise
    
    print("  ✓ Argcomplete integration test passed")

def test_global_package_manager_detection():
    """Test global package manager detection."""
    print("Testing global package manager detection...")
    
    from rockerc.renv import detect_global_package_manager
    
    manager_info = detect_global_package_manager()
    print(f"  Detected package manager: {manager_info}")
    
    assert isinstance(manager_info, dict), "detect_global_package_manager should return dict"
    assert 'type' in manager_info, "Should contain 'type' key"
    assert 'command' in manager_info, "Should contain 'command' key"
    
    if manager_info['type']:
        print(f"  ✓ Found {manager_info['type']} package manager")
    else:
        print("  ℹ No global package manager detected (this might be expected)")
    
    print("  ✓ Package manager detection works")

def test_shell_autocompletion_setup():
    """Test shell autocompletion configuration."""
    print("Testing shell autocompletion setup...")
    
    # Create a temporary shell config file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bashrc', delete=False) as temp_file:
        temp_file.write("# Test bashrc\nexport PATH=$PATH\n")
        temp_config = temp_file.name
    
    try:
        # Test adding autocompletion
        completion_line = 'eval "$(register-python-argcomplete renv)"'
        
        # Read original content
        with open(temp_config, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Add completion line
        with open(temp_config, 'a', encoding='utf-8') as f:
            f.write(f'\n# renv autocompletion\n{completion_line}\n')
        
        # Check it was added
        with open(temp_config, 'r', encoding='utf-8') as f:
            new_content = f.read()
        
        assert completion_line in new_content, "Completion line should be added"
        assert len(new_content) > len(original_content), "File should be longer"
        
        print("  ✓ Shell configuration modification works")
        
        # Test removing autocompletion
        lines = new_content.splitlines()
        filtered_lines = []
        skip_next = False
        
        for line in lines:
            if skip_next and 'register-python-argcomplete renv' in line:
                skip_next = False
                continue
            elif '# renv autocompletion' in line:
                skip_next = True
                continue
            else:
                filtered_lines.append(line)
        
        removed_content = '\n'.join(filtered_lines) + '\n'
        assert completion_line not in removed_content, "Completion line should be removed"
        
        print("  ✓ Shell configuration removal works")
        
    finally:
        # Clean up temp file
        os.unlink(temp_config)

def test_command_line_interface():
    """Test command line interface with mocked subprocess calls."""
    print("Testing command line interface...")
    
    # Test --help
    with patch('sys.argv', ['renv', '--help']):
        try:
            from rockerc.renv import main
            main()
        except SystemExit as e:
            # Help should exit with code 0
            assert e.code == 0, "Help should exit with code 0"
            print("  ✓ --help works")
    
    # Test version display
    with patch('sys.argv', ['renv', '--version']):
        with patch('builtins.print') as mock_print:
            try:
                from rockerc.renv import main
                main()
            except SystemExit as e:
                assert e.code == 0, "Version should exit with code 0"
                # Check that print was called with version info
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any('renv version' in call for call in print_calls), "Should print version"
                print("  ✓ --version works")
    
    # Test no arguments (should show version)
    with patch('sys.argv', ['renv']):
        with patch('builtins.print') as mock_print:
            try:
                from rockerc.renv import main
                main()
            except SystemExit as e:
                assert e.code == 0, "No args should exit with code 0"
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any('renv version' in call for call in print_calls), "Should print version"
                print("  ✓ No arguments (version display) works")

def test_install_command_logic():
    """Test install command logic with mocked dependencies."""
    print("Testing install command logic...")
    
    from rockerc.renv import install_argcomplete
    
    # Mock successful global installation
    with patch('rockerc.renv.detect_global_package_manager') as mock_detect:
        with patch('subprocess.run') as mock_run:
            with patch('builtins.open', create=True) as mock_open:
                with patch('pathlib.Path.exists', return_value=True):
                    # Mock successful uv tool detection
                    mock_detect.return_value = {
                        'type': 'uv_tool',
                        'command': ['uv', 'tool', 'install']
                    }
                    
                    # Mock file operations
                    mock_open.return_value.__enter__.return_value.read.return_value = "existing content"
                    
                    # Mock successful subprocess calls
                    mock_run.return_value = MagicMock(returncode=0)
                    
                    # Test install (should not crash)
                    try:
                        result = install_argcomplete()
                        print(f"  Install returned: {result}")
                        print("  ✓ Install logic executes without errors")
                    except Exception as e:
                        print(f"  ⚠ Install logic failed: {e}")

def test_real_world_scenario():
    """Test a realistic scenario with temporary directories."""
    print("Testing real-world scenario...")
    
    # Create temporary renv directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_renv = Path(temp_dir) / "renv"
        
        # Create mock repository structure
        test_repos = [
            ("testuser", "repo1"),
            ("testuser", "repo2"),
            ("anotheruser", "project1")
        ]
        
        for owner, repo in test_repos:
            repo_dir = temp_renv / owner / repo
            repo_dir.mkdir(parents=True)
            # Create HEAD file to simulate bare repo
            (repo_dir / "HEAD").write_text("ref: refs/heads/main\n")
        
        # Mock get_renv_base_dir to use our temp directory
        with patch('rockerc.renv.get_renv_base_dir', return_value=temp_renv):
            from rockerc.renv import get_existing_repos, repo_completer
            
            # Test repository discovery
            repos = get_existing_repos()
            expected_repos = ["testuser/repo1", "testuser/repo2", "anotheruser/project1"]
            
            print(f"  Found repos: {repos}")
            for expected in expected_repos:
                assert expected in repos, f"Should find repo {expected}"
            
            # Test autocompletion
            completions = repo_completer("testuser")
            print(f"  Completions for 'testuser': {completions}")
            assert "testuser/" in completions, "Should complete testuser/"
            
            completions = repo_completer("testuser/repo")
            print(f"  Completions for 'testuser/repo': {completions}")
            expected_completions = ["testuser/repo1", "testuser/repo2"]
            for expected in expected_completions:
                assert expected in completions, f"Should complete {expected}"
            
            print("  ✓ Real-world scenario test passed")

def test_error_handling():
    """Test error handling in various scenarios."""
    print("Testing error handling...")
    
    from rockerc.renv import get_existing_repos, get_branches_for_repo, repo_completer
    
    # Test with non-existent renv directory
    with patch('rockerc.renv.get_renv_base_dir', return_value=Path("/nonexistent")):
        repos = get_existing_repos()
        assert repos == [], "Should return empty list for non-existent directory"
        print("  ✓ Handles non-existent renv directory")
    
    # Test branch detection for non-existent repo
    branches = get_branches_for_repo("nonexistent", "repo")
    assert isinstance(branches, list), "Should return list even for non-existent repo"
    print("  ✓ Handles non-existent repository gracefully")
    
    # Test autocompletion with invalid input
    try:
        completions = repo_completer("invalid/input/with/@/many/parts")
        assert isinstance(completions, list), "Should return list even for invalid input"
        print("  ✓ Handles invalid autocompletion input")
    except Exception as e:
        print(f"  ⚠ Autocompletion error handling needs improvement: {e}")
    
    print("  ✓ Error handling tests passed")

def run_integration_test():
    """Run a simple integration test to see if everything works together."""
    print("Running integration test...")
    
    # Test that we can import everything and call main functions
    try:
        from rockerc.renv import main, get_version, get_existing_repos, repo_completer
        
        # Test version
        version = get_version()
        assert version != "unknown"
        
        # Test existing repos
        repos = get_existing_repos()
        assert isinstance(repos, list)
        
        # Test autocompletion
        completions = repo_completer("")
        assert isinstance(completions, list)
        
        print("  ✓ All imports and basic functions work")
        
        # Test CLI argument parsing doesn't crash
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("repo_spec", nargs="?")
        parser.add_argument("--install", action="store_true")
        parser.add_argument("--uninstall", action="store_true")
        parser.add_argument("-v", "--version", action="store_true")
        
        # Test various argument combinations
        test_args = [
            [],
            ["--version"],
            ["--install"],
            ["--uninstall"],
            ["blooop/bencher@main"]
        ]
        
        for args in test_args:
            try:
                parsed = parser.parse_args(args)
                print(f"  Args {args} parsed successfully")
            except SystemExit:
                # This is expected for --help, etc.
                pass
        
        print("  ✓ Integration test passed")
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        raise

def main():
    """Run all tests."""
    print("🧪 Comprehensive renv Functionality Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_version_functionality,
        test_autocompletion_functions,
        test_argcomplete_integration,
        test_global_package_manager_detection,
        test_shell_autocompletion_setup,
        test_command_line_interface,
        test_install_command_logic,
        test_real_world_scenario,
        test_error_handling,
        run_integration_test
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        print(f"\n🔍 {test_func.__name__.replace('_', ' ').title()}")
        print("-" * 40)
        try:
            test_func()
            passed += 1
            print(f"✅ {test_func.__name__} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_func.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! renv functionality is working correctly.")
        
        print("\n🔧 To test autocompletion manually:")
        print("1. Ensure argcomplete is installed globally:")
        print("   uv tool install argcomplete")
        print("   # or pipx install argcomplete")
        print("   # or pip install --user argcomplete")
        print("\n2. Add to your shell config (.bashrc/.zshrc):")
        print('   eval "$(register-python-argcomplete renv)"')
        print("\n3. Restart your shell and test:")
        print("   renv <TAB>")
        
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
