# Container Attachment Debugging Plan

## Investigation Steps

### 1. Code Review
- Examine current container attachment implementation in `rockerc/`
- Compare with git history to identify changes made during refactoring
- Focus on how shell sessions are initiated during attachment

### 2. Shell Configuration Analysis  
- Verify how .bashrc and .profile are sourced
- Check if interactive vs non-interactive shell modes affect sourcing
- Analyze PATH environment variable propagation

### 3. Docker Attachment Methods
- Review current `docker attach` vs `docker exec` usage
- Investigate shell initialization flags (`-i`, `-t`, `--login`)
- Test different attachment methods for proper environment setup

### 4. Diagnostic Testing
- Create test cases to verify executable discovery
- Test PATH variable contents in attached sessions
- Validate shell configuration sourcing

### 5. Implementation Fixes
- Ensure proper shell flags for interactive login sessions
- Add explicit sourcing of configuration files if needed
- Update attachment method to preserve full environment

### 6. Validation
- Run comprehensive test suite
- Verify CI pipeline passes
- Test manual attachment scenarios