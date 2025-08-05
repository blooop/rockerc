# Install pixi as the wtd user if user exists, otherwise as root
RUN if id wtd >/dev/null 2>&1; then \
        su - wtd -c "curl -fsSL https://pixi.sh/install.sh | bash"; \
    else \
        curl -fsSL https://pixi.sh/install.sh | bash; \
    fi
# Add pixi to PATH for both root and wtd user
ENV PATH="/root/.pixi/bin:/home/wtd/.pixi/bin:$PATH"