#!/usr/bin/env bash
set -e
cd /tmp

# #rockerc is set up in this repo

echo "Running: renv osrf/rocker \"bash -c 'git status; pwd; ls -l'\""
renv osrf/rocker "bash -c 'git status; pwd; ls -l'"



