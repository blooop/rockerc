#!/usr/bin/env python3
import sys

sys.path.insert(0, "/workspaces/rockerc")

try:
    from rockerc.rockerc import load_defaults_config, collect_arguments

    print("Testing disable_args functionality...")

    # Test loading defaults
    defaults = load_defaults_config()
    print(f"Defaults: {defaults}")
    print(f'Default args: {defaults.get("args", [])}')
    print(f'Default disable_args: {defaults.get("disable_args", [])}')

    # Test collecting arguments (which merges defaults with local config)
    merged = collect_arguments()
    print(f'Final merged args: {merged.get("args", [])}')

    # Check if nvidia is properly disabled
    if "nvidia" not in merged.get("args", []):
        print("✓ SUCCESS: nvidia is correctly disabled by default")
    else:
        print("✗ FAILURE: nvidia should be disabled but is present in args")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
