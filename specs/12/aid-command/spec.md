# Aid Command - AI-driven Development Tool

## Problem
Need a streamlined way to use Claude CLI in interactive mode for development tasks within containerized environments.

## Solution
Create `aid` (AI Develop) command that:
- Accepts `aid repo_owner/repo_name <prompt in plain text>` syntax
- Reuses renv machinery for containerized environment setup
- Launches Claude CLI interactively with the prompt pre-sent
- User sees live Claude output and can continue the conversation
- When delegating to renv, insert the `--` separator before the claude command so container options are parsed correctly
- Support model selection flags provided before the repo spec (`--claude`, `--codex`, `--gemini`), defaulting to Claude

## Implementation
1. Create new script `rockerc/aid.py` following renv pattern
2. Parse `aid repo_owner/repo_name <prompt>` arguments
3. Setup containerized environment using renv machinery
4. Launch Claude CLI in interactive mode (`claude -p "<prompt>"`) from workspace directory `/workspaces/{container_name}`
