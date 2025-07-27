# renv - Rocker Environment Manager

## Overview

`renv` is a tool for seamless multi-repo development using git worktrees and rocker containers. It automates cloning, worktree management, and container launching, making it easy to switch between branches and repositories in isolated environments.

## Installation

Install via pipx:
```bash
pipx install rockerc
```

Enable shell autocompletion:
```bash
renv --install
source ~/.bashrc  # or restart your terminal
```

## Usage

### Basic Syntax
```bash
renv [owner/repo[@branch][#subfolder]] [options]
```
- `owner/repo`: GitHub repository (e.g., `blooop/bencher`, `osrf/rocker`)
- `@branch`: Branch name (defaults to `main`)
- `#subfolder`: Optional subfolder to start in

### Major Workflows

#### 1. Clone and Work on a Repo
```bash
renv blooop/bencher@main
```
- Clones as bare repo to `~/renv/blooop/bencher`
- Creates worktree for `main` at `~/renv/blooop/bencher/worktree-main`
- Launches a rocker container in that worktree

#### 2. Switch Branches (Isolated Worktrees)
```bash
renv blooop/bencher@feature/new-feature
```
- Creates new worktree for the branch
- Launches container in the new worktree
- Previous worktrees remain intact

#### 3. Switch Back to Main
```bash
renv blooop/bencher@main
```
- Re-attaches to the main branch worktree and container

#### 4. Work on Multiple Repos
```bash
renv osrf/rocker@main
```
- Sets up and launches a container for another repo in parallel

#### 5. Debug or Manual Management
```bash
renv blooop/bencher@main --no-container
```
- Sets up worktree but does not launch container

## Directory Structure
```
~/renv/
├── blooop/
│   └── bencher/
│       ├── HEAD
│       ├── config
│       ├── worktree-main/
│       └── worktree-feature-new-feature/
└── osrf/
    └── rocker/
        ├── HEAD
        └── worktree-main/
```

## Options
- `--no-container`: Set up worktree only
- `--force`: Force rebuild container
- `--nocache`: Rebuild container with no cache

## Intelligent Autocompletion & Fuzzy Finder

When running `renv` without arguments, or with partial input, interactive fuzzy finding is enabled using `iterfzf`:

- **Partial Matching**: As you type, `iterfzf` matches any part of the repo or branch name. For example, typing `bl ben ma` will match `blooop/bencher@main`.
  - You can type fragments separated by spaces to quickly narrow down results.
  - Example prompt: `Select repo@branch (type 'bl ben ma' for blooop/bencher@main):`
- **User Completion**: Type a partial username and press TAB to complete based on existing directories in `~/renv/`.
  ```bash
  renv blo<TAB>    # Completes to blooop/ if ~/renv/blooop/ exists
  ```
- **Repository Completion**: After a username and `/`, TAB completes repository names.
  ```bash
  renv blooop/ben<TAB>    # Completes to blooop/bencher if ~/renv/blooop/bencher exists
  ```
- **Branch Completion**: After a repository and `@`, TAB completes branch names using git.
  ```bash
  renv blooop/bencher@fea<TAB>    # Completes to available branches like feature/xyz
  ```
- **Interactive Selection**: If no argument is provided, a fuzzy finder UI appears, allowing you to search and select from all available repo@branch combinations. You can use partial words and space-separated fragments for fast selection.

This makes switching between repos and branches fast and error-free, even in large multi-repo setups.

## Requirements
- Git
- rockerc
- rocker (Docker)

## Troubleshooting
- If repo exists, latest changes are fetched
- If worktree exists, it is reused
- If container build fails, check `rockerc.yaml`, Docker, and rocker installation

## Notes
- Branch names with `/` are converted to safe directory names
- Multiple worktrees and containers can be active in parallel
- Autocompletion covers user, repo, and branch names

---
For more details, see the project README or run `renv --help`.
