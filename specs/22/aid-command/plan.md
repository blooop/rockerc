# Aid Command Implementation Plan

## Architecture
- Create `rockerc/aid.py` as new module following existing patterns
- Add `aid` entry point to `pyproject.toml` 
- Reuse `renv.py` infrastructure for container management
- Execute AI CLI within container environment

## Implementation Steps

### 1. Module Structure (`rockerc/aid.py`)
```python
# Main functions:
- parse_aid_args() - Handle command line parsing including agent selection
- build_ai_command() - Construct appropriate CLI command for selected agent
- run_aid() - Main entry point that coordinates renv integration
- main() - CLI entry point
```

### 2. Agent Support
- `--gemini` (default): Use gemini CLI 
- `--claude`: Use claude CLI (if available)
- `--codex`: Use codex CLI (if available)

### 3. Command Construction
- Build interactive command strings for each agent type
- Ensure agentic mode is enabled (not simple Q&A)
- Pass prompt as initial message to start conversation
- Maintain interactive session for follow-up

### 4. Integration Points
- Use `RepoSpec.parse()` for repo specification handling
- Use `manage_container()` for container lifecycle
- Pass constructed AI command to container execution
- Ensure proper working directory setup

### 5. Error Handling
- Check if selected AI CLI is available in container
- Graceful fallback if agent CLI not found
- Proper error messages for invalid repo specs
- Handle container setup failures

## Testing Strategy
- Unit tests for argument parsing
- Integration tests with mock AI CLI commands
- Test with different repo specifications
- Verify container setup and command execution