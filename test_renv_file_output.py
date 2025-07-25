#!/usr/bin/env python3
"""
File-based test for renv functionality to bypass terminal output issues.
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def write_test_results(filename, results):
    """Write test results to a file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("renv Test Results\n")
        f.write("=" * 20 + "\n\n")
        
        for test_name, result, details in results:
            status = "PASS" if result else "FAIL"
            f.write(f"{test_name}: {status}\n")
            if details:
                f.write(f"  Details: {details}\n")
            f.write("\n")

def run_tests():
    """Run all tests and return results."""
    results = []
    
    # Test 1: Basic import
    try:
        from rockerc.renv import get_version
        results.append(("Import get_version", True, "Successfully imported"))
    except Exception as e:
        results.append(("Import get_version", False, str(e)))
        return results  # Can't continue without basic import
    
    # Test 2: Version reading
    try:
        version = get_version()
        if version != "unknown":
            results.append(("Version reading", True, f"Version: {version}"))
        else:
            results.append(("Version reading", False, "Version returned 'unknown'"))
    except Exception as e:
        results.append(("Version reading", False, str(e)))
    
    # Test 3: Import autocompletion functions
    try:
        from rockerc.renv import get_existing_repos, repo_completer, get_branches_for_repo
        results.append(("Import autocompletion functions", True, "All functions imported"))
    except Exception as e:
        results.append(("Import autocompletion functions", False, str(e)))
        return results  # Can't test autocompletion without imports
    
    # Test 4: Test get_existing_repos
    try:
        repos = get_existing_repos()
        results.append(("Get existing repos", True, f"Found {len(repos)} repos"))
    except Exception as e:
        results.append(("Get existing repos", False, str(e)))
    
    # Test 5: Test repo_completer
    try:
        completions = repo_completer("")
        results.append(("Repo completer", True, f"Got {len(completions)} completions"))
    except Exception as e:
        results.append(("Repo completer", False, str(e)))
    
    # Test 6: Test get_branches_for_repo
    try:
        branches = get_branches_for_repo("nonexistent", "repo")
        results.append(("Get branches", True, f"Got {len(branches)} branches (expected 0 for nonexistent repo)"))
    except Exception as e:
        results.append(("Get branches", False, str(e)))
    
    # Test 7: Test argcomplete availability
    try:
        from rockerc.renv import ARGCOMPLETE_AVAILABLE
        results.append(("Argcomplete availability", True, f"Available: {ARGCOMPLETE_AVAILABLE}"))
    except Exception as e:
        results.append(("Argcomplete availability", False, str(e)))
    
    # Test 8: Test global package manager detection
    try:
        from rockerc.renv import detect_global_package_manager
        manager_info = detect_global_package_manager()
        results.append(("Package manager detection", True, f"Detected: {manager_info.get('type', 'None')}"))
    except Exception as e:
        results.append(("Package manager detection", False, str(e)))
    
    # Test 9: Test main function import
    try:
        from rockerc.renv import main
        results.append(("Main function import", True, "Main function imported successfully"))
    except Exception as e:
        results.append(("Main function import", False, str(e)))
    
    return results

def main():
    """Run tests and write results."""
    try:
        results = run_tests()
        
        # Write results to file
        write_test_results("renv_test_results.txt", results)
        
        # Print summary to stdout
        passed = sum(1 for _, result, _ in results if result)
        total = len(results)
        
        print(f"Tests completed: {passed}/{total} passed")
        print("Detailed results written to: renv_test_results.txt")
        
        if passed == total:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed. Check renv_test_results.txt for details.")
            
        return passed == total
        
    except Exception as e:
        with open("renv_test_error.txt", 'w') as f:
            f.write(f"Test runner error: {e}\n")
            import traceback
            traceback.print_exc(file=f)
        print(f"Test runner failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
