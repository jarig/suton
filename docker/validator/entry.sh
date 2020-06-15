#!/bin/bash -eE

# Copyright 2020 TON DEV SOLUTIONS LTD.
#
# Licensed under the SOFTWARE EVALUATION License (the "License"); you may not use
# this file except in compliance with the License.  You may obtain a copy of the
# License at:
#
# https://www.ton.dev/licenses
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific TON DEV software governing permissions and limitations
# under the License.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=env.sh
. "${SCRIPT_DIR}/env.sh"

# get arguments
TON_ENV_WORK_DIR=$TON_WORK_DIR-$TON_ENV/$TON_ENV
TON_CLIENT_KEYS_ROOT=/var/ton-client-keys-${TON_ENV}  # shared docker volume
TON_ENV_GLOBAL_CONFIG=${TON_ENV_WORK_DIR}/etc/ton-global.config.json
TON_DB_ROOT=${TON_ENV_WORK_DIR}/db
TON_LOG_ROOT=${TON_ENV_WORK_DIR}/log
TON_ENV_LOCAL_CONFIG=${TON_DB_ROOT}/config.json


# Initialize
echo "INFO: Starting TON node..."
if [[ ! -d "$TON_ENV_WORK_DIR" || ! -d "$TON_CLIENT_KEYS_ROOT" ]]; then
  mkdir -p $TON_ENV_WORK_DIR
  mkdir -p $TON_CLIENT_KEYS_ROOT
  mkdir -p $TON_LOG_ROOT
  echo "INFO: Initializing TON work folder for '$TON_ENV' environment"
  # Copy defaults from container to mount
  cp -R $TON_WORK_DIR/* $TON_ENV_WORK_DIR/
  sudo chown "ton:ton" "${TON_ENV_WORK_DIR}"
  # remove local config file, to update it according to the env set and global config
  rm -f $TON_ENV_GLOBAL_CONFIG
  rm -f $TON_ENV_LOCAL_CONFIG
  chmod g+r $TON_LOG_ROOT
  echo "INFO: Copying client keys..."
  # setup keys for local-controller client (to shared docker volume)
  sudo cp ${KEYS_DIR}/client $TON_CLIENT_KEYS_ROOT/
  sudo cp ${KEYS_DIR}/client.pub $TON_CLIENT_KEYS_ROOT/
  sudo cp ${KEYS_DIR}/server.pub $TON_CLIENT_KEYS_ROOT/
  sudo cp ${KEYS_DIR}/liteserver.pub $TON_CLIENT_KEYS_ROOT/
  sudo chmod o+xr $TON_CLIENT_KEYS_ROOT/*.pub
  echo "INFO: Granting ownership permissions for client private key to $HOST_TON_CONTROL_USER_ID:$HOST_TON_CONTROL_GROUP_ID"
  sudo chown $HOST_TON_CONTROL_USER_ID:$HOST_TON_CONTROL_GROUP_ID $TON_CLIENT_KEYS_ROOT/client
fi

if [[ ! -f "$TON_ENV_LOCAL_CONFIG" ]]; then
  if [[ ! -z "$TON_VALIDATOR_CONFIG_URL" ]]; then
    config_url=$TON_VALIDATOR_CONFIG_URL
  else
    if [[ -z "$TON_ENV" || "$TON_ENV" == "main.ton.dev" ]]
    then
      config_url=https://ton.org/ton-global.config.json
    elif [[ "$TON_ENV" == "net.ton.dev" ]]
    then
      config_url=https://test.ton.org/ton-global.config.json
    else
      echo "ERROR: Don't know what config to download for ton ENV $TON_ENV, use TON_VALIDATOR_CONFIG_URL environment variable to specify the config URL."
      exit 1
    fi
  fi
  echo "INFO: Downloading global configuration file: $config_url"
  rm -f "$TON_ENV_GLOBAL_CONFIG"
  wget $config_url -O "$TON_ENV_GLOBAL_CONFIG"

  echo "INFO: Getting my public IP..."
  MY_ADDR="$(curl https://ipinfo.io/ip)":${ADNL_PORT}
  echo "INFO: MY_ADDR = ${MY_ADDR}"

  # generate local configuration
  echo "INFO: Generating local configuration from $config_url"
  "${TON_BUILD_DIR}/validator-engine/validator-engine" -C "${TON_ENV_GLOBAL_CONFIG}" --ip "${MY_ADDR}" --db "${TON_DB_ROOT}" -l "${TON_LOG_ROOT}/validator.log"
  # Update local config with appropriate keys
  server_pub_id=$(awk '{print $2}' "${KEYS_DIR}/keys_s")
  client_pub_id=$(awk '{print $2}' "${KEYS_DIR}/keys_c")
  liteserver_pub_id=$(awk '{print $2}' "${KEYS_DIR}/keys_l")
  jq '.control[0] = {"id": "'$server_pub_id'", "port": 3030, "allowed": []}' "$TON_ENV_LOCAL_CONFIG" > "$TON_ENV_LOCAL_CONFIG.tmp"
  jq '.control[0].allowed[0] = {"id": "'$client_pub_id'", "permissions": 15}' "$TON_ENV_LOCAL_CONFIG.tmp" > "$TON_ENV_LOCAL_CONFIG"
  cp -f "$TON_ENV_LOCAL_CONFIG" "$TON_ENV_LOCAL_CONFIG.tmp"
  jq '.liteservers[0] = {"id": "'$liteserver_pub_id'", "port": 3031}' "$TON_ENV_LOCAL_CONFIG.tmp" > "$TON_ENV_LOCAL_CONFIG"
fi

echo "INFO: Running validator engine"
"${TON_BUILD_DIR}/validator-engine/validator-engine" -C "${TON_ENV_GLOBAL_CONFIG}" --db "${TON_DB_ROOT}" -l "${TON_LOG_ROOT}/validator.log"

echo "INFO: start TON node... DONE"
