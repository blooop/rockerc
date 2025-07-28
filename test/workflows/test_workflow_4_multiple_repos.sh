#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

echo "Running: renv osrf/rocker@main"
renv osrf/rocker@main
