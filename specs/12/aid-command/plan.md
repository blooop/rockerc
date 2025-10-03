# Implementation Plan for Aid Command

## Overview
Create a new command `aid` that combines renv's containerization with Claude Code CLI for automated development workflows.

## Architecture
- Reuse renv's RepoSpec parsing and container management
- Add CLAUDE.MD injection into worktree
- Launch Claude Code CLI instead of bash/custom commands

## Detailed Steps

### 1. Create rockerc/aid.py
- Import necessary components from renv.py
- Create main() entry point for aid command
- Parse arguments: `aid repo_owner/repo_name <prompt in plain text>`

### 2. Argument Parsing
- First positional arg: repo_spec (owner/repo[@branch])
- Remaining args: prompt text (join as string)
- Options: --force, --nocache, --no-container (inherited from renv)

### 3. CLAUDE.MD Injection
- Create CLAUDE.MD template with the specified workflow
- After setup_branch_copy(), write CLAUDE.MD to worktree root
- Ensure file exists before launching container

### 4. Container Launch with Claude Code
- Reuse manage_container() logic from renv
- Instead of interactive bash or custom command, launch:
  - `claude-code --prompt "<user_prompt>"`
- Ensure Claude Code CLI is available in container (check rocker extensions or renv config)

### 5. Add Entry Point
In pyproject.toml [project.scripts]:
```
aid = "rockerc.aid:main"
```

### 6. Testing Strategy
- Test with existing renv repos
- Verify CLAUDE.MD is created in worktree
- Verify Claude Code launches with prompt
- Test error handling (missing repo, invalid spec, etc.)

## Code Reuse Strategy
- Import from renv.py:
  - RepoSpec class and parsing
  - setup_branch_copy()
  - manage_container() (possibly with modifications)
  - get_worktree_dir()
  - build_rocker_config()

## Open Questions
1. Should aid create a new branch automatically, or use existing branch?
   - Decision: Follow renv pattern, use existing branch or @branch syntax
2. How to ensure Claude Code CLI is available in container?
   - Decision: Document requirement in renv config or add to renv_rockerc_template.yaml
3. Should aid be interactive or one-shot?
   - Decision: Launch Claude Code interactively, let it iterate
