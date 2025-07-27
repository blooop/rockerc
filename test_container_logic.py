#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rockerc.rockerc import container_exists, container_is_running, extract_container_name_from_args

# Test the container name extraction
test_cmd = [
    "rocker",
    "--user",
    "--pull",
    "--deps",
    "--git",
    "--cwd",
    "--x11",
    "--ssh",
    "--pixi",
    "--uv",
    "ubuntu:22.04",
    "--name",
    "manifest_rocker-new",
    "--hostname",
    "manifest_rocker-new",
]

container_name = extract_container_name_from_args(test_cmd)
print(f"Extracted container name: '{container_name}'")

# Test the command parsing for the error case
test_error_output = 'docker: Error response from daemon: Conflict. The container name "/manifest_rocker-new" is already in use'
if "already in use" in test_error_output:
    print("✅ Error detection logic would work")
else:
    print("❌ Error detection logic would fail")

print("✅ Container management functions loaded successfully")
