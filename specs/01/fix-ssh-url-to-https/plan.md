# Implementation Plan

## Steps
1. Update `rockerc/renv.py:362` to change the repo_url from SSH format to HTTPS format
2. Update test expectations in `test/test_renv.py:181` that assert the SSH URL format
3. Run `pixi run ci` to verify all tests pass
4. Fix any additional issues that arise

## Details
- The issue occurs in `setup_cache_repo()` function when cloning the cache repository
- CI environments (GitHub Actions) don't have SSH keys configured by default
- HTTPS URLs work without authentication for public repositories
- Need to check if any tests explicitly verify the SSH URL format and update them
