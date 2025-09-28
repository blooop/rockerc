
 I am adding a new tool to complement rockerc.  its called renv and uses rocker to create a development container. You
   can use rockerc as inspiration for how to manage rocker, but create renv as a separate tool that calls rocker 
  directly. rockerc expects there to be rockerc files, whereas renv should work on any repo without a rockerc file and 
  defines its own require extension for basic development. I have included some template workflows as bash scripts, you
   must implement rocker to meeting the all the specs in the markdown file and also the tests stubs I left in 
  test/worksflows. use the pixi environment and pixi tasks to run tests and ci. you are working on the host machine   where rocker is installed. aad an executable `renv` to the pyproject.toml.  write lots of tests and work step by test
   to implement the features and higher level goal


# renv - Rocker Environment Manager

## Overview

`renv` is a tool for seamless multi-repo development using git worktrees and rocker containers. It automates cloning, worktree management, and container launching, making it easy to switch between branches and repositories in isolated environments.

The main workflow to support is the user can type a `renv repo_owner/repo_name` and re enter the container seamlessly, ie, if it needs to be built, build and attach.  If the image is already built but not running, start the container and attach, and if the container is already running, it should attach to that container.  

renv uses rocker to manage the building of the dockerfiles via extensions. renv automatically loads some default extensions to provide a base level of developer experience such as ssh, git etc. The user can add their own development tools by creating an extension for it.  The aim is that you only have to write a dockerfile for your tools once, and then you can bring it along to any development environment you want via a flag. see https://github.com/blooop/deps_rocker and https://github.com/osrf/rocker.   When the use runs the renv command on a repo, the user will enter a fully set up development container directly inside that git repository. 

renv automatically names the containers based on the repo name and branch name. so renv blooop/test_renv@feature1 creates a docker image and container named test_renv-feature1 and enters a folder called test_renv as that is the repo name. 

You can also use renv to run commands directly in the container and branch.  The last arguments are passed on directly to rocker which passes them onto docker. The behavior between entering a container and running a command is identical to running that command inline

Enable shell autocompletion:
```bash
renv --install
source ~/.bashrc  # or restart your terminal
```

## Usage

### Basic Syntax
```bash
renv [owner/repo[@branch][#subfolder]] [command]
```
- `owner/repo`: GitHub repository (e.g., `blooop/test_renv`, `osrf/rocker`)
- `@branch`: Branch name (defaults to `main`)
- `#subfolder`: Optional subfolder to start in
- `command`: Option bash command to execute in the container

### Major Workflows

#### 1. Clone and Work on a Repo
```bash
renv blooop/test_renv@main
```
- Clones as bare repo to `~/renv/blooop/test_renv`
- Creates worktree for `main` at `~/renv/blooop/test_renv/worktree-main`
- Launches a rocker container in that worktree
- git command work immediately on entering (ie, enter into the correct folder for git to work with worktrees, and bare repo is mounted properly)

#### 2. Switch Branches (Isolated Worktrees)
```bash
renv blooop/test_renv@feature/new-feature
```
- Creates new worktree for the branch
- Launches container in the new worktree
- Previous worktrees remain intact

#### 3. Switch Back to Main
```bash
renv blooop/test_renv@main
```
- Re-attaches to the main branch worktree and container. Does not need to rebuild

#### 4. Work on Multiple Repos
```bash
renv osrf/rocker@main
```
- Sets up and launches a container for another repo while retaining access to existing repos and branches

#### 5. Run a command in a container

```bash
renv blooop/test_renv git status
```
- Runs git status command and exit the container immediately

#### 5. Run a command in a container on a branch

```bash
renv blooop/test_renv@main git status
```

- Runs git status command and exit the container immediately

#### 5. Run a multi stage command in a container

```bash
renv blooop/test_renv "bash -c 'git status; pwd; ls -l'"

```

- prints the git status, the current working directory, and a list of files.

#### 6. VS Code Integration with renvsc
```bash
renvsc blooop/test_renv@main
```
- Works exactly like `renv` but automatically launches VS Code attached to the container
- Creates a detached container suitable for VS Code Remote-Containers extension
- All the same features as `renv`: worktree management, container reuse, multi-repo support
- VS Code opens directly in the repository with full container environment access

#### 7. Debug or Manual Management
```bash
renv blooop/test_renv@main --no-container
```
- Sets up worktree but does not launch container


some of these workflows have been set up as scripts that must get run as part of testing. 

