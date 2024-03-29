#!/bin/bash -eE


if [[ ! -z "$TON_CONTROL_QUEUE_PROVIDER_PIP_PACKAGE" ]]
then
  python3.7 -m pip install $TON_CONTROL_QUEUE_PROVIDER_PIP_PACKAGE
fi

if [[ ! -z "$TON_CONTROL_SECRET_MANAGER_PROVIDER_PIP_PACKAGE" ]]
then
  python3.7 -m pip install $TON_CONTROL_SECRET_MANAGER_PROVIDER_PIP_PACKAGE
fi

work_base_dir="/var/ton-control"
control_key_pick_up_dir="$work_base_dir/configs/keys"
work_dir="$work_base_dir/${TON_ENV}"
sudo mkdir -p "$work_dir"
sudo chown toncontrol:toncontrol -R "$work_dir"

keys_dir="/var/ton-control-keys/${TON_ENV}"

# Pickup toncontrol encryption keys
sudo mkdir -p "$keys_dir"
if [[ -d "$control_key_pick_up_dir" && -n "$(ls -A $control_key_pick_up_dir)" ]]; then
  echo "Copying keys to toncontrol keys volume..."
  sudo cp -f $control_key_pick_up_dir/* "$keys_dir/"
  echo "Available keys:"
  ls "$keys_dir"
  # remove them now from the host machine
  sudo rm "$control_key_pick_up_dir/"* || true
fi

sudo chown toncontrol:toncontrol -R "$keys_dir"
sudo mkdir -p "$work_dir/log"
sudo chown toncontrol:toncontrol "$work_dir/log"

tool_cwds_root="/opt/cwds"
sudo mkdir -p "$tool_cwds_root"
sudo chown toncontrol:toncontrol -R "$tool_cwds_root"



args="--work_dir=$work_dir --log_path=$work_dir/log --keys_dir=$keys_dir"
args="$args --tools_cwd_base=$tool_cwds_root"
args="$args --secret_manager_connection_env=TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING"
args="$args --tonos_cli_wallet_abi_url=$TON_CONTROL_WALLET_ABI_URL --tonos_cli_wallet_tvc_url=$TON_CONTROL_WALLET_TVC_URL"

add_argument () {
  name=$1
  value=$2
  noValue=$3

  if [[ -n $value ]]
  then
    if [[ -n $noValue ]]
    then
      args="$args --$name"
    else
      args="$args --$name=$value"
    fi
  fi
}

add_argument "rconsole_path" $TON_RCONSOLE_PATH
add_argument "default_election_stake" $TON_CONTROL_DEFAULT_STAKE
add_argument "stake_max_factor" $TON_CONTROL_STAKE_MAX_FACTOR
add_argument "fift_includes" $FIFT_INCLUDES
add_argument "queue_name" $TON_CONTROL_QUEUE_NAME
add_argument "queue_provider" $TON_CONTROL_QUEUE_PROVIDER_IMPORT_PATH
add_argument "secret_manager_provider" $TON_CONTROL_SECRET_MANAGER_IMPORT_PATH
add_argument "validator_network_address" $TON_CONTROL_VALIDATOR_NETWORK_ADDR
add_argument "lite_client_network_address" $TON_CONTROL_VALIDATOR_LITE_CLIENT_ADDR
add_argument "client_key" $TON_CONTROL_CLIENT_KEY_PATH
add_argument "server_pub_key" $TON_CONTROL_SERVER_PUB_KEY_PATH
add_argument "lite_server_pub_key" $TON_CONTROL_LITE_SERVER_PUB_KEY_PATH

echo "./main.py $args"
python3.7 ./main.py $args


