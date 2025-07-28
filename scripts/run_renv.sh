#!/bin/bash
# Remove the renv directory and run renv with the specified argument
set -oux pipefail
    # Remove any existing renv directory in /tmp
    cd /tmp || exit 1
    rm -rf renv
    # Copy the project to /tmp/rockerc_test and cd into it
    cp -r "$(dirname "$0")/.." /tmp/rockerc_test
    cd /tmp/rockerc_test || exit 1
    # Run renv with the provided argument
    renv osrf/rocker
