#!/usr/bin/env bash
set -euo pipefail

# Clean up containers from previous tests (but keep the renv directory)
docker ps -a --format "{{.Names}}" | grep "test_renv" | xargs -r docker rm -f 2>/dev/null || true

#test with no branch on main first
renv blooop/test_renv#folder1/folder2 -- bash -c "echo expected output: example.txt; ls"

#test with specific branches
#should enter on main repo @ branch test_branch1 and contain the folder "folder1" and README.md
renv blooop/test_renv@test_branch1 -- bash -c "echo expected output: README.md folder1; ls"

#should enter on main repo @ branch test_branch1 in subfolder folder1 and contain the folder "folder2"
renv blooop/test_renv@test_branch1#folder1 -- bash -c "echo expected output: folder2; ls"

#should enter on main repo @ branch test_branch1 in subfolder folder1/folder2 and contain the file "example.txt"
renv blooop/test_renv@test_branch1#folder1/folder2 -- bash -c "echo expected output: example.txt; ls"

#should enter on main repo @ branch test_branch2 in subfolder folder1/folder2 and contain the file "example.txt"
renv blooop/test_renv@test_branch2#folder1/folder2 -- bash -c "echo expected output: example.txt; ls"

# Test for naming disambiguation: branch names vs subfolder names should not conflict
# This tests the scenario where we have:
#   1. A subfolder named "folder1" on the main branch
#   2. A branch named "folder1" with no subfolder
# These should create different container names and not conflict
echo "Testing naming disambiguation between branches and subfolders..."
renv blooop/test_renv#folder1 -- bash -c "echo expected output: folder2; ls"
renv blooop/test_renv@folder1 -- bash -c "echo Checking folder1 branch exists; pwd"

echo "✓ Subfolder workflow validated"
