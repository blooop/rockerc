# Install pixi as the renv user if user exists, otherwise as root
RUN if id renv >/dev/null 2>&1; then \
        su - renv -c "curl -fsSL https://pixi.sh/install.sh | bash"; \
    else \
        curl -fsSL https://pixi.sh/install.sh | bash; \
    fi
# Add pixi to PATH for both root and renv user
ENV PATH="/root/.pixi/bin:/home/renv/.pixi/bin:$PATH"