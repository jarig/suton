import argparse
import importlib
import json
import os
import subprocess
import sys


sys.path.append(os.path.join(os.path.dirname(__file__), 'toncontrol'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tonlibs'))

from typing import List
from suton.services import DockerService, TonControlService
from suton.toncontrol.settings.core import TonSettings


class TonManage(object):

    def init_services(self, node_settings: TonSettings) -> List[DockerService]:
        # order matters
        return [
            DockerService(host=node_settings.DOCKER_HOST, name='tonvalidator'),
            TonControlService(host=node_settings.DOCKER_HOST,
                              configs_dir=node_settings.CONFIGS_DIR,
                              remote_work_dir=node_settings.TON_CONTROL_WORK_DIR),
            DockerService(host=node_settings.DOCKER_HOST, name='tonlogstash'),
        ]

    def get_node_settings(self, settings_path="") -> TonSettings:
        mod = importlib.import_module("{}.settings".format(settings_path))
        settings = mod.NodeSettings()
        if not settings.CONFIGS_DIR:
            settings.CONFIGS_DIR = os.path.join(os.path.dirname(mod.__file__), 'configs')
        return settings

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
        proc = subprocess.run(args, cwd=cwd, env=env)
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
        node_settings.init()
        node_settings.validate()
        cenv = os.environ.copy()
        connection_string = node_settings.TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING
        if isinstance(connection_string, dict):
            connection_string = json.dumps(connection_string)
        cenv['TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING'] = connection_string
        if node_settings.DOCKER_HOST:
            cenv['DOCKER_HOST'] = node_settings.DOCKER_HOST
        cenv['TON_WORK_DIR'] = node_settings.TON_WORK_DIR

        cenv['RUST_TONOS_CLI_GITHUB_COMMIT_ID'] = node_settings.RUST_TONOS_CLI_GITHUB_COMMIT_ID
        cenv['RUST_TON_NODE_GITHUB_COMMIT_ID'] = node_settings.RUST_TON_NODE_GITHUB_COMMIT_ID
        cenv['RUST_TON_NODE_GITHUB_REPO'] = node_settings.RUST_TON_NODE_GITHUB_REPO

        cenv['TON_CONTROL_WORK_DIR'] = node_settings.TON_CONTROL_WORK_DIR
        cenv['TON_CONTROL_SETTINGS'] = json.dumps(node_settings.to_json())

        if node_settings.TON_ENV:
            cenv['TON_ENV'] = node_settings.TON_ENV

        if node_settings.TON_VALIDATOR_CONFIG_URL:
            cenv['TON_VALIDATOR_CONFIG_URL'] = node_settings.TON_VALIDATOR_CONFIG_URL

        if node_settings.ELECTIONS_SETTINGS.TON_CONTROL_DEFAULT_STAKE:
            cenv['TON_CONTROL_DEFAULT_STAKE'] = node_settings.ELECTIONS_SETTINGS.TON_CONTROL_DEFAULT_STAKE
        if node_settings.ELECTIONS_SETTINGS.TON_CONTROL_STAKE_MAX_FACTOR:
            cenv['TON_CONTROL_STAKE_MAX_FACTOR'] = node_settings.ELECTIONS_SETTINGS.TON_CONTROL_STAKE_MAX_FACTOR

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

        if node_settings.ELECTIONS_SETTINGS.TON_CONTROL_ELECTION_MODE:
            cenv['TON_CONTROL_ELECTION_MODE'] = str(node_settings.ELECTIONS_SETTINGS.TON_CONTROL_ELECTION_MODE)

        self.pre_execute(node_settings)

        if args.parser_name == "docker":
            self._execute(['docker-compose'] + args.docker_args,
                          env=cenv,
                          cwd=self._get_path('docker'))
        elif args.parser_name == "run":
            available_services = self.init_services(node_settings)
            services_to_run = available_services
            if args.service:
                for service in available_services:
                    if service.name == args.service:
                        services_to_run = [service]
                        break
                if not services_to_run:
                    raise Exception("Specified not supported service: {}, available services: {}".format(args.service,
                                                                                                         available_services))
            # run services
            for service in services_to_run:
                docker_args = ["up"]
                if not args.attach:
                    docker_args.append("-d")
                if args.build:
                    docker_args.append("--build")
                docker_args.append(service.name)
                print("Preparing service: {}".format(service.name))
                service.prepare()
                self._execute(['docker-compose'] + docker_args,
                              env=cenv,
                              cwd=self._get_path('docker'))

