# Code Reuse Requirements: renv vs rockerc

## User Requirements

### Functional Requirements
1. **renvvsc** must follow the same flow as **rockervsc**:
   - Build/start container (detached)
   - Launch VSCode attached to container
   - Attach interactive shell to container

2. Terminal handling must be clean:
   - No formatting issues
   - No missed keypresses
   - Same quality as rockervsc

3. Maximum code reuse between renv and rockerc where possible

## Architectural Layering

```
Base Layer (core.py):
├── Container lifecycle: prepare_launch_plan(), execute_plan()
├── Flow components: wait_for_container(), launch_vscode(), interactive_shell()
└── Utilities: container_exists(), stop_and_remove_container()

Application Layer:
├── rockerc: Reads rockerc.yaml, uses core.py prepare_launch_plan() + execute_plan()
├── rockervsc: Thin wrapper, adds --vsc flag, delegates to rockerc
├── renv: Custom config building, git worktrees, uses core.py flow components
└── renvvsc: Thin wrapper, adds --vsc flag, delegates to renv
```

## Key Architectural Differences

### rockerc
- Reads rockerc.yaml configuration format
- Uses `prepare_launch_plan()` + `execute_plan()` directly
- Never changes working directory
- Exits immediately via `sys.exit()` after execute_plan()
- Volume mounts: Single workspace directory

### renv
- Custom configuration building (incompatible with prepare_launch_plan())
- Manages git worktrees and branch copies
- **Must change working directory** for `cwd` extension to detect correct path
- Uses try/finally pattern for cleanup
- Volume mounts: Git worktree directory with custom patterns

## Code Reuse Strategy

### What CAN be reused directly:
✅ Individual flow components from `core.py`:
   - `wait_for_container()` - Wait for container to be ready
   - `launch_vscode()` - Launch VS Code attached to container
   - `interactive_shell()` - Attach shell with proper TTY handling
   - `container_exists()`, `stop_and_remove_container()` - Container utilities

### What CANNOT be reused directly:
❌ `prepare_launch_plan()` - Expects rockerc.yaml config format
❌ `execute_plan()` - Full flow incompatible with renv's cwd management
❌ Config loading - Different formats (rockerc.yaml vs renv's custom building)

## Critical Implementation Details

### Working Directory Management
**Problem:** `renv` needs to change cwd for container launch (cwd extension), but this breaks TTY handling during attach operations.

**Solution:**
1. Change cwd **before** launching container
2. **Restore cwd immediately after** container launch
3. Perform all attach operations (VSCode + shell) with original cwd

```python
# Change cwd for container launch
os.chdir(target_dir)

# Launch container
if not exists:
    run_rocker_command(config, None, detached=True)

# CRITICAL: Restore cwd before attach operations
os.chdir(original_cwd)

# Now attach with original cwd (matching rockervsc)
launch_vscode(container_name, container_hex)
interactive_shell(container_name)
```

### VSCode Mode Flow

**rockervsc flow (via core.py):**
```
rockerc.run_rockerc()
  → prepare_launch_plan(vscode=True)
  → execute_plan()
    → launch_rocker() [detached]
    → wait_for_container()
    → launch_vscode()
    → interactive_shell()
  → sys.exit()
```

**renvvsc flow (using core.py components):**
```
renv.run_renv(--vsc)
  → manage_container(vsc=True)
    → os.chdir(target_dir)  # For cwd extension
    → run_rocker_command() [detached]
    → os.chdir(original_cwd)  # CRITICAL: Before attach
    → wait_for_container()
    → launch_vscode()
    → interactive_shell()
    → return
```

## Lessons Learned

1. **Architectural differences matter:** renv's cwd management requirement fundamentally changes the flow

2. **Granular reuse is better:** Reusing individual flow components (wait_for_container, launch_vscode, interactive_shell) was more successful than trying to reuse the full prepare_launch_plan/execute_plan

3. **TTY handling is sensitive:** Working directory state during interactive shell attachment affects terminal behavior

4. **Timing matters:** Restore cwd **between** launch and attach phases, not at the end

## Future Refactoring Opportunities

If more commonality is needed:
1. Extract config transformation layer to normalize renv → rockerc format
2. Make prepare_launch_plan() accept a "custom_cwd_handler" callback
3. Create a "launch_and_restore_cwd()" helper in core.py

However, current approach (individual component reuse) is clean and maintainable given the architectural constraints.
