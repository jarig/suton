import os

import paramiko


class SutonSSHClient(object):

    def __init__(self, hostname, username=None, password=None):
        hostname, parsed_username, parsed_password = SutonSSHClient.parse_ssh_hostname(hostname)
        self.hostname = hostname
        self.username = username if username else parsed_username
        self.password = password if password else parsed_password

    @staticmethod
    def parse_ssh_hostname(hostname):
        username = None
        password = None
        if hostname.startswith('ssh://'):
            tokens = hostname.replace('ssh://', '').split('@')
            if len(tokens) > 1:
                creds_tokens = tokens[0].split(":")
                if len(creds_tokens) > 1:
                    username = creds_tokens[0]
                    password = creds_tokens[1]
                else:
                    username = creds_tokens[0]
                hostname = tokens[1]
        return hostname, username, password

    def upload_file_via_ssh(self, source, dest, perms=None):
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=self.hostname, username=self.username, password=self.password)
        ssh_client.exec_command('mkdir -p {}'.format(os.path.dirname(dest)))
        ftp_client = ssh_client.open_sftp()
        ftp_client.put(source, dest)
        ftp_client.close()
        if perms:
            ssh_client.exec_command('chmod -R {} {}'.format(perms, dest))

