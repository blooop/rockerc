# Fix --vsc Option in renv

## Problem
The --vsc option in renv has broken. Previously, running `renv --vsc` or `renvvsc` would:
- Launch a detached container
- Attach VSCode
- Attach a terminal

Currently, regular renv works but passing --vsc causes the container to crash.

## Root Cause
The real issue is in the VSCode workflow execution flow in renv. The problem is NOT the lowercase changes - that was a red herring.

**Working `rockervsc` flow:**
```python
if plan.vscode:
    launch_vscode(plan.container_name, plan.container_hex)
return interactive_shell(plan.container_name)
```

**Broken `renv --vsc` flow:**
```python
if plan.vscode:
    launch_vscode(plan.container_name, plan.container_hex, vsc_folder)
# Manual docker exec with working directory
exec_cmd = ["docker", "exec", "-it", "-w", workdir, container_name, "/bin/bash"]
return subprocess.run(exec_cmd, check=False).returncode
```

The issues:
1. `renv --vsc` doesn't use the robust `interactive_shell()` function
2. Manual `docker exec` construction may have TTY/interaction problems
3. Working directory handling with `-w` flag may not work properly
4. VSCode and terminal attachment both fail due to execution flow issues

## Solution
Fix the VSCode workflow in renv to follow the same patterns as `interactive_shell()` from core.py while maintaining the required working directory functionality.

## Changes Made
1. **Use `subprocess.call()` instead of `subprocess.run()`** - matches core.py's `interactive_shell()`
2. **Use `os.environ.get("SHELL", "/bin/bash")` for shell detection** - matches core.py behavior
3. **Simplify TTY handling** - always use `-it` flags like core.py
4. **Keep working directory support** - renv needs `-w` flag that core.py doesn't support
5. **Update comments** - clarify why manual docker exec is needed vs using core.py's function

## Expected Outcome
- --vsc option works as before
- Container launches successfully with VSCode and terminal attached