#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

#rockerc is set up in this repo
echo "Running: renv osrf/rocker@echo_test and confirming the directory is manifest_rocker"
renv osrf/rocker@echo_test echo "I am in folder:" && pwd



