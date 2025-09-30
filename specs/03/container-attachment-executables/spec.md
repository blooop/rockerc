# Container Attachment Executable Discovery Issue

## Problem
After launching a container in detached mode, rockerc attaches to the container but executables are not being found. This functionality worked before recent refactoring of the container launch and attachment process.

## Root Cause Analysis Needed
- Check if shell configuration files (.bashrc, .profile) are being properly sourced during attachment
- Verify PATH environment variables are correctly set in the attached shell session  
- Compare current attachment implementation with previous working version

## Expected Behavior
- Container launches in detached mode successfully
- rockerc attaches to the running container
- All executables available in the container are discoverable in the attached session
- Shell environment (PATH, aliases, functions) is fully initialized

## Acceptance Criteria
- [ ] Shell configuration files (.bashrc, .profile) are sourced during attachment
- [ ] PATH environment variable includes all necessary directories
- [ ] Executables are discoverable via which/whereis commands
- [ ] Interactive shell features work as expected
- [ ] All existing tests pass