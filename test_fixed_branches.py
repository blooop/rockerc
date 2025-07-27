#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rockerc.renv import list_branches

# Test the updated list_branches function
branches = list_branches("blooop", "manifest_rocker")
print(f"Updated function found {len(branches)} branches:")
for branch in branches:
    print(f"  '{branch}'")

# Check for the + prefix specifically
plus_branches = [b for b in branches if b.startswith("+")]
if plus_branches:
    print(f"\n❌ Still found {len(plus_branches)} branches with + prefix:")
    for branch in plus_branches:
        print(f"  '{branch}'")
else:
    print("\n✅ No branches with + prefix found!")
