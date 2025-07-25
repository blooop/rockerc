#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspaces/rockerc')

try:
    from rockerc.rockerc import collect_arguments, yaml_dict_to_args
    
    print("Testing complete rockerc functionality...")
    
    # Test collecting arguments with current config
    merged = collect_arguments('.')
    print('Merged configuration:', merged)
    
    # Test converting to rocker command args
    cmd_args = yaml_dict_to_args(merged.copy())  # copy so we don't modify original
    print(f'Generated rocker command args: "rocker {cmd_args}"')
    
    # Verify nvidia is not in the command
    if '--nvidia' not in cmd_args:
        print("✓ SUCCESS: nvidia properly excluded from rocker command")
    else:
        print("✗ FAIL: nvidia should not be in rocker command")
        
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
