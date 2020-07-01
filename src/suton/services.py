import os

import paramiko
from suton.ssh_client import SutonSSHClient


class DockerService(object):

    def __init__(self, host, name, pre_run_hooks=None):
        self.name = name
        self.pre_run_hooks = pre_run_hooks

    def __str__(self):
        return self.name

    def prepare(self):
        pass


class TonControlService(DockerService):

    def __init__(self, host, configs_dir, remote_work_dir):
        super().__init__(host, 'toncontrol')
        self.configs_dir = configs_dir
        self.remote_work_dir = remote_work_dir
        self.host = host
        self.ssh_client = SutonSSHClient(host)

    def prepare(self):
        logstash_folder = os.path.join(self.configs_dir, 'logstash')
        if os.path.exists(logstash_folder):
            for conf in os.listdir(logstash_folder):
                print("Uploading logstash configuration: {}".format(conf))
                conf_path = os.path.join(logstash_folder, conf)
                remote_dest_path = '{}/{}/{}/{}'.format(self.remote_work_dir, 'configs', 'logstash', conf)
                self.ssh_client.upload_file_via_ssh(conf_path, remote_dest_path)

