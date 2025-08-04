#!/usr/bin/env bash
set -e

echo "Running: renv blooop/test_wtd and confirming the working directory is test_renv to match the name of the git repo"
renv blooop/test_wtd pwd


