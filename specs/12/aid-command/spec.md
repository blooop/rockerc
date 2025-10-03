# Aid Command - AI-driven Development Tool

## Problem
Need a streamlined way to use Claude CLI in agent mode for automated development tasks within containerized environments.

## Solution
Create `aid` (AI Develop) command that:
- Accepts `aid repo_owner/repo_name <prompt in plain text>` syntax
- Reuses renv machinery for containerized environment setup
- Launches Claude CLI in agent mode with the provided prompt
- User sees live Claude output and can interact with the container

## Implementation
1. Create new script `rockerc/aid.py` following renv pattern
2. Parse `aid repo_owner/repo_name <prompt>` arguments
3. Setup containerized environment using renv machinery
4. Launch Claude CLI in agent mode (`claude --agent -p "<prompt>"`) from workspace directory `/workspaces/{container_name}`
