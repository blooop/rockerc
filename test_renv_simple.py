#!/usr/bin/env python3
"""
Simple test to verify renv enhancements work correctly.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_version_reading():
    """Test that version can be read from pyproject.toml."""
    from rockerc.renv import get_version
    
    version = get_version()
    print(f"✓ Version reading works: {version}")
    
    # Verify it's not the fallback
    assert version != "unknown", "Version should not be unknown"
    
    # Verify it matches expected format (x.y.z.w)
    parts = version.split(".")
    assert len(parts) >= 3, f"Version should have at least 3 parts: {version}"
    
    return version

def test_autocompletion_functions():
    """Test that autocompletion functions can be imported and called."""
    from rockerc.renv import get_existing_repos, repo_completer, get_branches_for_repo
    
    # Test get_existing_repos (should not crash even if no repos exist)
    repos = get_existing_repos()
    print(f"✓ get_existing_repos works: found {len(repos)} repos")
    
    # Test repo_completer (should not crash with various inputs)
    completions = repo_completer("test")
    print(f"✓ repo_completer works: returned {len(completions)} completions")
    
    # Test get_branches_for_repo (should not crash even with non-existent repo)
    branches = get_branches_for_repo("nonexistent", "repo")
    print(f"✓ get_branches_for_repo works: returned {len(branches)} branches")

def test_main_function_import():
    """Test that main function can be imported."""
    from rockerc.renv import main
    print("✓ main function can be imported")

def test_argcomplete_availability():
    """Test argcomplete availability detection."""
    from rockerc.renv import ARGCOMPLETE_AVAILABLE
    print(f"✓ Argcomplete availability detected: {ARGCOMPLETE_AVAILABLE}")

def main():
    """Run all tests."""
    print("Testing renv enhancements...")
    print("=" * 40)
    
    try:
        version = test_version_reading()
        test_autocompletion_functions()
        test_main_function_import()
        test_argcomplete_availability()
        
        print("=" * 40)
        print("✅ All tests passed!")
        print(f"✅ renv version {version} is ready with autocompletion support")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
