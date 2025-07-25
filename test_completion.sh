#!/bin/bash
# Test script for the updated completion functionality

echo "Testing completion script..."

# Test 1: Check if script can be sourced without errors
if source ./renv_completion.sh 2>/dev/null; then
    echo "✓ Completion script loaded successfully"
else
    echo "✗ Failed to load completion script"
    exit 1
fi

# Test 2: Check if function is defined
if declare -f _renv_complete >/dev/null; then
    echo "✓ Completion function _renv_complete is defined"
else
    echo "✗ Completion function _renv_complete is not defined"
    exit 1
fi

# Test 3: Check if completion is registered for renv
if complete -p renv >/dev/null 2>&1; then
    echo "✓ Completion is registered for renv command"
    complete -p renv
else
    echo "✗ Completion is not registered for renv command"
    exit 1
fi

echo "All tests passed! Simple bash completion is ready to use."
