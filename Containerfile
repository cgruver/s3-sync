FROM registry.access.redhat.com/ubi9/ubi:latest

RUN dnf -y install python3.11-pip && \
    dnf -y clean all && \
    python3.11 -m pip install --no-cache-dir diskless-s3-sync

USER 1001

VOLUME ["/etc/s3-sync/config.toml"]

ENTRYPOINT ["/usr/local/bin/s3-sync"]
CMD []