## Directory Structure
```
~/renv/
├── blooop/
│   └── bencher/
│       ├── HEAD
│       ├── config
│       ├── worktrees
│   └── test_renv/
│       ├── HEAD
│       ├── config
│       ├── worktrees
└── osrf/
    └── rocker/
        ├── HEAD
        └── worktrees
```

by default renv will ignore the rocker extensions --cwd --nvidia  and it will pass --nocleanup and --persist image to rocker. It ignores --cwd because it uses its own volume mounting and workspace logic.


by default renv has these extensions enabled

image: ubuntu:22.04
# Default arguments enabled for container setup
args:
  - user    # Enable user mapping for file permissions
  - pull    # Enable automatic image pulling
  - git     # Enable git integration
  - git-clone # Enable git clone support
  - ssh     # Enable SSH support
  - nocleanup # Prevent cleanup after run
  - persist-image # Persist built image after run so its always cached

extension-blacklist:
  - nvidia  # Disable NVIDIA GPU support by default
  - create-dockerfile # Overly verbose for 3rd party repos
  - cwd     # We have custom mounting logic




## Options
- `--no-container`: Set up worktree only
- `--force`: Force rebuild container
- `--nocache`: Rebuild container with no cache

## Intelligent Autocompletion & Fuzzy Finder

When running `renv` without arguments, or with partial input, interactive fuzzy finding is enabled using `iterfzf`:

- **Partial Matching**: As you type, `iterfzf` matches any part of the repo or branch name. For example, typing `bl tes ma` will match `blooop/test_renv@main`.
  - You can type fragments separated by spaces to quickly narrow down results.
  - Example prompt: `Select repo@branch (type 'bl tes ma' for blooop/test_renv@main):`
- **User Completion**: Type a partial username and press TAB to complete based on existing directories in `~/renv/`.
  ```bash
  renv blo<TAB>    # Completes to blooop/ if ~/renv/blooop/ exists
  ```
- **Repository Completion**: After a username and `/`, TAB completes repository names.
  ```bash
  renv blooop/tes<TAB>    # Completes to blooop/test_renv if ~/renv/blooop/test_renv exists
  ```
- **Branch Completion**: After a repository and `@`, TAB completes branch names using git.
  ```bash
  renv blooop/test_renv@fea<TAB>    # Completes to available branches like feature/xyz
  ```
- **Interactive Selection**: If no argument is provided, a fuzzy finder UI appears, allowing you to search and select from all available repo@branch combinations. You can use partial words and space-separated fragments for fast selection.

This makes switching between repos and branches fast and error-free, even in large multi-repo setups.

## VS Code Integration (renvsc)

`renvsc` provides seamless VS Code integration with renv-managed containers. It combines all the functionality of `renv` with automatic VS Code launching and attachment.

### Key Features
- **Full renv compatibility**: All `renv` commands work with `renvsc`
- **Automatic VS Code launch**: Opens VS Code attached to the container after creation
- **Detached containers**: Creates containers in detached mode suitable for VS Code Remote-Containers
- **Container reuse**: Reattaches VS Code to existing containers without rebuilding
- **Multi-repo support**: Switch between different repos and branches with VS Code

### Usage Examples

#### Basic Usage
```bash
renvsc blooop/test_renv@main
```
- Creates/reuses container for the repository and branch
- Launches VS Code attached to the container
- Working directory is set to the repository root

#### Branch Switching
```bash
renvsc blooop/test_renv@feature/new-feature
```
- Creates new worktree and container for the feature branch
- Opens VS Code in the new environment
- Previous containers remain available

#### Multi-Repository Development
```bash
renvsc osrf/rocker@main
```
- Switch to a different repository while keeping existing containers
- VS Code opens in the new repository environment

### Requirements for renvsc
- All standard renv requirements (Git, rocker, Docker)
- VS Code installed with Remote-Containers extension
- Container must support VS Code server (automatically handled by renv's base configuration)

### Technical Details
- Uses `--detach` flag for container creation (required for VS Code)
- Removes `persist-image` extension (incompatible with detached mode)
- Generates container hex identifier for VS Code Remote-Containers URI
- Maintains full compatibility with renv's configuration and extensions

## Requirements
- Git
- rockerc
- rocker (Docker)
- For renvsc: VS Code with Remote-Containers extension

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


this is an example of how to use oyr-run-arg to pass arguments to docker through rocker.
