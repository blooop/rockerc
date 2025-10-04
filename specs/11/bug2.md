I am triggering the container breakout detected message when the renv dir has
  been wiped and there is still a container that was running from before. add a test
 case for this.  renv successfully restarts and attaches to a new container, but 
renvvsc does not. it doesn't rebuild the container or attach to it and just launches
 vscode with nothing to attach to. ```ags@ags-7510:~$ renvvsc blooop/bencher
INFO: Working with: blooop/bencher@main
INFO: Cloning cache repository: git@github.com:blooop/bencher.git
Cloning into '/home/ags/renv/.cache/blooop/bencher'...
remote: Enumerating objects: 29012, done.
remote: Counting objects: 100% (1103/1103), done.
remote: Compressing objects: 100% (420/420), done.
remote: Total 29012 (delta 805), reused 744 (delta 683), pack-reused 27909 (from 2)
Receiving objects: 100% (29012/29012), 35.20 MiB | 18.19 MiB/s, done.
Resolving deltas: 100% (21937/21937), done.
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
INFO: Container 'bencher-main' already exists; reusing.
INFO: Launched VS Code on container 'bencher-main'
INFO: Attaching interactive shell: docker exec -it bencher-main /bin/bash
OCI runtime exec failed: exec failed: unable to start container process: current 
working directory is outside of container mount namespace root -- possible container
 breakout detected: unknown
ags@ags-7510:~$ renv blooop/bencher
INFO: Working with: blooop/bencher@main
INFO: Fetching updates for cache: git@github.com:blooop/bencher.git
INFO: Branch copy already exists: /home/ags/renv/blooop/bencher-main
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
INFO: Container appears corrupted (possible breakout detection), launching new 
container with rocker
bencher-main
Error response from daemon: removal of container bencher-main is already in progress
INFO: Using rocker to launch new container directly
INFO: Running rocker: rocker --persist-image --x11 --user --pull --git --git-clone 
--fzf --ssh --ssh-client --lazygit --neovim --cwd --deps --pixi 
--extension-blacklist ['nvidia'] --name bencher-main --hostname bencher-main 
ubuntu:22.04 bash
Extension oyr_cap_add doesn't support default arguments. Please extend it.
Extension oyr_cap_drop doesn't support default arguments. Please extend it.
Extension oyr_colcon doesn't support default arguments. Please extend it.
Extension oyr_mount doesn't support default arguments. Please extend it.
Extension oyr_run_arg doesn't support default arguments. Please extend it.
Extension oyr_spacenav doesn't support default arguments. Please extend it.
Adding implicilty required extension(s) ['curl'] required by extension 'lazygit'
Active extensions ['curl', 'git', 'hostname', 'name', 'neovim', 'deps', 'ssh', 
'ssh_client', 'user', 'x11', 'cwd', 'git_clone', 'pixi', 'fzf', 'lazygit']
found /home/ags/renv/blooop/bencher-main/bencher.deps.yaml
{'apt_tools': ['git', 'git-lfs', 'python3-pip', 'jq'], 'pip_language-toolchain': 
['uv', 'pip', 'pre-commit']}
key:apt_tools val:git
key:apt_tools val:git-lfs
key:apt_tools val:python3-pip
key:apt_tools val:jq
key:pip_language-toolchain val:uv
key:pip_language-toolchain val:pip
key:pip_language-toolchain val:pre-commit
empy_snippet # INSTALLING APT DEPS: @layer_name
RUN apt-get update && apt-get install -y --no-install-recommends \
    @[for x in data_list]@
    @x \
    @[end for]@
    && apt-get clean && rm -rf /var/lib/apt/lists/*

empy_data {'data_list': ['git', 'git-lfs', 'jq', 'python3-pip'], 'filename': 
'apt_tools', 'layer_name': 'tools'}
empy_snippet # INSTALLING PIP DEPS: @layer_name
RUN pip3 install -U \
@[for x in data_list]@
    @x \
@[end for]@
    && echo "pip"

empy_data {'data_list': ['pip', 'pre-commit', 'uv'], 'filename': 
'pip_language-toolchain', 'layer_name': 'language-toolchain'}
WARNING:root:lazygit
WARNING:root:pixi
WARNING:root:fzf
Writing dockerfile to /tmp/tmpaiuuc_ip/Dockerfile
vvvvvv
# Preamble from extension [curl]

# Preamble from extension [git]

# Preamble from extension [hostname]

# Preamble from extension [name]

# Preamble from extension [neovim]

# Preamble from extension [deps]

# Preamble from extension [ssh]

# Preamble from extension [ssh_client]

# Preamble from extension [user]

# Preamble from extension [x11]

# Preamble from extension [cwd]

# Preamble from extension [git_clone]

# Preamble from extension [pixi]

# Preamble from extension [fzf]

# Preamble from extension [lazygit]


FROM ubuntu:22.04
USER root
# Snippet from extension [curl]
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
# Snippet from extension [git]

# Snippet from extension [hostname]

# Snippet from extension [name]

# Snippet from extension [neovim]
RUN apt-get update && apt-get install -y --no-install-recommends \
    neovim \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
# Snippet from extension [deps]
# INSTALLING APT DEPS: tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        git-lfs \
        jq \
        python3-pip \
        && apt-get clean && rm -rf /var/lib/apt/lists/*

# INSTALLING PIP DEPS: language-toolchain
RUN pip3 install -U \
    pip \
    pre-commit \
    uv \
    && echo "pip"

# Snippet from extension [ssh]

# Snippet from extension [ssh_client]
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
# Snippet from extension [user]
# make sure sudo is installed to be able to give user sudo access in docker
RUN if ! command -v sudo >/dev/null; then \
      apt-get update \
      && apt-get install -y sudo \
      && apt-get clean; \
    fi

RUN existing_user_by_uid=`getent passwd "1000" | cut -f1 -d: || true` && \
    if [ -n "${existing_user_by_uid}" ]; then userdel -r "${existing_user_by_uid}"; 
fi && \
    existing_user_by_name=`getent passwd "ags" | cut -f1 -d: || true` && \
    existing_user_uid=`getent passwd "ags" | cut -f3 -d: || true` && \
    if [ -n "${existing_user_by_name}" ]; then find / -uid ${existing_user_uid} 
-exec chown -h 1000 {} + || true ; find / -gid ${existing_user_uid} -exec chgrp -h 
1000 {} + || true ; fi && \
    if [ -n "${existing_user_by_name}" ]; then userdel -r 
"${existing_user_by_name}"; fi && \
    existing_group_by_gid=`getent group "1000" | cut -f1 -d: || true` && \
    if [ -z "${existing_group_by_gid}" ]; then \
      groupadd -g "1000" "ags"; \
    fi && \
    useradd --no-log-init --no-create-home --uid "1000" -s /bin/bash -c "Austin" -g 
"1000" -d "/home/ags" "ags" && \
    echo "ags ALL=NOPASSWD: ALL" >> /etc/sudoers.d/rocker

# Making sure a home directory exists if we haven't mounted the user's home 
directory explicitly
RUN mkdir -p "$(dirname "/home/ags")" && mkhomedir_helper ags
WORKDIR /home/ags

# Snippet from extension [x11]

# Snippet from extension [cwd]

# Snippet from extension [git_clone]
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
# Snippet from extension [pixi]

# Snippet from extension [fzf]

# Snippet from extension [lazygit]
RUN LAZYGIT_VERSION=$(curl -s 
"https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | grep -Po 
'"tag_name": "v\K[^"]*') \
&& echo "Lazygit version: ${LAZYGIT_VERSION}" \
&& curl -Lo lazygit.tar.gz -L "https://github.com/jesseduffield/lazygit/releases/dow
nload/v${LAZYGIT_VERSION}/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz" \
&& ls -lh lazygit.tar.gz \
&& tar -xzf lazygit.tar.gz lazygit \
&& install lazygit /usr/local/bin \
&& rm lazygit.tar.gz lazygit

USER ags
# User Snippet from extension [curl]

# User Snippet from extension [git]

# User Snippet from extension [hostname]

# User Snippet from extension [name]

# User Snippet from extension [neovim]

# User Snippet from extension [deps]

# User Snippet from extension [ssh]

# User Snippet from extension [ssh_client]

# User Snippet from extension [user]

# User Snippet from extension [x11]

# User Snippet from extension [cwd]

# User Snippet from extension [git_clone]

# User Snippet from extension [pixi]
RUN curl -fsSL https://pixi.sh/install.sh | bash
RUN echo 'export PATH="$HOME/.pixi/bin:$PATH"' >> ~/.bashrc
RUN echo 'eval "$(pixi completion --shell bash)"' >> ~/.bashrc

# User Snippet from extension [fzf]
# Install fzf from source as apt is very out of date
RUN git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf;  ~/.fzf/install 
--all

# User Snippet from extension [lazygit]


^^^^^^
Getting files
adding file pyproject_default, True
apt_tools
pip_language-toolchain
Writing to file /tmp/tmpaiuuc_ip/pyproject_default
Building docker file with arguments:  {'path': '/tmp/tmpaiuuc_ip', 'rm': True, 
'nocache': False, 'pull': True}
building > Step 1/18 : FROM ubuntu:22.04
building >  ---> 392fa14dddd0
building > Step 2/18 : USER root
building >  ---> Using cache
building >  ---> 4667c897f27d
building > Step 3/18 : RUN apt-get update && apt-get install -y 
--no-install-recommends     curl     ca-certificates     && apt-get clean && rm -rf 
/var/lib/apt/lists/*
building >  ---> Using cache
building >  ---> 5ae8dfc15517
building > Step 4/18 : RUN apt-get update && apt-get install -y 
--no-install-recommends     neovim     && apt-get clean && rm -rf 
/var/lib/apt/lists/*
building >  ---> Using cache
building >  ---> 0470f69da077
building > Step 5/18 : RUN apt-get update && apt-get install -y 
--no-install-recommends         git         git-lfs         jq         python3-pip  
       && apt-get clean && rm -rf /var/lib/apt/lists/*
building >  ---> Using cache
building >  ---> 075f5787c93e
building > Step 6/18 : RUN pip3 install -U     pip     pre-commit     uv     && echo
 "pip"
building >  ---> Using cache
building >  ---> c98a3c3abe8d
building > Step 7/18 : RUN apt-get update && apt-get install -y 
--no-install-recommends     openssh-client     && apt-get clean && rm -rf 
/var/lib/apt/lists/*
building >  ---> Using cache
building >  ---> 86230f8be80e
building > Step 8/18 : RUN if ! command -v sudo >/dev/null; then       apt-get 
update       && apt-get install -y sudo       && apt-get clean;     fi
building >  ---> Using cache
building >  ---> 877b6ae3bcf2
building > Step 9/18 : RUN existing_user_by_uid=`getent passwd "1000" | cut -f1 -d: 
|| true` &&     if [ -n "${existing_user_by_uid}" ]; then userdel -r 
"${existing_user_by_uid}"; fi &&     existing_user_by_name=`getent passwd "ags" | 
cut -f1 -d: || true` &&     existing_user_uid=`getent passwd "ags" | cut -f3 -d: || 
true` &&     if [ -n "${existing_user_by_name}" ]; then find / -uid 
${existing_user_uid} -exec chown -h 1000 {} + || true ; find / -gid 
${existing_user_uid} -exec chgrp -h 1000 {} + || true ; fi &&     if [ -n 
"${existing_user_by_name}" ]; then userdel -r "${existing_user_by_name}"; fi &&     
existing_group_by_gid=`getent group "1000" | cut -f1 -d: || true` &&     if [ -z 
"${existing_group_by_gid}" ]; then       groupadd -g "1000" "ags";     fi &&     
useradd --no-log-init --no-create-home --uid "1000" -s /bin/bash -c "Austin" -g 
"1000" -d "/home/ags" "ags" &&     echo "ags ALL=NOPASSWD: ALL" >> 
/etc/sudoers.d/rocker
building >  ---> Using cache
building >  ---> a309a2cc51fe
building > Step 10/18 : RUN mkdir -p "$(dirname "/home/ags")" && mkhomedir_helper 
ags
building >  ---> Using cache
building >  ---> a68b8bec8921
building > Step 11/18 : WORKDIR /home/ags
building >  ---> Using cache
building >  ---> e650a290ef27
building > Step 12/18 : RUN apt-get update && apt-get install -y 
--no-install-recommends     git     git-lfs     ca-certificates     && apt-get clean
 && rm -rf /var/lib/apt/lists/*
building >  ---> Using cache
building >  ---> c46d34ff12df
building > Step 13/18 : RUN LAZYGIT_VERSION=$(curl -s 
"https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | grep -Po 
'"tag_name": "v\K[^"]*') && echo "Lazygit version: ${LAZYGIT_VERSION}" && curl -Lo 
lazygit.tar.gz -L "https://github.com/jesseduffield/lazygit/releases/download/v${LAZ
YGIT_VERSION}/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz" && ls -lh 
lazygit.tar.gz && tar -xzf lazygit.tar.gz lazygit && install lazygit /usr/local/bin 
&& rm lazygit.tar.gz lazygit
building >  ---> Using cache
building >  ---> ade014ed63d2
building > Step 14/18 : USER ags
building >  ---> Using cache
building >  ---> ebee1cc95873
building > Step 15/18 : RUN curl -fsSL https://pixi.sh/install.sh | bash
building >  ---> Using cache
building >  ---> b8a0e0a545e0
building > Step 16/18 : RUN echo 'export PATH="$HOME/.pixi/bin:$PATH"' >> ~/.bashrc
building >  ---> Using cache
building >  ---> b49b38779707
building > Step 17/18 : RUN echo 'eval "$(pixi completion --shell bash)"' >> 
~/.bashrc
building >  ---> Using cache
building >  ---> f8ecd5728ef4
building > Step 18/18 : RUN git clone --depth 1 https://github.com/junegunn/fzf.git 
~/.fzf;  ~/.fzf/install --all
building >  ---> Using cache
building >  ---> 43a2b00265c1
building > Successfully built 43a2b00265c1
Executing command: 
docker run --rm -it -v /etc/gitconfig:/etc/gitconfig:ro -v 
/home/ags/.gitconfig:/home/ags/.gitconfig:ro --hostname bencher-main  --name 
bencher-main  -e SSH_AUTH_SOCK -v 
/run/user/1000/keyring/ssh:/run/user/1000/keyring/ssh -v 
"/home/ags/.ssh:/home/ags/.ssh"  -e DISPLAY -e TERM   -e QT_X11_NO_MITSHM=1   -e 
XAUTHORITY=/tmp/.dockeryasdjxpb.xauth -v 
/tmp/.dockeryasdjxpb.xauth:/tmp/.dockeryasdjxpb.xauth   -v 
/tmp/.X11-unix:/tmp/.X11-unix   -v /etc/localtime:/etc/localtime:ro  -v 
/home/ags/renv/blooop/bencher-main:/bencher-main -w /bencher-main 43a2b00265c1 bash
ags@bencher-main:/bencher-main$ 
```  Fix this 
