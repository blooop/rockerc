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
❌ `prepare_launch_plan()` - Multiple incompatibilities (see detailed analysis below)
❌ `execute_plan()` - Full flow incompatible with renv's cwd management
❌ Config loading - Different formats (rockerc.yaml vs renv's custom building)

## Detailed: Why prepare_launch_plan() Cannot Be Used

### Problem 1: Config Format Incompatibility

**rockerc expects volume as STRING:**
```yaml
# rockerc.yaml
volume: '"${PWD}":/workspaces/"${CONTAINER_NAME}":Z'
```

**renv creates volume as LIST:**
```python
config["volume"] = [
    f"{branch_dir}:{docker_branch_mount}:Z",
]
```

### Problem 2: yaml_dict_to_args() Doesn't Handle Lists

`yaml_dict_to_args()` in rockerc.py line 306:
```python
for k, v in d.items():
    segments.extend([f"--{k}", str(v)])  # <-- str(v) on a list!
```

This converts a Python list to a STRING REPRESENTATION:
```
Input:  volume = ['/path:/mount:Z']
Output: --volume ['/path:/mount:Z']  # Malformed! Includes brackets
```

### Problem 3: Duplicate Volume Mounts

`prepare_launch_plan()` calls `build_rocker_arg_injections()` which adds volume via `ensure_volume_binding()`.

Combined with renv's existing volume in config dict:
```bash
# From renv's config dict (malformed):
--volume ['/home/user/renv/blooop/bencher-main:/workspaces/bencher-main:Z']

# From build_rocker_arg_injections (correct):
--volume /home/user/renv/blooop/bencher-main:/workspaces/bencher-main:Z
```

Result: Docker error due to duplicate/malformed volume arguments

### Problem 4: Working Directory Management

`prepare_launch_plan()` doesn't support renv's cwd management pattern where cwd must be:
1. Changed BEFORE launch (for `cwd` extension)
2. Restored AFTER launch (for clean TTY)

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

## Final Implementation (Completed)

### VSCode Mode - Full Unified Backend
**Status:** ✅ Complete - Uses prepare_launch_plan() directly

renvvsc now uses the exact same flow as rockervsc:
1. Remove volume from config dict
2. Call `prepare_launch_plan()` which adds volume via `build_rocker_arg_injections()`
3. Launch container with correct cwd (for cwd extension)
4. **Restore cwd immediately after launch** (critical for clean TTY)
5. Wait for container
6. Launch VSCode
7. Attach interactive shell

### Terminal Mode - Helper Function Reuse
**Status:** ✅ Complete - Uses core.py helpers for consistency

Terminal mode calls core.py helper functions directly:
- `ensure_name_args()` - Adds --name and --image-name
- `add_extension_env()` - Adds ROCKERC_EXTENSIONS env var
- `ensure_volume_binding()` - Adds volume mount

Cannot use full `prepare_launch_plan()` because:
- Terminal mode must NOT be detached (needs to run command directly)
- prepare_launch_plan always adds --detach

### Result
Maximum code reuse achieved while respecting architectural differences:
- VSCode mode: 100% unified with rockervsc
- Terminal mode: Reuses all config building helpers from core.py
- Both modes handle cwd correctly for the cwd extension
- All tests pass
