
make a tool that supports this commands

renv [repo_name:branch]

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



extra: once all the basics work

use: argcomplete

to enable autocomplete.  ie, if I start typing blooop/ then it should autocomplete the available repos, and once
I have typed blooop/bencher@ it should autocomplete the available branches. 