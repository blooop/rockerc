#!/usr/bin/env bash
set -euo pipefail

RENV_DIR="${RENV_DIR:-$HOME/renv}"
rm -rf "${RENV_DIR}"


#test with no branch on main first
renv blooop/test_renv#folder1/folder2 -- bash -c "echo expected output: example.txt; ls"

#test with specific branches
#should enter on main repo @ branch test_branch1 and contain the folder "folder1" and README.md
renv blooop/test_renv@test_branch1 -- bash -c "echo expected output: README.md folder1; ls"

#should enter on main repo @ branch test_branch1 in subfolder folder1 and contain the folder "folder2"
renv blooop/test_renv@test_branch1#folder1 -- bash -c "echo expected output: folder2; ls"

#should enter on main repo @ branch test_branch1 in subfolder folder1/folder2 and contain the file "example.txt"
renv blooop/test_renv@test_branch1#folder1/folder2 -- bash -c "echo expected output: example.txt; ls"

#should enter on main repo @ branch test_branch1 in subfolder folder1/folder2 and contain the file "example.txt"
renv blooop/test_renv@test_branch2#folder1/folder2 -- bash -c "echo expected output: example.txt; ls"

#should enter on main repo @ branch test_branch2 in subfolder folder1/folder2 and contain the file "example.txt"

echo "✓ Subfolder workflow validated"
