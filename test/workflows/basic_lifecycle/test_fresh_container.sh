#!/usr/bin/env bash
set -e
rm -rf ~/renv
cd /tmp

renv blooop/test_renv git status
echo "✓ Fresh container test completed"
