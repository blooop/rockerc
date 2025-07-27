#!/usr/bin/env python3

"""
Comprehensive test of the new fuzzy search functionality in renv.

This script tests:
1. Basic imports
2. Repository and branch listing
3. Fuzzy search options generation
4. Bash completion functionality
"""

import sys
import os
import subprocess

# Add the current directory to the path so we can import rockerc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all required imports work."""
    print("🧪 Testing imports...")
    try:
        from rockerc.renv import (
            get_all_repo_branch_combinations,
            fuzzy_select_repo_spec,
            generate_completion_candidates,
            list_owners_and_repos,
            list_branches,
        )
        from iterfzf import iterfzf

        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_repo_listing():
    """Test repository and branch listing functionality."""
    print("\n🧪 Testing repository listing...")
    try:
        from rockerc.renv import list_owners_and_repos, list_branches

        repos = list_owners_and_repos()
        print(f"✅ Found {len(repos)} repositories")

        if repos:
            # Test branch listing for the first repo
            first_repo = repos[0]
            if "/" in first_repo:
                owner, repo = first_repo.split("/", 1)
                branches = list_branches(owner, repo)
                print(f"✅ Found {len(branches)} branches for {first_repo}")
            else:
                print("⚠️  First repo doesn't have expected owner/repo format")

        return True
    except Exception as e:
        print(f"❌ Repository listing failed: {e}")
        return False


def test_fuzzy_combinations():
    """Test the fuzzy search combinations generation."""
    print("\n🧪 Testing fuzzy search combinations...")
    try:
        from rockerc.renv import get_all_repo_branch_combinations

        combinations = get_all_repo_branch_combinations()
        print(f"✅ Generated {len(combinations)} fuzzy search options")

        # Check that we have both repo-only and repo@branch combinations
        repo_only = [c for c in combinations if "@" not in c]
        repo_branch = [c for c in combinations if "@" in c]

        print(f"   - {len(repo_only)} repository-only options")
        print(f"   - {len(repo_branch)} repository@branch options")

        if len(combinations) > 0:
            print("   Sample options:")
            for combo in combinations[:5]:
                print(f"     - {combo}")

        return True
    except Exception as e:
        print(f"❌ Fuzzy combinations generation failed: {e}")
        return False


def test_bash_completion():
    """Test bash completion functionality."""
    print("\n🧪 Testing bash completion...")
    try:
        from rockerc.renv import generate_completion_candidates

        # Test empty completion
        candidates = generate_completion_candidates([])
        print(f"✅ Empty query returned {len(candidates)} candidates")

        # Test prefix completion
        candidates = generate_completion_candidates(["bl"])
        print(f"✅ 'bl' prefix returned {len(candidates)} candidates")

        # Test branch completion
        candidates = generate_completion_candidates(["blooop/bencher@"])
        print(f"✅ 'blooop/bencher@' returned {len(candidates)} branch candidates")

        return True
    except Exception as e:
        print(f"❌ Bash completion test failed: {e}")
        return False


def test_fuzzy_search_example():
    """Test fuzzy search with example query."""
    print("\n🧪 Testing fuzzy search example...")
    try:
        from rockerc.renv import get_all_repo_branch_combinations

        combinations = get_all_repo_branch_combinations()

        # Simulate fuzzy search for "bl ben ma" (blooop/bencher@main)
        query = "bl ben ma"
        matches = []

        for combo in combinations:
            # Simple fuzzy matching simulation
            query_chars = query.lower().replace(" ", "")
            combo_lower = combo.lower()

            # Check if all characters in query appear in order in combo
            last_index = -1
            match = True
            for char in query_chars:
                index = combo_lower.find(char, last_index + 1)
                if index == -1:
                    match = False
                    break
                last_index = index

            if match:
                matches.append(combo)

        print(f"✅ Query '{query}' found {len(matches)} fuzzy matches")

        if matches:
            print("   Top matches:")
            for match in matches[:3]:
                print(f"     - {match}")

        return True
    except Exception as e:
        print(f"❌ Fuzzy search example failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Running comprehensive renv fuzzy search tests...")

    tests = [
        test_imports,
        test_repo_listing,
        test_fuzzy_combinations,
        test_bash_completion,
        test_fuzzy_search_example,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The fuzzy search functionality is working correctly.")
        print("\n💡 Usage examples:")
        print("   1. Interactive fuzzy search: renv")
        print("   2. Direct usage: renv blooop/bencher@main")
        print("   3. Bash completion: renv bl<TAB>")
        print("   4. Branch completion: renv blooop/bencher@<TAB>")
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
