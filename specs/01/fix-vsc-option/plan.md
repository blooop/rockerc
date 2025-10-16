# Investigation and Fix Plan for --vsc Option

## Step 1: Commit History Analysis
- Review recent commits to identify changes that might affect VSCode integration
- Focus on commits related to:
  - Branch/folder naming changes
  - Container configuration
  - VSCode-specific code paths

## Step 2: Code Analysis
- Examine current renv implementation
- Compare working regular renv vs broken --vsc option
- Identify differences in execution paths

## Step 3: Testing and Debugging
- Attempt to reproduce the issue
- Add debug logging if needed
- Identify exact failure point

## Step 4: Root Cause Analysis
- Determine specific cause of container crash
- Understand how recent changes broke VSCode integration

## Step 5: Implementation
- Develop fix for identified issue
- Ensure backward compatibility
- Test fix thoroughly

## Step 6: Validation
- Run CI tests
- Verify both regular renv and --vsc option work correctly