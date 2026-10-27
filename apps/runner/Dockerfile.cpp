FROM gcc:12.2.0-bookworm
WORKDIR /tmp
USER nobody:nogroup
CMD ["sleep", "infinity"]
