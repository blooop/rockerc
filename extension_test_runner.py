#!/usr/bin/env python3
"""
Generic extension test runner.
This script provides a generic way to test any extension that has a test.sh file.
"""
import subprocess
import sys
from pathlib import Path


def cleanup_containers():
    """Clean up test containers and environment."""
    print("Cleaning up test environment...")
    try:
        # Use wtd prune to clean up properly
        subprocess.run(["wtd", "--prune"], capture_output=True, timeout=30)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        # Fallback cleanup in case prune fails
        subprocess.run(
            ["docker", "container", "prune", "-f", "--filter", "label=wtd"],
            capture_output=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        # Remove cache directory
        cache_dir = Path.home() / ".wtd"
        if cache_dir.exists():
            import shutil

            shutil.rmtree(cache_dir, ignore_errors=True)
    except Exception:
        pass


def test_extension_generic(extension_name: str, test_repo: str = "blooop/test_wtd@main") -> bool:
    """
    Generic extension test runner that handles all the boilerplate.

    Args:
        extension_name: Name of the extension to test
        test_repo: Test repository to use (default: blooop/test_wtd@main)

    Returns:
        True if all tests pass, False otherwise
    """
    print(f"=== TESTING EXTENSION: {extension_name.upper()} ===")

    try:
        # Step 1: Test that extension appears in extension list
        print("=== STEP 1: TEST EXTENSION IN LIST ===")
        result = subprocess.run(["wtd", "--ext-list"], capture_output=True, text=True, timeout=30)

        if extension_name not in result.stdout:
            print(f"✗ {extension_name} extension not found in extension list")
            print(f"Extension list output: {result.stdout}")
            return False
        print(f"✓ {extension_name} extension appears in extension list")

        # Step 2: Test loading extension explicitly
        print("=== STEP 2: TEST EXTENSION LOADING ===")
        print(f"Testing {extension_name} extension loading with test repository...")

        load_result = subprocess.run(
            [
                "wtd",
                "--rebuild",
                "-e",
                extension_name,
                test_repo,
                "echo",
                f"{extension_name} extension test",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = load_result.stdout + load_result.stderr

        # Check if extension was loaded
        if f"✓ Loaded extension: {extension_name}" not in output:
            print(f"✗ {extension_name} extension failed to load")
            print("Load output:")
            print(output)
            return False
        print(f"✓ {extension_name} extension loaded successfully")

        # Check if the command executed properly
        if f"{extension_name} extension test" not in output:
            print(f"✗ Command failed to execute with {extension_name} extension")
            print("Load output:")
            print(output)
            return False
        print(f"✓ Command executed successfully with {extension_name} extension")

        # Step 3: Run the extension's specific test.sh
        print("=== STEP 3: RUN EXTENSION-SPECIFIC TEST ===")
        test_result = subprocess.run(
            [
                "wtd",
                "-e",
                extension_name,
                test_repo,
                "bash",
                "-c",
                "cd /workspace && test -f test.sh && ./test.sh || echo 'No test.sh found'",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        test_output = test_result.stdout + test_result.stderr

        if "No test.sh found" in test_output:
            print(f"⚠ {extension_name} extension has no test.sh file")
        elif test_result.returncode != 0:
            print(f"✗ {extension_name} extension-specific test failed")
            print("Test output:")
            print(test_output)
            return False
        else:
            print(f"✓ {extension_name} extension-specific test passed")

        # Step 4: Test with other common extensions
        print("=== STEP 4: TEST WITH OTHER EXTENSIONS ===")
        multi_result = subprocess.run(
            ["wtd", "-e", "git", "-e", extension_name, test_repo, "echo", "multi-extension test"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        multi_output = multi_result.stdout + multi_result.stderr

        if (
            "✓ Loaded extension: git" not in multi_output
            or f"✓ Loaded extension: {extension_name}" not in multi_output
        ):
            print(f"✗ {extension_name} extension failed to work with other extensions")
            print("Multi-extension output:")
            print(multi_output)
            return False
        print(f"✓ {extension_name} extension works with other extensions")

        if "multi-extension test" not in multi_output:
            print("✗ Multi-extension command failed")
            print("Multi-extension output:")
            print(multi_output)
            return False
        print("✓ Multi-extension command executed successfully")

        print(f"=== {extension_name.upper()} EXTENSION TEST PASSED ===")
        return True

    except subprocess.TimeoutExpired:
        print(f"✗ {extension_name} extension test timed out")
        return False
    except Exception as e:
        print(f"✗ {extension_name} extension test failed with exception: {e}")
        return False


def main():
    """Main entry point for the extension test runner."""
    if len(sys.argv) != 2:
        print("Usage: python test_extension_runner.py <extension_name>")
        sys.exit(1)

    extension_name = sys.argv[1]

    # Set up cleanup
    cleanup_containers()

    try:
        success = test_extension_generic(extension_name)
        if success:
            print(f"\n🎉 All tests passed for {extension_name} extension!")
            sys.exit(0)
        else:
            print(f"\n❌ Tests failed for {extension_name} extension!")
            sys.exit(1)
    finally:
        cleanup_containers()


if __name__ == "__main__":
    main()
