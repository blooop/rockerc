# Install pixi as the worktree_docker user if user exists, otherwise as root
RUN if id worktree_docker >/dev/null 2>&1; then \
        su - worktree_docker -c "curl -fsSL https://pixi.sh/install.sh | bash"; \
    else \
        curl -fsSL https://pixi.sh/install.sh | bash; \
    fi
# Add pixi to PATH for both root and worktree_docker user
ENV PATH="/root/.pixi/bin:/home/worktree_docker/.pixi/bin:$PATH"