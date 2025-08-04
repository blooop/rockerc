ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} renv && \
    useradd -u ${USER_ID} -g renv -m -s /bin/bash renv && \
    echo 'renv ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER renv
WORKDIR /workspace