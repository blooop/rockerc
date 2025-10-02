ags@ags-7510:~$ renv blooop/bencher
INFO: Working with: blooop/bencher@main
INFO: Cloning cache repository: git@github.com:blooop/bencher.git
Cloning into '/home/ags/renv/.cache/blooop/bencher'...
remote: Enumerating objects: 29012, done.
remote: Counting objects: 100% (1102/1102), done.
remote: Compressing objects: 100% (418/418), done.
remote: Total 29012 (delta 804), reused 745 (delta 684), pack-reused 27910 (from 2)
Receiving objects: 100% (29012/29012), 35.20 MiB | 18.52 MiB/s, done.
Resolving deltas: 100% (21933/21933), done.
INFO: Creating branch copy for: main
Already on 'main'
Your branch is up to date with 'origin/main'.
Already up to date.
Global         Local          Status  
lazygit                       loaded  
neovim                        loaded  
nvidia                        filtered
persist-image  persist-image  loaded  
x11            x11            loaded  
user           user           loaded  
pull           pull           loaded  
git            git            loaded  
git-clone      git-clone      loaded  
fzf            fzf            loaded  
ssh            ssh            loaded  
ssh-client     ssh-client     loaded  
cwd            cwd            loaded  
               deps           loaded  
               pixi           loaded  
INFO: Container appears corrupted (possible breakout detection), launching new container with rocker
bencher-main
Error response from daemon: removal of container bencher-main is already in progress
INFO: Using rocker to launch new container directly
INFO: Running rocker: rocker --persist-image --x11 --user --pull --git --git-clone --fzf --ssh --ssh-client --lazygit --neovim --cwd --deps --pixi --extension-blacklist ['nvidia'] --name bencher-main --hostname bencher-main --_renv_target_dir /home/ags/renv/blooop/bencher-main ubuntu:22.04 bash
Extension oyr_cap_add doesn't support default arguments. Please extend it.
Extension oyr_cap_drop doesn't support default arguments. Please extend it.
Extension oyr_colcon doesn't support default arguments. Please extend it.
Extension oyr_mount doesn't support default arguments. Please extend it.
Extension oyr_run_arg doesn't support default arguments. Please extend it.
Extension oyr_spacenav doesn't support default arguments. Please extend it.
usage: rocker [-h] [--noexecute] [--nocache] [--nocleanup] [--persist-image]
              [--pull] [--version] [--cargo] [--claude] [--claude-npm]
              [--codex] [--conda] [--cuda] [--curl] [--cwd] [--cwd-name]
              [--detach] [--dev-helpers] [--devices [DEVICES ...]]
              [--env NAME[=VALUE] [NAME[=VALUE] ...]] [--env-file ENV_FILE]
              [--expose EXPOSE] [--fzf] [--gemini] [--git]
              [--git-config-path GIT_CONFIG_PATH] [--git-clone]
              [--group-add GROUP_ADD] [--home] [--hostname HOSTNAME]
              [--ipc IPC] [--isaacsim] [--lazygit] [--locales] [--name NAME]
              [--neovim] [--network {none,bridge,host}] [--npm]
              [--nvidia [{auto,runtime,gpus}]]
              [--nvidia-glvnd-version {16.04,18.04,20.04,22.04,24.04}]
              [--nvidia-glvnd-policy {latest_lts}] [--deps [DEPS]]
              [--oyr-cap-add CAPABILITY] [--oyr-cap-drop CAPABILITY]
              [--oyr-colcon] [--oyr-mount PATH [PATH ...]]
              [--oyr-run-arg DOCKER_RUN_ARG] [--oyr-spacenav] [--palanteer]
              [--pixi] [--port PORT] [--privileged] [--pulse]
              [--rmw {cyclonedds,fastrtps,zenoh}] [--ros-humble]
              [--shm-size SHM_SIZE] [--spec-kit] [--ssh] [--ssh-client]
              [--tzdata] [--ulimit TYPE=SOFT_LIMIT[:HARD_LIMIT]
              [TYPE=SOFT_LIMIT[:HARD_LIMIT] ...]] [--urdf-viz] [--user]
              [--user-override-name USER_OVERRIDE_NAME] [--user-preserve-home]
              [--user-preserve-groups [USER_PRESERVE_GROUPS ...]]
              [--user-preserve-groups-permissive]
              [--user-override-shell USER_OVERRIDE_SHELL] [--uv] [--vcstool]
              [--volume HOST-DIR[:CONTAINER-DIR[:OPTIONS]]
              [HOST-DIR[:CONTAINER-DIR[:OPTIONS]] ...]] [--x11]
              [--mode {interactive,non-interactive,dry-run}]
              [--image-name IMAGE_NAME]
              [--extension-blacklist [EXTENSION_BLACKLIST ...]]
              [--strict-extension-selection]
              image [command ...]
rocker: error: unrecognized arguments: --_renv_target_dir
