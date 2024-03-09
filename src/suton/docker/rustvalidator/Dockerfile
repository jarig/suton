FROM ubuntu:18.04 as build

# Node
ARG TON_NODE_GITHUB_REPO=https://github.com/tonlabs/ever-node
ARG TON_NODE_GITHUB_COMMIT_ID=master
# Tools
# ARG TON_NODE_TOOLS_GITHUB_REPO=https://github.com/tonlabs/ever-node-tools
# ARG TON_NODE_TOOLS_GITHUB_COMMIT_ID=master
# Tonos CLI
ARG TONOS_CLI_GITHUB_REPO=https://github.com/tonlabs/ever-cli
ARG TONOS_CLI_GITHUB_COMMIT_ID=master

# https://github.com/tonlabs/ever-node/blob/master/recomended_rust
ARG RUST_VERSION=1.76.0
ARG RUST_VERSION_TONOS=1.76.0

# Compile
ENV TZ=Etc/UTC
ENV PATH="/root/.cargo/bin:${PATH}"
#ENV RUST_BACKTRACE=1


RUN apt-get update && apt-get install -y curl gnupg2 && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN echo "deb [arch=amd64] http://archive.ubuntu.com/ubuntu/ focal main restricted universe multiverse" >> /etc/apt/sources.list;\
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 871920D1991BC93C;\
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32;\
    apt-get update && apt-get install -y \
    gpg \
    tar \
    cmake \
    build-essential \
    pkg-config \
    libssl-dev \
    libtool \
    m4 \
    automake \
    clang \
    git \
    libzstd-dev \
    libgoogle-perftools-dev \
    sudo

ENV ZSTD_LIB_DIR=/usr/lib/x86_64-linux-gnu

# rdkafka from confluent's repo
RUN curl https://packages.confluent.io/deb/5.5/archive.key | apt-key add;\
    echo "deb [arch=amd64] https://packages.confluent.io/deb/5.5 stable main" >> /etc/apt/sources.list;\
    apt-get update;\
    apt-get install -y librdkafka-dev;

# Prepare
RUN mkdir -p /opt/freeton/build
WORKDIR /opt/freeton/build

RUN git clone --recursive "$TON_NODE_GITHUB_REPO" ton-node
RUN cd ton-node && git checkout --recurse-submodules "$TON_NODE_GITHUB_COMMIT_ID" && git log -1

# RUN git clone --recursive "$TON_NODE_TOOLS_GITHUB_REPO" ton-labs-node-tools
# RUN cd "ton-labs-node-tools" && git checkout "$TON_NODE_TOOLS_GITHUB_COMMIT_ID"
# RUN cd "ton-labs-node-tools" && git submodule init && git submodule update --recursive
# RUN cd "ton-labs-node-tools" && git submodule foreach 'git submodule init'
# RUN cd "ton-labs-node-tools" && git submodule foreach 'git submodule update  --recursive'

RUN git clone --recursive "$TONOS_CLI_GITHUB_REPO" tonos-cli
RUN cd "tonos-cli" && git checkout --recurse-submodules "$TONOS_CLI_GITHUB_COMMIT_ID" && git log -1


# Get Rust
COPY rust_install.sh /tmp/rust_install.sh
RUN bash -c "/tmp/rust_install.sh $RUST_VERSION"

WORKDIR /opt/freeton/build/ton-node
RUN cargo update && cargo build --release

# WORKDIR /opt/freeton/build/ton-labs-node-tools
# RUN cargo update && cargo build --release

RUN bash -c "/tmp/rust_install.sh $RUST_VERSION_TONOS"
WORKDIR /opt/freeton/build/tonos-cli
RUN cargo update && cargo build --release

# Execute
FROM ubuntu:18.04

ARG HOST_TON_USER_ID=1000
ARG HOST_TON_GROUP_ID=1000
ARG RUST_VERSION=1.76.0

ENV TZ=Europe/Tallinn

RUN apt-get update && apt-get install -y curl gnupg2
RUN curl https://packages.confluent.io/deb/5.5/archive.key | apt-key add
RUN echo "deb [arch=amd64] https://packages.confluent.io/deb/5.5 stable main" >> /etc/apt/sources.list
RUN echo "deb [arch=amd64] http://archive.ubuntu.com/ubuntu/ focal main restricted universe multiverse" >> /etc/apt/sources.list;\
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 871920D1991BC93C;\
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32;\
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone;\
    apt-get update && apt-get install -y \
    librdkafka1 \
    build-essential \
    cmake \
    cron \
    git \
    gdb \
    gpg \
    jq \
    tar \
    vim \
    tcpdump \
    netcat \
    python3 \
    python3-pip \
    wget \
    libzstd-dev \
    libgoogle-perftools-dev \
    sudo

RUN groupadd --gid "$HOST_TON_GROUP_ID" ton \
    && useradd --uid "$HOST_TON_USER_ID" --gid "$HOST_TON_USER_ID" --create-home --shell /bin/bash ton && \
    echo "ton ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
	mkdir /opt/freeton/ && \
	chown ton:ton /opt/freeton/

ENV ZSTD_LIB_DIR=/usr/lib/x86_64-linux-gnu

# Get Rust
COPY rust_install.sh /tmp/rust_install.sh
RUN bash -c "/tmp/rust_install.sh $RUST_VERSION"

RUN mkdir -p /ton-node
RUN chown ton:ton /ton-node

USER ton

COPY --chown=ton:ton --from=build /opt/freeton/build/ton-node/target/release/ton_node /ton-node/ton_node_no_kafka_compression
COPY --chown=ton:ton --from=build /opt/freeton/build/ton-node/target/release/console /ton-node/tools/
COPY --chown=ton:ton --from=build /opt/freeton/build/ton-node/target/release/keygen /ton-node/tools/
COPY --chown=ton:ton --from=build /opt/freeton/build/tonos-cli/target/release/tonos-cli /ton-node/tools/

COPY --chown=ton:ton configs/* /ton-node/configs/

COPY --chown=ton:ton entry.sh /ton-node/scripts/

ENTRYPOINT ["/ton-node/scripts/entry.sh"]