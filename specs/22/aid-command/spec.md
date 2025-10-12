# Aid Command Specification

## Overview
Add `aid` (AI Develop) command for streamlined AI-driven development within containerized environments.

## Requirements

### Command Syntax
```bash
aid [--gemini|--claude|--codex] repo_owner/repo_name <prompt in plain text>
```

### Behavior
- Accepts repo specification in same format as renv (`owner/repo[@branch][#subfolder]`)
- Reuses renv machinery for containerized environment setup
- Launches AI CLI interactively with prompt pre-sent
- Agent operates in agentic mode (not plain response mode) 
- User sees live AI output and can continue conversation
- Default agent is gemini if no flag specified

### Technical Requirements
- Integrate with existing renv workflow
- Support same repo specification format as renv
- Execute within the containerized environment
- Pass through plain text prompts without additional processing
- Maintain interactive session for continued conversation

## Implementation Notes
- Use renv's existing container management and setup
- Execute AI CLI commands via `manage_container()` with proper command construction
- Support agent selection via command line flags
- Ensure proper working directory and environment setup
