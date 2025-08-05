#!/usr/bin/env python3
"""
Test all available extensions using the generic extension test runner.
This ensures that all extensions are properly tested and working correctly.
"""
import sys
import pytest
from worktree_docker.extension_test_runner import run_extension_test_generic, cleanup_containers


@pytest.mark.parametrize("extension", ["base", "git", "user", "pixi", "uv"])
def test_extension_integration(extension):
    """Test extension integration using the generic test runner."""
    try:
        cleanup_containers()
        test_success = run_extension_test_generic(extension)
        assert test_success, f"{extension} extension test failed"
    finally:
        cleanup_containers()


if __name__ == "__main__":
    # Run all extension tests manually if executed as a script
    all_passed = True
    for ext in ["base", "git", "user", "pixi", "uv"]:
        print(f"\nRunning test for extension: {ext}")
        cleanup_containers()
        result = run_extension_test_generic(ext)
        cleanup_containers()
        if not result:
            all_passed = False
    sys.exit(0 if all_passed else 1)
