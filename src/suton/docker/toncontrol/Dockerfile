FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

ARG HOST_TON_CONTROL_USER_ID=1002
ARG HOST_TON_CONTROL_GROUP_ID=1002

RUN apt-get update && \
    apt-get install --no-install-recommends -y libreadline7 python3.7 ca-certificates sudo python3-pip git && \
    groupadd --gid "$HOST_TON_CONTROL_USER_ID" toncontrol \
    && useradd --uid "$HOST_TON_CONTROL_GROUP_ID" --gid "$HOST_TON_CONTROL_GROUP_ID" --create-home --shell /bin/bash toncontrol && \
    echo "toncontrol ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

RUN echo "deb [arch=amd64] http://archive.ubuntu.com/ubuntu/ focal main restricted universe multiverse" >> /etc/apt/sources.list;\
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 871920D1991BC93C;\
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32;\
    apt-get update && apt-get install -y \
    gpg \
    tar \
    build-essential \
    libzstd-dev

RUN python3.7 -m pip install --upgrade pip

COPY --chown=toncontrol:toncontrol --from=tonvalidator:latest /ton-node/tools /opt/ton/tools

WORKDIR /tmp

ADD ./toncontrol /opt/toncontrol
# TODO: Remove once libs are moved to own repos
ADD ./tonlibs /opt/tonlibs

RUN mkdir -p /opt/toncontrol
RUN chown toncontrol:toncontrol /opt/toncontrol/

USER toncontrol
WORKDIR /opt/toncontrol
RUN python3.7 -m pip install -r requirements.txt

COPY ./docker/toncontrol/entry.sh .
RUN sudo chmod 755 entry.sh

ENV TON_CONTROL_QUEUE_PROVIDER_PIP_PACKAGE=""
ENV TON_CONTROL_QUEUE_PROVIDER_IMPORT_PATH=""
ENV TON_CONTROL_SECRET_MANAGER_PROVIDER_PIP_PACKAGE=""
ENV TON_CONTROL_SECRET_MANAGER_IMPORT_PATH=""
ENV TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING=""
ENV TON_CONTROL_DEFAULT_STAKE="30%"
ENV TON_CONTROL_ELECTION_MODE=""
ENV TON_CONTROL_SETTINGS=""
ENV TON_CONTROL_STAKE_MAX_FACTOR="3"
ENV TON_CONTROL_QUEUE_NAME=node-0
ENV TON_CONTROL_VALIDATOR_NETWORK_ADDR=tonvalidator:3030
ENV TON_CONTROL_VALIDATOR_LITE_CLIENT_ADDR=tonvalidator:3031
ENV TON_CONTROL_WALLET_ABI_URL=https://raw.githubusercontent.com/tonlabs/ton-labs-contracts/master/solidity/safemultisig/SafeMultisigWallet.abi.json
ENV TON_CONTROL_WALLET_TVC_URL=https://github.com/tonlabs/ton-labs-contracts/raw/master/solidity/safemultisig/SafeMultisigWallet.tvc
ENV FIFT_INCLUDES=/opt/ton/fift-libs/libs:/opt/ton/fift-libs/smartcont

# Run Ton Control
ENTRYPOINT ["./entry.sh"]