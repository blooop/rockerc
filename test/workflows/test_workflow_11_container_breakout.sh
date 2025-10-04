
#!/usr/bin/env bash
set -e

RENV_DIR="${RENV_DIR:-$HOME/renv}"

echo "Step 1: Run renv blooop/test_renv pwd (should build and run container)"
renv blooop/test_renv pwd

echo "Step 2: Delete ${RENV_DIR} directory"
rm -rf "${RENV_DIR}"
if [ -d "${RENV_DIR}" ]; then
    echo "ERROR: ${RENV_DIR} directory still exists after rm -rf"
    exit 1
fi
echo "✓ ${RENV_DIR} deleted"

echo "Step 3: Run renv blooop/test_renv pwd again (should detect breakout and rebuild)"
renv blooop/test_renv pwd
