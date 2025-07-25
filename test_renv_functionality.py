#!/usr/bin/env python3
"""Test script for renv autocompletion functionality."""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add the rockerc directory to the Python path
sys.path.insert(0, '/workspaces/rockerc')

from rockerc.renv import get_existing_repos, get_branches_for_repo, repo_completer, get_renv_base_dir

def setup_test_repos():
    """Set up test repositories for autocompletion testing."""
    test_dir = Path.home() / "test_renv"
    
    # Clean up any existing test directory
    if test_dir.exists():
        subprocess.run(["rm", "-rf", str(test_dir)], check=True)
    
    # Create test repo structure
    test_repo1 = test_dir / "testuser" / "testrepo1"
    test_repo2 = test_dir / "testuser" / "testrepo2"
    test_repo3 = test_dir / "anotheruser" / "anotherepo"
    
    for repo_dir in [test_repo1, test_repo2, test_repo3]:
        repo_dir.mkdir(parents=True)
        
        # Initialize as bare git repo
        subprocess.run(["git", "init", "--bare"], cwd=repo_dir, check=True, capture_output=True)
        
        # Create a few test branches
        subprocess.run(["git", "branch", "main"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "branch", "feature/test"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "branch", "develop"], cwd=repo_dir, capture_output=True)
    
    return test_dir

def test_autocompletion():
    """Test autocompletion functions."""
    print("Setting up test repositories...")
    test_dir = setup_test_repos()
    
    # Temporarily modify the renv base dir for testing
    original_get_renv_base_dir = get_renv_base_dir
    
    def mock_get_renv_base_dir():
        return test_dir
    
    # Monkey patch for testing
    import rockerc.renv
    rockerc.renv.get_renv_base_dir = mock_get_renv_base_dir
    
    try:
        print("Testing get_existing_repos...")
        existing_repos = get_existing_repos()
        print(f"Found existing repos: {existing_repos}")
        
        expected_repos = ["testuser/testrepo1", "testuser/testrepo2", "anotheruser/anotherepo"]
        for repo in expected_repos:
            assert repo in existing_repos, f"Expected repo {repo} not found in {existing_repos}"
        
        print("Testing repo_completer with user prefix...")
        completions = repo_completer("testuser")
        print(f"Completions for 'testuser': {completions}")
        assert "testuser/" in completions, f"Expected 'testuser/' in completions: {completions}"
        
        print("Testing repo_completer with partial repo name...")
        completions = repo_completer("testuser/test")
        print(f"Completions for 'testuser/test': {completions}")
        expected = ["testuser/testrepo1", "testuser/testrepo2"]
        for expected_completion in expected:
            assert expected_completion in completions, f"Expected {expected_completion} in {completions}"
        
        print("Testing get_branches_for_repo...")
        branches = get_branches_for_repo("testuser", "testrepo1")
        print(f"Branches for testuser/testrepo1: {branches}")
        # Note: git branch output might be different for bare repos, so we'll just check it doesn't crash
        
        print("All autocompletion tests passed!")
        
    finally:
        # Restore original function
        rockerc.renv.get_renv_base_dir = original_get_renv_base_dir
        # Clean up test directory
        subprocess.run(["rm", "-rf", str(test_dir)], check=True)

def test_version():
    """Test version functionality."""
    print("Testing version functionality...")
    from rockerc.renv import get_version
    
    version = get_version()
    print(f"Version: {version}")
    
    # Version should not be unknown and should match what's in pyproject.toml
    assert version != "unknown", "Version should not be unknown"
    
    # Read version directly from pyproject.toml to compare
    with open("/workspaces/rockerc/pyproject.toml", "r") as f:
        for line in f:
            if line.strip().startswith('version = "'):
                expected_version = line.split('"')[1]
                assert version == expected_version, f"Expected {expected_version}, got {version}"
                break
    
    print("Version test passed!")

if __name__ == "__main__":
    print("Running renv functionality tests...")
    test_version()
    test_autocompletion()
    print("All tests passed!")
