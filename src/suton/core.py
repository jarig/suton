import argparse
import importlib
import json
import os
import subprocess
import sys


class TonSettings(object):
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

    def validate(self):
        if self.TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING is None:
            raise Exception("You need to set secret-manager connection string value")


class TonManage(object):

    def get_node_settings(self, settings_path="") -> TonSettings:
        mod = importlib.import_module("{}.settings".format(settings_path))
        return mod.NodeSettings()

    def extra_args(self, parser):
        pass

    def pre_execute(self, node_settings: TonSettings):
        """
        Hook that is called before main docker command is executed.
        For example you can transfer some files via ssh (ex logstash configs or keys) before image starts.
        """
        pass

    def _execute(self, args, cwd, env=None, timeout=None):
        print("Running {} in {}".format(args, cwd))
        proc = subprocess.run(args, cwd=cwd, env=env, shell=True)
        return proc.returncode
    
    def _get_path(self, folder):
        return os.path.join(os.path.dirname(__file__), folder)

    def main(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--node", default=None, help="Node name")
        docker_subparsers = parser.add_subparsers(dest="parser_name")
        run_parser = docker_subparsers.add_parser('run')
        run_parser.add_argument('--build', action='store_true', default=False, help='Build Docker containers')
        run_parser.add_argument('--service', default=None, help='Specify service to run')
        run_parser.add_argument('--attach', default=False, action='store_true', help='Attach after run')
        docker_parser = docker_subparsers.add_parser('docker')
        docker_parser.add_help = False
        docker_parser.add_argument('docker_args', metavar='arguments', type=str, nargs=argparse.REMAINDER,
                                   help='args to docker-compose')
        self.extra_args(parser)
        if sys.argv[1] == "docker":
            args, _ = parser.parse_known_args()
            args.docker_args = sys.argv[2:]
        else:
            args = parser.parse_args()
        if args.node:
            # load settings
            node_settings = self.get_node_settings(args.node)
        else:
            node_settings = self.get_node_settings()
        node_settings.validate()
        cenv = os.environ.copy()
        connection_string = node_settings.TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING
        if isinstance(connection_string, dict):
            connection_string = json.dumps(connection_string)
        cenv['TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING'] = connection_string
        if node_settings.DOCKER_HOST:
            cenv['DOCKER_HOST'] = node_settings.DOCKER_HOST
        cenv['TON_WORK_DIR'] = node_settings.TON_WORK_DIR
        cenv['TON_CONTROL_WORK_DIR'] = node_settings.TON_CONTROL_WORK_DIR
        if node_settings.TON_ENV:
            cenv['TON_ENV'] = node_settings.TON_ENV
        if node_settings.TON_VALIDATOR_CONFIG_URL:
            cenv['TON_VALIDATOR_CONFIG_URL'] = node_settings.TON_VALIDATOR_CONFIG_URL
        if node_settings.TON_CONTROL_DEFAULT_STAKE:
            cenv['TON_CONTROL_DEFAULT_STAKE'] = node_settings.TON_CONTROL_DEFAULT_STAKE
        if node_settings.TON_CONTROL_STAKE_MAX_FACTOR:
            cenv['TON_CONTROL_STAKE_MAX_FACTOR'] = node_settings.TON_CONTROL_STAKE_MAX_FACTOR
        if node_settings.TONOS_CLI_CONFIG_URL:
            cenv['TONOS_CLI_CONFIG_URL'] = node_settings.TONOS_CLI_CONFIG_URL
        if node_settings.TON_CONTROL_QUEUE_NAME:
            cenv['TON_CONTROL_QUEUE_NAME'] = node_settings.TON_CONTROL_QUEUE_NAME
        elif node_settings.NODE_NAME:
            cenv['TON_CONTROL_QUEUE_NAME'] = "node-{}".format(node_settings.NODE_NAME)
        else:
            cenv['TON_CONTROL_QUEUE_NAME'] = "node-{}".format(args.node)

        if node_settings.TON_CONTROL_VALIDATOR_NETWORK_ADDR:
            cenv['TON_CONTROL_VALIDATOR_NETWORK_ADDR'] = node_settings.TON_CONTROL_VALIDATOR_NETWORK_ADDR

        if node_settings.TON_CONTROL_VALIDATOR_LITE_CLIENT_ADDR:
            cenv['TON_CONTROL_VALIDATOR_LITE_CLIENT_ADDR'] = node_settings.TON_CONTROL_VALIDATOR_LITE_CLIENT_ADDR

        if node_settings.TON_CONTROL_CLIENT_KEY_PATH:
            cenv['TON_CONTROL_CLIENT_KEY_PATH'] = node_settings.TON_CONTROL_CLIENT_KEY_PATH

        if node_settings.TON_CONTROL_SERVER_PUB_KEY_PATH:
            cenv['TON_CONTROL_SERVER_PUB_KEY_PATH'] = node_settings.TON_CONTROL_SERVER_PUB_KEY_PATH

        if node_settings.TON_CONTROL_LITE_SERVER_PUB_KEY_PATH:
            cenv['TON_CONTROL_LITE_SERVER_PUB_KEY_PATH'] = node_settings.TON_CONTROL_LITE_SERVER_PUB_KEY_PATH

        self.pre_execute(node_settings)

        docker_args = []
        if args.parser_name == "docker":
            docker_args = args.docker_args
        elif args.parser_name == "run":
            docker_args = ["up"]
            if not args.attach:
                docker_args.append("-d")
            if args.build:
                docker_args.append("--build")

            if args.service:
                docker_args.append(args.service)

        # run docker-compose
        self._execute(['docker-compose'] + docker_args,
                      env=cenv,
                      cwd=self._get_path('docker'))



