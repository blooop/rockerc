I should not get this error. ```ags@ags-7520:~$ renv
[renv] INFO: Setting up environment for blooop/renv@fsearch
[renv] INFO: Fetching latest changes for blooop/renv
[renv] INFO: Successfully fetched latest changes
[renv] INFO: Worktree already exists for blooop/renv@fsearch
[renv] INFO: Will mount /home/ags/renv/blooop/renv/worktree-fsearch to /workspaces and start in /workspaces
[renv] INFO: Attach directory for container: /renv
[renv] INFO: Running rockerc with volumes: /home/ags/renv/blooop/renv:/repo.git, /home/ags/renv/blooop/renv/worktree-fsearch:/renv and workdir: /renv
[renv] INFO: Setting GIT_DIR=/repo.git/worktrees/worktree-fsearch and GIT_WORK_TREE=/renv in container
[renv] INFO: Container 'renv-fsearch' does not exist. Building new container...
No local rockerc.yaml found - using defaults. Create rockerc.yaml to customize.
``` if there is no rockerc it should just launch with the defaults.