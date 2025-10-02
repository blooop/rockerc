# SSH Key Setup Instructions for GitHub Actions

The CI is now configured to use SSH for git cloning. To enable this, you need to add an SSH private key to your GitHub repository secrets.

## Steps:

### 1. Generate or use an existing SSH key

For a dedicated CI key (recommended):
```bash
ssh-keygen -t ed25519 -C "github-actions-rockerc" -f ~/.ssh/rockerc_deploy_key -N ""
```

Or use an existing SSH key that has access to the repositories you need to clone.

### 2. Add the public key as a Deploy Key

For the `blooop/test_renv` repository (and any other repos that need to be cloned):

1. Go to https://github.com/blooop/test_renv/settings/keys
2. Click "Add deploy key"
3. Title: `rockerc-ci` (or any descriptive name)
4. Key: Paste the contents of `~/.ssh/rockerc_deploy_key.pub`
5. **Important**: You do NOT need to check "Allow write access" unless the CI needs to push

### 3. Add the private key to this repository's secrets

For the `blooop/rockerc` repository:

1. Go to https://github.com/blooop/rockerc/settings/secrets/actions
2. Click "New repository secret"
3. Name: `SSH_PRIVATE_KEY`
4. Value: Paste the **entire contents** of `~/.ssh/rockerc_deploy_key` (the private key, NOT the .pub file)
5. Click "Add secret"

### 4. Verify

Once the secret is added, push a commit to trigger the CI workflow and verify it can clone the test repository successfully.

## Alternative: Use Personal SSH Key

If you want to use your personal SSH key instead of a deploy key:

1. Use your existing `~/.ssh/id_ed25519` or `~/.ssh/id_rsa`
2. Add the private key contents to the `SSH_PRIVATE_KEY` secret (step 3 above)
3. Your public key should already be in your GitHub account settings

**Note**: This gives the CI access to all repositories your personal key has access to, so the deploy key approach is more secure for production use.
