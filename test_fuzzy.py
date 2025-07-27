#!/usr/bin/env python3

# Test script for the fuzzy select functionality
try:
    from rockerc.renv import fuzzy_select_repo_spec, get_all_repo_branch_combinations

    print("✓ Import successful")

    # Test the function that gets combinations
    combinations = get_all_repo_branch_combinations()
    print(f"✓ Found {len(combinations)} repo/branch combinations")

    if combinations:
        print("Examples:")
        for combo in combinations[:3]:  # Show first 3
            print(f"  - {combo}")
    else:
        print("No repositories found (this is expected if no repos are cloned yet)")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()
