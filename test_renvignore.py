#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspaces/rockerc')

try:
    from rockerc.rockerc import read_renvignore
    print('Successfully imported read_renvignore')
    ignored = read_renvignore()
    print('Ignored extensions:', ignored)
    print('Number of extensions found:', len(ignored))
    for ext in ignored:
        print(f'  - {ext}')
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
