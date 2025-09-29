Unified Detached Flow & VS Code Integration
==========================================

Overview
--------
Version 0.13.0 introduces a unified always-detached execution model. The container is
started (or reused) in detached mode, VS Code can optionally attach, and the user
is placed in an interactive shell via ``docker exec``.

Sequence
--------
1. Merge global and project configuration (``~/.rockerc.yaml`` + local ``rockerc.yaml``).
2. Optionally build an image if ``dockerfile`` key provided (strip ``pull`` arg).
3. Inject required rocker flags (``--detach``, ``--name``, ``--image-name``, workspace volume).
4. Launch rocker only if the container does not already exist.
5. Poll for container availability (tunable via environment variables).
6. (Optional) Launch VS Code with ``--vsc`` (or by using the ``rockervsc`` alias).
7. Open interactive shell with ``docker exec -it <name> $SHELL``.

Flags & Options
---------------
--vsc
    Launch and attach VS Code after the container is available.
--force / -f
    Rename any existing container (``<name>_YYYYmmdd_HHMMSS``) before creating a new one.
--create-dockerfile
    Generate ``Dockerfile.rocker`` and a runnable ``run_dockerfile.sh`` from rocker's dry-run.

Environment Variables
---------------------
ROCKERC_WAIT_TIMEOUT
    Total seconds to wait for container availability (default 20).
ROCKERC_WAIT_INTERVAL
    Interval between existence checks (default 0.25).

Edge Cases & Behavior
---------------------
Existing container
    Reused without re-running rocker; shell & VS Code attach proceed.
Force recreate
    Existing container is renamed then a new one is created.
VS Code missing
    Logged warning; shell still opens.
--rm usage
    Discouraged with ``--vsc`` (could delete the container while VS Code remains open); rockerc does not strip it automatically.
Name collision
    Use ``--force`` to intentionally create a new container.

Rationale
---------
Detaching the original rocker process prevents TTY contention and resolves prior issues
with dropped keypresses or interrupted interactive sessions when VS Code attaches.

Troubleshooting
---------------
Container never appears
    Increase ``ROCKERC_WAIT_TIMEOUT`` or inspect docker daemon logs.
VS Code fails to attach
    Run the logged ``code --folder-uri ...`` command manually; ensure the ``code`` CLI is installed.
Shell exits immediately
    Confirm your image contains the shell referenced by ``$SHELL`` (defaults to ``/bin/bash``).

Testing Notes
-------------
Unit tests mock docker subprocess calls, ensuring no real container lifecycle changes
occur during test runs. See ``test_launch_plan.py`` for examples.

