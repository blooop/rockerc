
#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

echo "Running: renv blooop/test_renv touch persistent.txt to confirm that persistent files work as expected"
renv blooop/test_renv touch persistent.txt

echo "Running: renv blooop/test_renv ls to confirm that persistent files are present"
renv blooop/test_renv ls