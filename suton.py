import argparse
import importlib
import json
import os
import subprocess
import sys


class TonSettings(object):
    # Intended to be overriden and values set to appropriate values
    # Note: do not commit sensitive data, and instead use Python to derive them in run-time from secure places
    NODE_NAME = os.path.basename(os.path.dirname(__file__))

    # DOCKER_HOST parameter, ex: ssh://root@1.1.1.1
    DOCKER_HOST = None
    TON_WORK_DIR = None
    TON_ENV = "net.ton.dev"
    TON_CONTROL_WORK_DIR = None
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = None  # never commit your raw seeds, encrypt them or use connection-strings to vaults
    TON_VALIDATOR_CONFIG_URL = None  # optionally specify where from to take config

    def validate(self):
        if self.TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING is None:
            raise Exception("You need to set secret-manager connection string value")


class TonManage(object):

    def get_settings(self, settings_path=""):
        mod = importlib.import_module("{}.settings".format(settings_path))
        return mod.NodeSettings()

    def extra_args(self, parser):
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
            settings = self.get_settings(args.node)
        else:
            settings = self.get_settings()
        settings.validate()
        cenv = os.environ.copy()
        connection_string = settings.TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING
        if isinstance(connection_string, dict):
            connection_string = json.dumps(connection_string)
        cenv['TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING'] = connection_string
        if settings.DOCKER_HOST:
            cenv['DOCKER_HOST'] = settings.DOCKER_HOST
        cenv['TON_WORK_DIR'] = settings.TON_WORK_DIR
        cenv['TON_CONTROL_WORK_DIR'] = settings.TON_CONTROL_WORK_DIR
        if settings.TON_ENV:
            cenv['TON_ENV'] = settings.TON_ENV
        if settings.TON_VALIDATOR_CONFIG_URL:
            cenv['TON_VALIDATOR_CONFIG_URL'] = settings.TON_VALIDATOR_CONFIG_URL

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



