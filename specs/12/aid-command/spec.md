# Aid Command - AI-driven Development Tool

## Problem
Need a streamlined way to use Claude Code for automated development tasks within containerized environments. Current workflow requires manual steps to set up containers and invoke Claude Code.

## Solution
Create `aid` (AI Develop) command that:
- Accepts `aid repo_owner/repo_name <prompt in plain text>` syntax
- Reuses renv machinery for containerized environment setup
- Injects custom CLAUDE.MD workflow instructions
- Automatically invokes Claude Code CLI with the provided prompt
- Lets the agent iterate on the prompt within the container

## Workflow
The aid command uses this CLAUDE.MD:
```
This project uses pixi to manage its environment.

look at the pyproject.toml to see the pixi tasks

Workflow:
    * On first message:
        - create a new specification according to the pattern specs/01/short-spec-name/spec.md.  Keep it as concise as possible
        - create a plan in the same folder, you can expand more here
        - commit the contents of this folder only

    * Every time I ask for a change
        - update the spec.md with clarifications while keeping it concise. commit if there are changes
        - implement the change
        - run `pixi run ci`
        - fix errors and iterate until ci passes
        - only if ci passes commit the changes.
```

## Implementation
1. Create new script `rockerc/aid.py` following renv pattern
2. Parse `aid repo_owner/repo_name <prompt>` arguments
3. Setup containerized environment using renv machinery
4. Inject CLAUDE.MD into the worktree
5. Launch Claude Code CLI with prompt inside container
