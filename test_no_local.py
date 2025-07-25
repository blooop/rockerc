#!/usr/bin/env python3
import sys
import tempfile
import os
sys.path.insert(0, '/workspaces/rockerc')

try:
    from rockerc.rockerc import load_defaults_config, collect_arguments
    
    # Test in a temporary directory with no local rockerc.yaml
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing in temporary directory: {temp_dir}")
        os.chdir(temp_dir)
        
        # Test collecting arguments (which merges defaults with local config)
        merged = collect_arguments(".")
        print('Configuration with defaults only:', merged)
        print('Final args:', merged.get('args', []))
        
        # Verify nvidia is not in the final args (should be disabled by default)
        if 'nvidia' not in merged.get('args', []):
            print("✓ SUCCESS: nvidia properly disabled by default")
        else:
            print("✗ FAIL: nvidia should be disabled by default")
    
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
