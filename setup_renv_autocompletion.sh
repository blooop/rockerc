#!/bin/bash

# Enable autocompletion for renv
# This script demonstrates how to set up autocompletion for the enhanced renv tool

echo "Setting up autocompletion for renv..."

# Check if argcomplete is available
if command -v register-python-argcomplete >/dev/null 2>&1; then
    echo "✓ argcomplete is available"
    
    # Register autocompletion for renv
    # In a real setup, this would be added to .bashrc or .zshrc
    eval "$(register-python-argcomplete renv)"
    
    echo "✓ Autocompletion registered for renv"
    echo ""
    echo "Usage examples with autocompletion:"
    echo "  renv <TAB>                    # Shows available users"
    echo "  renv blooop/<TAB>            # Shows repos for user 'blooop'"
    echo "  renv blooop/bencher@<TAB>    # Shows branches for 'blooop/bencher'"
    echo ""
    echo "To make this permanent, add the following to your ~/.bashrc:"
    echo "  eval \"$(register-python-argcomplete renv)\""
    
else
    echo "⚠ argcomplete not found. Install with: pip install argcomplete"
    echo "Then run: activate-global-python-argcomplete"
fi

echo ""
echo "Enhanced renv features:"
echo "✓ Version display when no arguments provided"
echo "✓ Intelligent autocompletion for users, repos, and branches"
echo "✓ Filesystem-aware completion based on ~/renv directory structure"
echo "✓ Branch completion using git commands"
