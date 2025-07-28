#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

echo "Running: renv osrf/rocker echo 'persistent message' > tmp.txt"
renv osrf/rocker echo "persistent message" > tmp.txt

echo "Running: renv osrf/rocker@new_branch touch tmp2.txt"
renv osrf/rocker@new_branch touch tmp2.txt
renv osrf/rocker echo "new_branch" > tmp.txt

echo "Running: renv osrf/rocker cat tmp.txt"
renv osrf/rocker echo "contents of tmp.txt: " && cat tmp.txt
