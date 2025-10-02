# Fix SSH Authentication in GitHub CI

## Problem
The `setup_cache_repo()` function uses SSH URL format (`git@github.com:...`) which fails in CI environments without SSH keys configured.

## Solution
Keep SSH URLs (preferred) and configure GitHub Actions to use SSH keys for git operations.

## Implementation
Add SSH key setup step to `.github/workflows/ci.yml` before running tests to enable SSH git cloning.
