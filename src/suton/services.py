import os
import shutil

import paramiko
from suton.ssh_client import SutonSSHClient


class DockerService(object):

    def __init__(self, host, name, pre_run_hooks=None):
        self.name = name
        self.pre_run_hooks = pre_run_hooks
        self.host = host

    def __str__(self):
        return self.name

    def _upload_via_ssh(self, base_dir, source, dest):
        ssh_client = None
        if self.host:
            ssh_client = SutonSSHClient(self.host)
        for dirpath, dirnames, filenames in os.walk(source):
            for conf in filenames:
                print("Uploading to configuration folder '{}': {}".format(dest, conf))
                full_path = os.path.join(dirpath, conf)
                conf_path = os.path.relpath(dirpath, source)
                remote_dest_path = f'{base_dir}/configs/{dest}/{conf_path}/{conf}'
                if ssh_client:
                    ssh_client.upload_file_via_ssh(full_path, remote_dest_path)
                else:
                    abs_path = os.path.abspath(remote_dest_path)
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    # local machine, just copy
                    shutil.copy2(full_path, abs_path)

    def prepare(self):
        pass


class TonControlService(DockerService):

    def __init__(self, host, configs_dir, remote_work_dir):
        super().__init__(host, 'toncontrol')
        self.configs_dir = configs_dir
        self.remote_work_dir = remote_work_dir
        self.host = host

    def prepare(self):
        logstash_folder = os.path.join(self.configs_dir, 'logstash')
        if os.path.exists(logstash_folder):
            self._upload_via_ssh(self.remote_work_dir, logstash_folder, 'logstash')
        keys_folder = os.path.join(self.configs_dir, 'keys')
        if os.path.exists(keys_folder):
            self._upload_via_ssh(self.remote_work_dir, keys_folder, 'keys')
