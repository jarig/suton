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

    def _upload_confs(self, source, dest):
        for conf in os.listdir(source):
            print("Uploading to configuration folder '{}': {}".format(dest, conf))
            conf_path = os.path.join(source, conf)
            remote_dest_path = '{}/{}/{}/{}'.format(self.remote_work_dir, 'configs', dest, conf)
            self.ssh_client.upload_file_via_ssh(conf_path, remote_dest_path)

    def prepare(self):
        logstash_folder = os.path.join(self.configs_dir, 'logstash')
        if os.path.exists(logstash_folder):
            self._upload_confs(logstash_folder, 'logstash')
        keys_folder = os.path.join(self.configs_dir, 'keys')
        if os.path.exists(keys_folder):
            self._upload_confs(keys_folder, 'keys')
