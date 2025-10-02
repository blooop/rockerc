# Fix SSH Git Clone in CI

## Problem
The `setup_cache_repo()` function uses SSH URL format (`git@github.com:...`) which fails in CI environments without SSH keys configured.

## Solution
Configure GitHub Actions to properly use SSH keys via the `webfactory/ssh-agent` action. This maintains SSH as the primary method for both local and CI environments.

## Implementation
1. Add `webfactory/ssh-agent` action to `.github/workflows/ci.yml` with SSH_PRIVATE_KEY secret
2. Keep SSH URLs in `setup_cache_repo()`
3. Document SSH key setup requirements in CI
