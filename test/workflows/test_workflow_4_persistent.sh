#!/usr/bin/env bash
set -e
cd /tmp

renv --prune blooop/test_renv

echo "Running: wtd blooop/test_wtd touch persistent.txt to confirm that persistent files work as expected"
wtd blooop/test_wtd touch persistent.txt

echo "Running: wtd blooop/test_wtd ls to confirm that persistent files are present"
wtd blooop/test_wtd ls