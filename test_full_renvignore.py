#!/usr/bin/env python3
import sys
import tempfile
import os
import yaml
sys.path.insert(0, '/workspaces/rockerc')

from rockerc.rockerc import collect_arguments

# Create a temporary rockerc.yaml for testing
with tempfile.TemporaryDirectory() as tmpdir:
    rockerc_config = {
        'image': 'ubuntu:22.04',
        'args': ['nvidia', 'x11', 'user', 'git', 'pixi', 'pull', 'deps']
    }
    
    rockerc_path = os.path.join(tmpdir, 'rockerc.yaml')
    with open(rockerc_path, 'w') as f:
        yaml.dump(rockerc_config, f)
    
    print('Original args:', rockerc_config['args'])
    
    # Test the filtering
    result = collect_arguments(tmpdir)
    print('Filtered args:', result.get('args', []))
