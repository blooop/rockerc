
#!/usr/bin/env bash
set -e

echo "=== CONTAINER BREAKOUT DETECTION TEST (SERIAL) ==="
echo "Step 1: Run renv blooop/test_renv pwd (should build and run container)"
output1=$(renv blooop/test_renv pwd 2>&1)
echo "$output1"

echo "Step 2: Delete ~/renv directory"
rm -rf ~/renv
if [ -d ~/renv ]; then
    echo "ERROR: ~/renv directory still exists after rm -rf"
    exit 1
fi
echo "✓ ~/renv deleted"

echo "Step 3: Run renv blooop/test_renv pwd again (should detect breakout and rebuild)"
output2=$(renv blooop/test_renv pwd 2>&1 || true)
echo "$output2"

echo "=== END OF TEST ==="
