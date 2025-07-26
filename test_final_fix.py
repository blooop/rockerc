#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rockerc.renv import get_all_repo_branch_combinations

combos = get_all_repo_branch_combinations()
print("Checking for urdf-viz in combinations:")
for combo in combos:
    if 'urdf' in combo:
        print(f"  Found: {combo}")

print("\nChecking for + prefix in combinations:")
for combo in combos:
    if '+' in combo:
        print(f"  ISSUE: {combo}")

if not any('+' in combo for combo in combos):
    print("  ✅ No + prefixes found!")
