FROM ubuntu:18.04 as builder

ARG TON_SCRIPTS_REV=master
ARG HOST_USER_UID=1000
ARG HOST_USER_GID=1000
ENV DEBIAN_FRONTEND=noninteractive
ENV CMAKE_BUILD_PARALLEL_LEVEL=2

RUN set -ex && \
    apt-get update && \
    apt-get install --no-install-recommends -y curl cargo ninja-build sudo ca-certificates build-essential cmake clang openssl libssl-dev zlib1g-dev gperf wget git && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid "$HOST_USER_GID" ton \
    && useradd --uid "$HOST_USER_UID" --gid "$HOST_USER_GID" --create-home --shell /bin/bash ton && \
    echo "ton ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
	mkdir /opt/freeton/ && \
	chown ton:ton /opt/freeton/

USER ton
WORKDIR /opt/freeton/
RUN git clone --depth 1 --recursive https://github.com/tonlabs/main.ton.dev.git
RUN cd /opt/freeton/main.ton.dev && git fetch origin $TON_SCRIPTS_REV && git checkout -f $TON_SCRIPTS_REV
WORKDIR /opt/freeton/main.ton.dev/scripts/
RUN ./env.sh && ./build.sh


FROM ubuntu:18.04

ARG TON_CONTROL_PORT=3030
ARG HOST_TON_USER_ID=1001
ARG HOST_TON_GROUP_ID=1001
ENV DEBIAN_FRONTEND=noninteractive

RUN set -ex && \
    apt-get update && \
    apt-get install --no-install-recommends -y libreadline7 curl sudo ca-certificates wget jq && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid "$HOST_TON_GROUP_ID" ton \
    && useradd --uid "$HOST_TON_USER_ID" --gid "$HOST_TON_GROUP_ID" --create-home --shell /bin/bash ton && \
    echo "ton ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
	mkdir /opt/freeton/ && \
	chown ton:ton /opt/freeton/

COPY --chown=ton:ton --from=builder /opt/freeton/main.ton.dev /opt/freeton/main.ton.dev
USER ton
WORKDIR /opt/freeton/main.ton.dev/scripts/
RUN ./setup.sh
COPY entry.sh .
RUN sudo chmod 755 entry.sh

ENV TON_ENV="net.ton.dev"
ENV TON_VALIDATOR_CONFIG_URL=""
ENV HOST_TON_CONTROL_USER_ID=$HOST_TON_CONTROL_USER_ID
ENV HOST_TON_CONTROL_GROUP_ID=$HOST_TON_CONTROL_GROUP_ID

ENTRYPOINT ["./entry.sh"]
