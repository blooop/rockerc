
#!/usr/bin/env bash
set -e

echo "Step 1: Run renv blooop/test_renv pwd (should build and run container)"
renv blooop/test_renv pwd

echo "Step 2: Delete ~/renv directory"
rm -rf ~/renv
if [ -d ~/renv ]; then
    echo "ERROR: ~/renv directory still exists after rm -rf"
    exit 1
fi
echo "✓ ~/renv deleted"

echo "Step 3: Run renv blooop/test_renv pwd again (should detect breakout and rebuild)"
renv blooop/test_renv pwd
