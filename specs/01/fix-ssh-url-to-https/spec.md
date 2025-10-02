# Fix SSH URL to HTTPS for Git Clone

## Problem
The `setup_cache_repo()` function in `renv.py:362` uses SSH URL format (`git@github.com:...`) which fails in CI environments without SSH keys configured.

## Solution
Change repository URL from SSH format to HTTPS format for public repository cloning.

## Implementation
Update `rockerc/renv.py:362` to use HTTPS URL format:
- From: `git@github.com:{owner}/{repo}.git`
- To: `https://github.com/{owner}/{repo}.git`
