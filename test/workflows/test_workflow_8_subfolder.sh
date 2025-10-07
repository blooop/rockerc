#!/usr/bin/env bash
set -euo pipefail

RENV_DIR="${RENV_DIR:-$HOME/renv}"
rm -rf "${RENV_DIR}"

#should enter on main repo @ branch nf3 and contain the folder "folder1"
renv blooop/test_renv@nf3 ls

#should enter on main repo @ branch nf3 in subfolder folder1 and contain the folder "folder2"
renv blooop/test_renv@nf3#folder1 ls

#should enter on main repo @ branch nf3 in subfolder folder1/folder2 and contain the file "example.txt"
renv blooop/test_renv@nf3#folder1/folder2 ls

echo "✓ Subfolder workflow validated"
