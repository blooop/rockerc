#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

echo "Running: renv osrf/rocker git status"
renv osrf/rocker git status
