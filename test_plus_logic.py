#!/usr/bin/env python3

# Simple test to verify the + prefix handling
test_line = "+ urdf-viz"
print(f"Original: {repr(test_line)}")

line = test_line.strip()
print(f"After strip(): {repr(line)}")

if line.startswith("+"):
    line = line[1:].strip()
    print(f"After removing + prefix: {repr(line)}")

print(f"Final result: {repr(line)}")
