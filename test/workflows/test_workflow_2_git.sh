#!/usr/bin/env bash
set -e

echo "Running: renv blooop/test_renv and confirming the git status works as expected"
renv blooop/test_renv git status
