#!/usr/bin/env python3
import sys
import tempfile
sys.path.insert(0, '/workspaces/rockerc')

try:
    from rockerc.rockerc import load_defaults_config, collect_arguments
    print('Testing disable_args functionality WITHOUT local rockerc.yaml...')
    
    # Create a temporary directory without rockerc.yaml
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f'Testing in temporary directory: {temp_dir}')
        
        # Test loading defaults
        defaults = load_defaults_config(temp_dir)
        print(f'Defaults: {defaults}')
        print(f'Default args: {defaults.get("args", [])}')
        print(f'Default disable_args: {defaults.get("disable_args", [])}')
        
        # Test collecting arguments (which merges defaults with local config)
        merged = collect_arguments(temp_dir)
        print(f'Final merged args: {merged.get("args", [])}')
        
        # Check if nvidia is properly disabled
        if 'nvidia' not in merged.get('args', []):
            print('✓ SUCCESS: nvidia is correctly disabled by default when no local override')
        else:
            print('✗ FAILURE: nvidia should be disabled but is present in args')
            
    print('\nNow testing WITH local rockerc.yaml (should enable nvidia):')
    # Test with current directory (has rockerc.yaml)
    merged_with_local = collect_arguments('.')
    print(f'Final merged args with local config: {merged_with_local.get("args", [])}')
    if 'nvidia' in merged_with_local.get('args', []):
        print('✓ SUCCESS: nvidia is correctly enabled by local rockerc.yaml override')
    else:
        print('✗ FAILURE: nvidia should be enabled by local rockerc.yaml')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
