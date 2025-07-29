
#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv
# Remove any existing rocker-main container to ensure a clean test
docker rm -f rocker-main || true

# echo "Running: renv blooop/test_renv echo 'persistent message' > tmp.txt"
# renv blooop/test_renv ls

echo "Running: renv blooop/test_renv echo 'persistent message' > tmp.txt"
renv blooop/test_renv touch persistent.txt

echo "Running: renv blooop/test_renv echo 'persistent message' > tmp.txt"
renv blooop/test_renv ls

# echo "Running: renv blooop/test_renv cat tmp.txt"
# renv blooop/test_renv echo "contents of tmp.txt: " && cat tmp.txt
