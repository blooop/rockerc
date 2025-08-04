ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} worktree_docker && \
    useradd -u ${USER_ID} -g worktree_docker -m -s /bin/bash worktree_docker && \
    echo 'worktree_docker ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER worktree_docker
WORKDIR /workspace