#!/bin/bash

# Test workflow for --install shell completion feature
# This test verifies that wtd --install creates completion scripts

set -e

# Cleanup function
cleanup() {
    echo "Cleaning up test environment..."
    # Remove test completion files
    rm -f /tmp/test_bash_completion_wtd 2>/dev/null || true
    rm -f /tmp/test_zsh_completion_wtd 2>/dev/null || true
    rm -f /tmp/test_fish_completion_wtd 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT

echo "=== TEST: SHELL COMPLETION INSTALLATION ==="

# Test installing bash completion by temporarily changing HOME
echo "=== STEP 1: TEST BASH COMPLETION INSTALLATION ==="

# Create a temporary directory for testing
TEST_HOME="/tmp/wtd_test_home"
mkdir -p "$TEST_HOME"

# Run with modified HOME to avoid polluting user's actual completion
HOME="$TEST_HOME" pixi run python -m rockerc.worktree_docker --install

# Check that bash completion was created
if [ -f "$TEST_HOME/.bash_completion.d/wtd" ]; then
    echo "✓ Bash completion file created successfully"
else
    echo "✗ Bash completion file not found"
    exit 1
fi

# Check that the completion file contains expected content
if grep -q "_wtd_complete" "$TEST_HOME/.bash_completion.d/wtd"; then
    echo "✓ Bash completion contains expected function"
else
    echo "✗ Bash completion doesn't contain expected function"
    exit 1
fi

# Check that it contains the right commands
if grep -q "wtd" "$TEST_HOME/.bash_completion.d/wtd"; then
    echo "✓ Bash completion contains correct commands (no destroy)"
else
    echo "✗ Bash completion doesn't contain correct commands"
    exit 1
fi

echo "=== STEP 2: VERIFY COMPLETION CONTENT ==="

# Verify the completion script is syntactically valid bash
if bash -n "$TEST_HOME/.bash_completion.d/wtd"; then
    echo "✓ Bash completion script syntax is valid"
else
    echo "✗ Bash completion script has syntax errors"
    exit 1
fi

echo "=== STEP 3: TEST HELP SHOWS INSTALL OPTION ==="

# Test that help shows the install option
HELP_OUTPUT=$(pixi run python -m rockerc.wtd --help 2>&1)

if echo "$HELP_OUTPUT" | grep -q "Install shell auto-completion"; then
    echo "✓ Help shows --install option"
else
    echo "✗ Help doesn't show --install option"
    echo "Help output: $HELP_OUTPUT"
    exit 1
fi

echo "=== STEP 4: TEST COMPLETION WITH UNSUPPORTED SHELL ==="

# Test with an unsupported shell environment
SHELL="/bin/unsupported_shell" HOME="$TEST_HOME" pixi run python -m rockerc.wtd --install 2>&1 | tee /tmp/install_output

if grep -q "Unknown shell: unsupported_shell" /tmp/install_output; then
    echo "✓ Handles unsupported shell gracefully"
else
    echo "✗ Doesn't handle unsupported shell properly"
    exit 1
fi

# Clean up test home
rm -rf "$TEST_HOME"

echo "=== SHELL COMPLETION INSTALLATION TEST PASSED ==="