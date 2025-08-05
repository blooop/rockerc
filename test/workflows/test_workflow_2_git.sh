#!/usr/bin/env bash
set -e

echo "Running: wtd blooop/test_wtd and confirming the git status works as expected"
wtd blooop/test_wtd git status

echo "Should enter a clean workspace, with no dirty changes"