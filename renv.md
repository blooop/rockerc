
make a tool that supports this commands

renv [user/repo_name:branch]

This is a environment manager tool that makes it seamless to work in a variety of repos at the same time.

The workflow to open a rocker devcontainer based on a third party repo.

ie

`renv blooop/bencher@main`

should clone https://github.com/blooop/bencher as a bare repo in ~/renv/blooop/bencher and then create a worktree for the branch `main`  it should then `cd` to that folder and run rockerc, which will build a container based on the contents of the repo and enter a container.

if I then did

`renv blooop/bencher@feature/over_time_limited`  it should check to see if the repo is already cloned (which it is), and then create a new worktree for the `feature/over_time_limited` branch, change to that worktree, and use rockerc to build and enter a container.

if I then did

`renv blooop/bencher@main` it should take me back to an environment in the original worktree leaving my other worktrees intact.

In addition if I did

`renv osrf/rocker` it should automatically set up the folder structure and bare repo clone of https://github.com/osrf/rocker:main in ~/renv/osrf/rocker and set up the worktree of the branch `main`


### 2. Intelligent Autocompletion

The tool should includes comprehensive autocompletion support using `iterfzf`:

#### User Completion
When typing a partial username, it completes based on existing directories in `~/renv/`:
```bash
renv blo<TAB>    # Completes to blooop/ if ~/renv/blooop/ exists
```

#### Repository Completion
When typing after a username with `/`, it completes repository names:
```bash
renv blooop/ben<TAB>    # Completes to blooop/bencher if ~/renv/blooop/bencher exists
```

#### Branch Completion
When typing after a repository with `@`, it completes branch names using git commands:
```bash
renv blooop/bencher@fea<TAB>    # Completes to available branches like feature/xyz
```
