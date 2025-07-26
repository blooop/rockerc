#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rockerc.renv import parse_repo_spec

# Test cases
test_cases = [
    "blooop/test",
    "blooop/test@main", 
    "blooop/test@feature",
    "blooop/test#scripts",
    "blooop/test@main#scripts",
    "blooop/test@feature#docs/api"
]

print("Testing parse_repo_spec with new subfolder support:")
for test_case in test_cases:
    try:
        result = parse_repo_spec(test_case)
        print(f"  '{test_case}' -> {result}")
    except Exception as e:
        print(f"  '{test_case}' -> ERROR: {e}")
