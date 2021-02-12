#!/bin/bash -eE

export TON_NODE_ROOT_DIR="/ton-node"
export TON_NODE_DB_DIR="${TON_NODE_ROOT_DIR}/node_db"
export TON_NODE_CONFIGS_DIR="${TON_NODE_ROOT_DIR}/configs"
export TON_NODE_TOOLS_DIR="${TON_NODE_ROOT_DIR}/tools"
export TON_NODE_LOGS_DIR="${TON_NODE_ROOT_DIR}/logs"
export STATSD_DOMAIN=localhost:
export STATSD_PORT=9125
RNODE_CONSOLE_SERVER_PORT="3031"
NODE_EXEC_NAME="ton_node_no_kafka_compression"
NODE_EXEC="${TON_NODE_ROOT_DIR}/$NODE_EXEC_NAME"

# /ton-node is mount point. Then we create subfolder, so in case of env-switch container shouldn't be re-created
TON_NODE_ENV_ROOT_DIR="/ton-node-work/$TON_ENV"
TON_NODE_ENV_TOOLS_DIR="${TON_NODE_ENV_ROOT_DIR}/tools"
TON_NODE_ENV_DB_DIR="${TON_NODE_ENV_ROOT_DIR}/node_db"
TON_NODE_ENV_LOGS_DIR="${TON_NODE_ENV_ROOT_DIR}/logs"
TON_CONSOLE_KEYS_ROOT=/var/rton-console-keys-${TON_ENV}  # shared docker volume

echo "INFO: R-Node startup..."

echo "INFO: NETWORK_TYPE = ${NETWORK_TYPE}"
echo "INFO: TON_ENV = ${TON_ENV}"
echo "INFO: DEPLOY_TYPE = ${DEPLOY_TYPE}"
echo "INFO: CONFIGS_PATH = ${CONFIGS_PATH}"


echo "INFO: Starting TON node..."
#
if [[ ! -f "$TON_CONSOLE_KEYS_ROOT/client" || ! -f "$TON_NODE_CONFIGS_DIR/config.json" || ! -d "$TON_NODE_ENV_DB_DIR/db" ]]; then
  mkdir -p "$TON_NODE_ENV_ROOT_DIR"
  mkdir -p "$TON_CONSOLE_KEYS_ROOT"
  mkdir -p "$TON_NODE_ENV_LOGS_DIR"
  mkdir -p "$TON_NODE_ENV_TOOLS_DIR"
  echo "INFO: Initializing TON work folder for '$TON_ENV' environment"
  # prepare ton-env workspace

  cp -Rf $TON_NODE_TOOLS_DIR/* "$TON_NODE_ENV_TOOLS_DIR/"

  TMP_DIR="/tmp/rust_conf"
  rm -rf "${TMP_DIR}"
  mkdir -p "${TMP_DIR}"
  ls -al ${TON_NODE_CONFIGS_DIR}
  if [[ -f "$TON_NODE_CONFIGS_DIR/config.json" ]]; then
    rm "$TON_NODE_CONFIGS_DIR/config.json"
  fi

  # create console config
  "${TON_NODE_TOOLS_DIR}/keygen" >"${TON_NODE_CONFIGS_DIR}/console_client_keys.json"
  # cat "${TON_NODE_CONFIGS_DIR}/console_client_keys.json"
  console_public=$(jq -c .public "${TON_NODE_CONFIGS_DIR}/console_client_keys.json")

  echo "Public console key: $console_public"

  jq ".control_server_ip_port = \"${RNODE_CONSOLE_SERVER_PORT}\"" "${TON_NODE_CONFIGS_DIR}/default_config.json" >"${TMP_DIR}/default_config.json.tmp"
  cp "${TMP_DIR}/default_config.json.tmp" "${TON_NODE_CONFIGS_DIR}/default_config.json"

  # Generate initial config.json
  cd "${TON_NODE_ENV_ROOT_DIR}" && "${NODE_EXEC}" --configs "${TON_NODE_CONFIGS_DIR}" --ckey "$console_public" &
  ton_pid=$!
  sleep 10

  if [ ! -f "${TON_NODE_CONFIGS_DIR}/config.json" ]; then
      echo "ERROR: ${TON_NODE_CONFIGS_DIR}/config.json does not exist"
      exit 1
  fi

  # cat "${TON_NODE_CONFIGS_DIR}/config.json"

  if [ ! -f "${TON_NODE_CONFIGS_DIR}/console_config.json" ]; then
      echo "ERROR: ${TON_NODE_CONFIGS_DIR}/console_config.json does not exist"
      exit 1
  fi

  # kill any dangling ones
  kill $ton_pid || true
  while kill -0 $ton_pid; do
    sleep 1
  done

  jq ".control_server.address = \"0.0.0.0:${RNODE_CONSOLE_SERVER_PORT}\"" "${TON_NODE_CONFIGS_DIR}/config.json" >"${TMP_DIR}/config.json.tmp"
  cp "${TMP_DIR}/config.json.tmp" "${TON_NODE_CONFIGS_DIR}/config.json"

  # cat "${TON_NODE_CONFIGS_DIR}/console_config.json"
  jq -r ".private.pvt_key" "${TON_NODE_CONFIGS_DIR}/console_client_keys.json" > "${TMP_DIR}/client"
  jq -r ".public.pub_key" "${TON_NODE_CONFIGS_DIR}/console_client_keys.json" > "${TMP_DIR}/client.pub"
  jq -r ".server_key.pub_key" "${TON_NODE_CONFIGS_DIR}/console_config.json" > "${TMP_DIR}/server.pub"
  sudo cp -f "${TMP_DIR}/client" "${TON_CONSOLE_KEYS_ROOT}/client"
  sudo cp -f "${TMP_DIR}/client.pub" "${TON_CONSOLE_KEYS_ROOT}/client.pub"
  sudo cp -f "${TMP_DIR}/server.pub" "${TON_CONSOLE_KEYS_ROOT}/server.pub"

  # cleanup
  rm -f "${TON_NODE_CONFIGS_DIR}/console_config.json"
  rm -rf "${TMP_DIR}"

  # prepare keys
  echo "INFO: Copying client keys..."
  # setup keys for local-controller client (to shared docker volume)
  # client private key
  sudo chmod o+xr $TON_CONSOLE_KEYS_ROOT/*
  echo "INFO: Granting ownership permissions for client private key to $HOST_TON_CONTROL_USER_ID:$HOST_TON_CONTROL_GROUP_ID"
  sudo chown $HOST_TON_CONTROL_USER_ID:$HOST_TON_CONTROL_GROUP_ID "$TON_CONSOLE_KEYS_ROOT/client"
fi



wget "$TON_VALIDATOR_CONFIG_URL" -O "${TON_NODE_CONFIGS_DIR}/ton-global.config.json"

cd "${TON_NODE_ENV_ROOT_DIR}"

#tail -f /dev/null
# shellcheck disable=SC2086
exec $NODE_EXEC --configs "${TON_NODE_CONFIGS_DIR}" ${TON_NODE_EXTRA_ARGS} # >>${TON_NODE_LOGS_DIR}/output.log 2>&1