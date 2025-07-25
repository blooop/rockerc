#!/usr/bin/env python3
"""
Demonstration of the new renv --install and --uninstall commands.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def demo_install_commands():
    """Demonstrate the new install/uninstall commands."""
    print("Enhanced renv Tool - Install/Uninstall Commands Demo")
    print("=" * 55)
    print()
    
    print("### New Installation Commands ###")
    print()
    
    print("✅ renv --install")
    print("   Automatically installs and configures autocompletion:")
    print("   1. Detects your virtual environment type (uv or pip)")
    print("   2. Installs argcomplete package")
    print("   3. Adds autocompletion to your shell configuration")
    print("   4. Activates global argcomplete (if possible)")
    print()
    
    print("✅ renv --uninstall")
    print("   Removes autocompletion setup:")
    print("   1. Removes configuration from shell files")
    print("   2. Optionally uninstalls argcomplete package")
    print()
    
    print("### Virtual Environment Detection ###")
    print("The install command automatically detects:")
    print("• uv virtual environments (UV_VENV)")
    print("• pip virtual environments (VIRTUAL_ENV)")
    print("• Shell type (bash, zsh, fish)")
    print("• Appropriate configuration files (.bashrc, .zshrc, etc.)")
    print()
    
    print("### Setup Workflow ###")
    print("1. Activate your virtual environment:")
    print("   source venv/bin/activate  # pip")
    print("   # or")
    print("   uv venv && source .venv/bin/activate  # uv")
    print()
    print("2. Install autocompletion:")
    print("   renv --install")
    print()
    print("3. Restart your shell or source the config:")
    print("   source ~/.bashrc  # or ~/.zshrc")
    print()
    print("4. Test autocompletion:")
    print("   renv <TAB>")
    print()
    
    print("### Features ###")
    print("✓ Supports both uv and pip virtual environments")
    print("✓ Detects shell type automatically")
    print("✓ Safe installation (checks for existing configuration)")
    print("✓ Easy removal with --uninstall")
    print("✓ Works with global argcomplete activation")
    print()
    
    print("### Usage Examples ###")
    print("# Quick setup in a new environment")
    print("uv venv && source .venv/bin/activate")
    print("renv --install")
    print()
    print("# Clean removal")
    print("renv --uninstall")
    print()
    
    print("### Error Handling ###")
    print("The commands include robust error handling:")
    print("• Detects missing virtual environment")
    print("• Handles installation failures gracefully")
    print("• Provides clear error messages")
    print("• Safe file operations")
    print()
    
    print("🎉 The renv tool now provides a complete autocompletion setup solution!")

if __name__ == "__main__":
    demo_install_commands()
