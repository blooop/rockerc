# Container Lifecycle Architecture

## Critical Design Principle: Always Detached + Attach Pattern

**ALL rockerc and renv tools MUST follow the same container lifecycle pattern:**

1. **Launch Phase**: Always create containers in detached mode with a keep-alive process
2. **Attach Phase**: Use `docker exec -it` to attach interactive shells or launch VSCode
3. **Persistence**: Containers remain running after shell/VSCode sessions end

This pattern ensures:
- Consistent behavior across all tools (rockerc, renv, renvvsc, rockervsc)
- Containers can be reused across multiple sessions
- Proper attachment via `docker exec` without "container not running" errors
- VSCode can reliably attach to running containers

## Implementation Requirements

### Core Functions (rockerc/core.py)

1. **`wait_for_container()`** MUST wait for containers to be **running**, not just existing
2. **`container_is_running()`** MUST distinguish between existing vs running containers
3. **`prepare_launch_plan()`** MUST handle stopped containers by attempting to restart them

### Command Generation (rockerc/rockerc.py)

**`yaml_dict_to_args()` MUST automatically inject keep-alive commands:**

```python
# When --detach is present and no explicit command provided:
if "--detach" in cmd_str and not has_explicit_command:
    cmd_str += " tail -f /dev/null"
```

**NEVER manually add keep-alive commands in individual tools** - this leads to inconsistency and missed cases.

### Container States and Transitions

```
[Non-existent]
    ↓ (rocker create --detach + tail -f /dev/null)
[Running + Keep-alive]
    ↓ (docker exec -it)
[Running + Interactive Shell]
    ↓ (shell exit)
[Running + Keep-alive] ← Container persists!
    ↓ (docker exec -it OR code --folder-uri)
[Running + New Session]
```

## Historical Context

### The Regression Root Cause

This issue was NOT a recent regression but a **long-standing architectural problem**:

- **Before Fix**: Each tool (renv.py, renvvsc.py) manually added `["tail", "-f", "/dev/null"]`
- **Problem**: Inconsistent application, missed cases, scattered logic
- **After Fix**: Centralized logic in `yaml_dict_to_args()` ensures ALL detached containers get keep-alive

### Git History Timeline

- `de68392`: Manually fixed renv.py VSCode mode by adding keep-alive
- `f252e46`: Manually added keep-alive to regular renv mode
- `4a578ac`: **Proper fix** - centralized keep-alive logic in `yaml_dict_to_args()`

The "regression" was actually multiple tools having incomplete implementations.

## Testing Requirements

**EVERY test for detached containers MUST verify:**

1. `--detach` flag results in `tail -f /dev/null` being appended
2. `wait_for_container()` waits for running state, not just existence
3. `docker exec -it` can successfully attach to created containers
4. Containers persist after shell sessions end

**Example test pattern:**

```python
def test_detached_container_lifecycle():
    # Create detached container
    config = {"args": ["user"], "image": "ubuntu:22.04"}
    result = yaml_dict_to_args(config, "--detach --name test")

    # Must include keep-alive
    assert "tail -f /dev/null" in result

    # Must be able to attach
    assert can_exec_into_container("test")
```

## Integration Requirements

**When adding new tools or modifying existing ones:**

1. ✅ **DO**: Use `core.py` functions (`prepare_launch_plan`, `execute_plan`)
2. ✅ **DO**: Let `yaml_dict_to_args()` handle keep-alive logic automatically
3. ❌ **DON'T**: Manually append `["tail", "-f", "/dev/null"]` to rocker commands
4. ❌ **DON'T**: Create new container lifecycle patterns

## Monitoring and Prevention

**CI Requirements:**
- Integration tests MUST verify end-to-end container attachment
- Tests MUST run multiple times to catch intermittent failures
- Static analysis MUST flag manual keep-alive command injection

**Code Review Checklist:**
- [ ] Does this code create detached containers?
- [ ] Does it rely on `yaml_dict_to_args()` for keep-alive logic?
- [ ] Are there integration tests verifying container attachment?
- [ ] No manual `tail -f /dev/null` additions?

## Debugging Container Issues

**When containers fail to attach:**

1. Check `docker ps -a` - is container created but exited?
2. Check `docker logs <container>` - any immediate exit errors?
3. Verify rocker command includes `tail -f /dev/null`
4. Verify `wait_for_container()` waits for running state
5. Test `docker exec -it <container> /bin/bash` manually

**Common symptoms of missing keep-alive:**
- "Error response from daemon: container X is not running"
- Container appears in `docker ps -a` but not `docker ps`
- VSCode attachment fails immediately
- Interactive shell attachment fails