FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

ARG HOST_TON_CONTROL_USER_ID=1002
ARG HOST_TON_CONTROL_GROUP_ID=1002

RUN apt-get update && \
    apt-get install --no-install-recommends -y libreadline7 python3.7 ca-certificates sudo python3-pip git && \
    groupadd --gid "$HOST_TON_CONTROL_USER_ID" toncontrol \
    && useradd --uid "$HOST_TON_CONTROL_GROUP_ID" --gid "$HOST_TON_CONTROL_GROUP_ID" --create-home --shell /bin/bash toncontrol && \
    echo "toncontrol ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

COPY --chown=toncontrol:toncontrol --from=tonvalidator:latest /opt/freeton/main.ton.dev/ton/build/lite-client /opt/ton/lite-client
COPY --chown=toncontrol:toncontrol --from=tonvalidator:latest /opt/freeton/main.ton.dev/ton/build/validator-engine-console /opt/ton/validator-engine-console
COPY --chown=toncontrol:toncontrol --from=tonvalidator:latest /opt/freeton/main.ton.dev/ton/build/utils /opt/ton/utils
COPY --chown=toncontrol:toncontrol --from=tonvalidator:latest /opt/freeton/main.ton.dev/ton/build/crypto /opt/ton/crypto
COPY --chown=toncontrol:toncontrol --from=tonvalidator:latest /opt/freeton/main.ton.dev/ton/crypto/fift/lib /opt/ton/fift-libs/libs
COPY --chown=toncontrol:toncontrol --from=tonvalidator:latest /opt/freeton/main.ton.dev/ton/crypto/smartcont /opt/ton/fift-libs/smartcont
COPY --chown=toncontrol:toncontrol --from=tonvalidator:latest /opt/freeton/main.ton.dev/configs /opt/ton/configs


WORKDIR /tmp

ADD ./toncontrol /opt/toncontrol
# TODO: Remove once libs are moved to own repos
ADD ./tonlibs /opt/tonlibs

RUN mkdir -p /opt/toncontrol
RUN chown toncontrol:toncontrol /opt/toncontrol/

USER toncontrol
WORKDIR /opt/toncontrol
RUN pip3 install -r requirements.txt

COPY ./docker/toncontrol/entry.sh .
RUN sudo chmod 755 entry.sh

ENV TON_CONTROL_QUEUE_PROVIDER_PIP_PACKAGE=""
ENV TON_CONTROL_QUEUE_PROVIDER_IMPORT_PATH=""
ENV TON_CONTROL_SECRET_MANAGER_PROVIDER_PIP_PACKAGE=""
ENV TON_CONTROL_SECRET_MANAGER_IMPORT_PATH=""
ENV TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING=""
ENV TON_CONTROL_DEFAULT_STAKE="30%"
ENV TON_CONTROL_STAKE_MAX_FACTOR="3"
ENV TONOS_CLI_CONFIG_URL=https://$TON_ENV
ENV TON_CONTROL_QUEUE_NAME=node-0
ENV TON_VALIDATOR_NETWORK_ADDR=tonvalidator:3030
ENV TON_CONTROL_ABI_PATH=/opt/ton/configs/SafeMultisigWallet.abi.json
ENV TON_CONTROL_TVC_PATH=/opt/ton/configs/SafeMultisigWallet.tvc
ENV FIFT_INCLUDES=/opt/ton/fift-libs/libs:/opt/ton/fift-libs/smartcont

# Run Ton Control
ENTRYPOINT ["./entry.sh"]