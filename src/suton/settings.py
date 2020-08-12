
class SettingsAbstract(object):
    CONFIGS_DIR = None

    # which scripts to use for building validator node
    TON_BUILD_SCRIPTS_URL = "https://github.com/tonlabs/main.ton.dev"
    TON_BUILD_SCRIPTS_REV = "master"

    # Intended to be overriden and values set to appropriate values
    # Note: do not commit sensitive data, and instead use Python to derive them in run-time from secure places
    NODE_NAME = None

    # DOCKER_HOST parameter, ex: ssh://root@1.1.1.1
    DOCKER_HOST = None
    TON_WORK_DIR = None
    TON_ENV = "net.ton.dev"
    TON_CONTROL_WORK_DIR = None
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = None  # never commit your raw seeds, encrypt them or use connection-strings to vaults
    TON_VALIDATOR_CONFIG_URL = None  # optionally specify where from to take config
    TON_CONTROL_DEFAULT_STAKE = None  # % or absolute value, ex 30%
    TON_CONTROL_QUEUE_NAME = None
    TONOS_CLI_CONFIG_URL = None
    TON_CONTROL_STAKE_MAX_FACTOR = None
    TON_CONTROL_VALIDATOR_NETWORK_ADDR = None
    TON_CONTROL_VALIDATOR_LITE_CLIENT_ADDR = None
    TON_CONTROL_CLIENT_KEY_PATH = None
    TON_CONTROL_SERVER_PUB_KEY_PATH = None
    TON_CONTROL_LITE_SERVER_PUB_KEY_PATH = None
    TON_CONTROL_SKIP_ELECTIONS = None

    def validate(self):
        if self.TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING is None:
            raise Exception("You need to set secret-manager connection string value")