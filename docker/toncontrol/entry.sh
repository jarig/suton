#!/bin/bash -eE


if [[ ! -z "$TON_CONTROL_QUEUE_PROVIDER_PIP_PACKAGE" ]]
then
  pip3 install $TON_CONTROL_QUEUE_PROVIDER_PIP_PACKAGE
fi

if [[ ! -z "$TON_CONTROL_SECRET_MANAGER_PROVIDER_PIP_PACKAGE" ]]
then
  pip3 install $TON_CONTROL_SECRET_MANAGER_PROVIDER_PIP_PACKAGE
fi

sudo mkdir -p /var/ton-control-keys
if [[ -d "/var/ton-control/keys" && -n "$(ls -A /var/ton-control/keys)" ]]; then
  echo "Moving keys to toncontrol keys volume..."
  sudo mv -f /var/ton-control/keys/* /var/ton-control-keys/
  echo "Available keys:"
  ls /var/ton-control-keys/
fi

sudo chown toncontrol:toncontrol -R /var/ton-control-keys/
sudo mkdir -p "/var/ton-control/log"
sudo chown toncontrol:toncontrol "/var/ton-control/log"

sudo mkdir -p "/var/ton-control/tonos_cwd"
sudo chown toncontrol:toncontrol -R "/var/ton-control/tonos_cwd"


args="--log_path=/var/ton-control/log --queue_name=$TON_CONTROL_QUEUE_NAME --keys_dir=/var/ton-control-keys"
args="$args --tonos_cli_cwd=/var/ton-control/tonos_cwd"
args="$args --secret_manager_connection_env=TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING"
args="$args --tonos_cli_abi_path=$TON_CONTROL_ABI_PATH --tonos_cli_tvc_path=$TON_CONTROL_TVC_PATH"

if [[ ! -z $FIFT_INCLUDES ]]
then
  args="$args --fift_includes=$FIFT_INCLUDES"
fi

if [[ ! -z $TONOS_CLI_CONFIG_URL ]]
then
  args="$args --tonos_config_url=$TONOS_CLI_CONFIG_URL"
fi

if [[ ! -z $TON_CONTROL_QUEUE_PROVIDER_IMPORT_PATH ]]
then
  args="$args --queue_provider=$TON_CONTROL_QUEUE_PROVIDER_IMPORT_PATH"
fi

if [[ ! -z $TON_CONTROL_SECRET_MANAGER_IMPORT_PATH ]]
then
  args="$args --secret_manager_provider=$TON_CONTROL_SECRET_MANAGER_IMPORT_PATH"
fi

if [[ ! -z $TON_VALIDATOR_NETWORK_ADDR ]]
then
  args="$args --validator_network_address=$TON_VALIDATOR_NETWORK_ADDR"
fi

echo "./main.py $args"
python3 ./main.py $args

