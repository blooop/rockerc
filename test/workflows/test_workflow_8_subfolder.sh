#!/usr/bin/env bash
set -euo pipefail

RENV_DIR="${RENV_DIR:-$HOME/renv}"
rm -rf "${RENV_DIR}"

output=""
set +e
output=$(renv blooop/test_renv@nf3#foldera/folderb 2>&1)
status=$?
set -e

echo "${output}"

if [[ ${status} -eq 0 ]]; then
    echo "Expected renv to fail when sparse subfolder is missing." >&2
    exit 1
fi

if ! grep -q "Subfolder 'foldera/folderb' not found" <<<"${output}"; then
    echo "Missing expected sparse checkout error message." >&2
    exit 1
fi

echo "✓ Subfolder workflow validated"
