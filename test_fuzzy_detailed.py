#!/usr/bin/env python3

# Test script for the fuzzy select functionality with actual fuzzy selection
import sys
import os

# Add the current directory to the path so we can import rockerc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rockerc.renv import get_all_repo_branch_combinations
    from iterfzf import iterfzf

    print("✓ Imports successful")

    # Test the function that gets combinations
    combinations = get_all_repo_branch_combinations()
    print(f"✓ Found {len(combinations)} repo/branch combinations")

    if combinations:
        print(
            "\nTesting fuzzy search (you can type 'bl ben ma' to search for blooop/bencher@main):"
        )
        print("Available options (first 10):")
        for combo in combinations[:10]:
            print(f"  - {combo}")

        print("\nTo test fuzzy search interactively, run:")
        print(
            "  python3 -c \"from rockerc.renv import fuzzy_select_repo_spec; result = fuzzy_select_repo_spec(); print(f'Selected: {result}')\""
        )

        # Show some examples of how fuzzy matching would work
        print("\nExample fuzzy matches for 'bl ben ma':")
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

        print(f"Found {len(matches)} potential matches:")
        for match in matches[:5]:  # Show first 5 matches
            print(f"  - {match}")

    else:
        print("No repositories found. To test, you would need to clone some repositories first.")
        print("Example: renv blooop/bencher@main")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()
