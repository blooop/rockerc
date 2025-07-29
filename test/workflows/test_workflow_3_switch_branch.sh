
#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv
# Remove any existing rocker-main container to ensure a clean test
docker rm -f rocker-main || true

# echo "Running: renv osrf/rocker echo 'persistent message' > tmp.txt"
# renv osrf/rocker ls

echo "Running: renv osrf/rocker echo 'persistent message' > tmp.txt"
renv osrf/rocker touch persistent.txt

echo "Running: renv osrf/rocker echo 'persistent message' > tmp.txt"
renv osrf/rocker ls

# echo "Running: renv osrf/rocker cat tmp.txt"
# renv osrf/rocker echo "contents of tmp.txt: " && cat tmp.txt
