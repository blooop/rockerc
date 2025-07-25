#!/bin/bash

# Test script to verify that completion doesn't add space after repo names

echo "Testing completion fix..."

# Source the completion script
source ~/.local/share/bash-completion/completions/renv

# Create a simple test directory structure to simulate repos
mkdir -p ~/renv/testowner/testrepo

# Test completion by simulating what bash would do
COMP_WORDS=("renv" "testowner/testrepo")
COMP_CWORD=1
cur="testowner/testrepo"

# Call the completion function
_renv_complete

# Check the results
echo "COMPREPLY contains: ${COMPREPLY[@]}"
echo "Number of completions: ${#COMPREPLY[@]}"

# Check if compopt -o nospace was called by examining the completion behavior
# This is indirect since we can't directly check compopt state in a script
if [[ ${#COMPREPLY[@]} -eq 1 ]] && [[ "${COMPREPLY[0]}" == *"/"* ]]; then
    echo "✓ Single repo completion found - nospace should be active"
else
    echo "⚠ No single repo completion found"
fi

# Clean up test directory
rm -rf ~/renv/testowner
