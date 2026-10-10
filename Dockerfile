# AIStack — the image that runs AIStack (ADR-0017 § 2, 1.8).
#
# One image for every process: the web application and the five
# collectors are services of `docker-compose.yml`, each running this
# image with a different command (see `docker/entrypoint.sh`).
#
# The `docker` client, copied as a single static binary from Docker's
# own image, is how AIStack observes and throttles the host's
# containers through the mounted socket; `lm-sensors` and
# `openssh-client` are the two other host commands it runs.
FROM docker:27-cli AS docker-cli

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# The declarations live outside the image (ADR-0017 § 1); the
# entrypoint fills this directory on every start, never overwriting.
ENV AISTACK_CONFIG_DIR=/config
ENV HOME=/tmp

RUN apt-get update \
    && apt-get install -y --no-install-recommends lm-sensors openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY docker/entrypoint.sh /usr/local/bin/aistack-entrypoint
RUN chmod 0755 /usr/local/bin/aistack-entrypoint \
    && mkdir -p /config /app/reports/generated \
    && chmod 0777 /config /app/reports/generated

ENTRYPOINT ["aistack-entrypoint"]
CMD ["web"]
