# worktree_docker Implementation Checklist for Claude Code

This checklist summarizes all requirements and features for building the `worktree_docker` tool as described in the specification. Use this as a step-by-step guide to ensure full coverage and compliance.

---

## 1. General Requirements
- [ ] Implement a Python CLI tool called `worktree_docker` (executable via `pyproject.toml`)
- [ ] Use `rocker` directly for container management (not `worktree_docker`)
- [ ] Must work on any repo, no `worktree_docker` file required
- [ ] Use the `pixi` environment and tasks for tests and CI
- [ ] Write comprehensive tests for all workflows (see provided bash scripts)

## 2. Core Features
- [ ] Accept input: `worktree_docker [owner/repo[@branch][#subfolder]] [command]`
- [ ] Clone repo as bare to `~/worktree_docker/{owner}/{repo}`
- [ ] Create worktree for branch at `~/worktree_docker/{owner}/{repo}/worktree-{branch}`
- [ ] Launch rocker container in the worktree
- [ ] Automatically name containers/images as `{repo}-{branch}`
- [ ] If image not built, build it; if not running, start and attach; if running, attach
- [ ] Enter correct folder for git to work with worktrees
- [ ] Support switching branches and multiple parallel worktrees/containers
- [ ] Allow running commands directly in the container (e.g., `worktree_docker blooop/test_wtd git status`)
- [ ] Support multi-stage commands (e.g., `worktree_docker blooop/test_wtd "bash -c 'git status; pwd; ls -l'"`)
- [ ] Pass last arguments directly to rocker/docker

## 3. Default Extensions & Blacklist
- [ ] Default image: `ubuntu:24.04`
- [ ] Enable extensions: `user`, `pull`, `git`, `git-clone`, `ssh`, `nocleanup`, `persist-image`
- [ ] Blacklist extensions: `nvidia`, `create-dockerfile`, `cwd`
- [ ] Ignore rocker extensions: `--cwd`, `--nvidia`
- [ ] Always pass `--nocleanup` and `--persist-image` to rocker

## 4. Options & Flags
- [ ] `--no-container`: Set up worktree only, do not launch container
- [ ] `--force`: Force rebuild container
- [ ] `--nocache`: Rebuild container with no cache

## 5. Autocompletion & Fuzzy Finder
- [ ] Implement shell autocompletion for user, repo, and branch names
- [ ] If no argument, launch interactive fuzzy finder (e.g., `iterfzf`) to select repo@branch
- [ ] Support partial matching and TAB completion for user/repo/branch
- [ ] Interactive selection UI for repo@branch combinations

## 6. Directory Structure
- [ ] Organize repos and worktrees under `~/worktree_docker/{owner}/{repo}/worktree-{branch}`
- [ ] Support multiple worktrees and containers in parallel
- [ ] Convert branch names with `/` to safe directory names

## 7. Troubleshooting & Robustness
- [ ] If repo exists, fetch latest changes
- [ ] If worktree exists, reuse it
- [ ] If container build fails, provide clear error messages
- [ ] Autocompletion covers user, repo, and branch names

## 8. Documentation & Help
- [ ] Provide clear CLI help (`worktree_docker --help`)
- [ ] Document all options, workflows, and troubleshooting steps

## 9. Testing & Validation
- [ ] Implement and run all provided bash workflow scripts as tests
- [ ] Validate all major workflows:
    - Clone and work on repo
    - Switch branches
    - Switch back to main
    - Work on multiple repos
    - Run commands in container
    - Multi-stage commands
    - Debug/manual management
- [ ] Use pixi tasks for CI and test automation

---

**References:**
- [blooop/deps_rocker](https://github.com/blooop/deps_rocker)
- [osrf/rocker](https://github.com/osrf/rocker)
- Provided markdown spec and bash workflow scripts

---

**Note:** Check off each item as you implement and test it. This checklist ensures full compliance with the worktree_docker specification and robust, user-friendly development workflows.
