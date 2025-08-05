ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} wtd && \
    useradd -u ${USER_ID} -g wtd -m -s /bin/bash wtd && \
    echo 'wtd ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER wtd
WORKDIR /workspace