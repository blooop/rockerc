#!/usr/bin/env python3
"""Test script for renv version functionality."""

import sys
import os

# Add the rockerc directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rockerc"))

from rockerc.renv import get_version


def test_version():
    """Test that version can be retrieved."""
    version = get_version()
    print(f"renv version: {version}")
    assert version != "unknown", "Version should not be unknown"
    assert version == "0.7.2.4", f"Expected version 0.7.2.4, but got {version}"
    print("Version test passed!")


if __name__ == "__main__":
    test_version()
