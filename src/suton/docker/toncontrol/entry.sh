#!/bin/bash -eE


if [[ ! -z "$TON_CONTROL_QUEUE_PROVIDER_PIP_PACKAGE" ]]
then
  pip3 install $TON_CONTROL_QUEUE_PROVIDER_PIP_PACKAGE
fi

if [[ ! -z "$TON_CONTROL_SECRET_MANAGER_PROVIDER_PIP_PACKAGE" ]]
then
  pip3 install $TON_CONTROL_SECRET_MANAGER_PROVIDER_PIP_PACKAGE
fi

work_dir="/var/ton-control/${TON_ENV}"
sudo mkdir -p "$work_dir"
sudo chown toncontrol:toncontrol -R "$work_dir"

keys_dir="/var/ton-control-keys/${TON_ENV}"
sudo mkdir -p "$keys_dir"
if [[ -d "$work_dir/keys" && -n "$(ls -A $work_dir/keys)" ]]; then
  echo "Moving keys to toncontrol keys volume..."
  sudo mv -f $work_dir/keys/* "$keys_dir/"
  echo "Available keys:"
  ls $keys_dir
fi

sudo chown toncontrol:toncontrol -R "$keys_dir"
sudo mkdir -p "$work_dir/log"
sudo chown toncontrol:toncontrol "$work_dir/log"

sudo mkdir -p "$work_dir/tonos_cwd"
sudo chown toncontrol:toncontrol -R "$work_dir/tonos_cwd"


args="--work_dir=$work_dir --log_path=$work_dir/log --queue_name=$TON_CONTROL_QUEUE_NAME --keys_dir=$keys_dir"
args="$args --tonos_cli_cwd=$work_dir/tonos_cwd"
args="$args --secret_manager_connection_env=TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING"
args="$args --tonos_cli_abi_path=$TON_CONTROL_ABI_PATH --tonos_cli_tvc_path=$TON_CONTROL_TVC_PATH"

if [[ ! -z $TON_CONTROL_DEFAULT_STAKE ]]
then
  args="$args --default_election_stake=$TON_CONTROL_DEFAULT_STAKE"
fi

if [[ ! -z $TON_CONTROL_STAKE_MAX_FACTOR ]]
then
  args="$args --stake_max_factor=$TON_CONTROL_STAKE_MAX_FACTOR"
fi

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


