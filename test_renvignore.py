#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspaces/rockerc')

try:
    from rockerc.rockerc import load_defaults_config, collect_arguments
    print('Successfully imported new config functions')
    
    # Test loading defaults
    defaults = load_defaults_config()
    print('Default configuration:', defaults)
    print('Default args:', defaults.get('args', []))
    
    # Test collecting arguments (which merges defaults with local config)
    merged = collect_arguments()
    print('Merged configuration:', merged)
    print('Final args:', merged.get('args', []))
    
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
