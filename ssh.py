from fabric import Connection
from invoke import Responder

class SSHHostConn:

    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password

    def connect(self):
        # create the SSH Connection
        conn = Connection(
            "{username}@{ip}:{port}".format(
                username=self.username,
                ip=self.host,
                port=22,
            ),
            connect_kwargs={"password": self.password},
        )
        self.conn=conn

    def run(self, cmd):
        sudopass = Responder(
            pattern=r'\[sudo\] password for ' + self.username + ':',
            response=self.password + '\n',
        )
        resp = self.conn.run(cmd, pty=True, warn=True, watchers=[sudopass])
        tmp = resp.stdout
        return tmp.replace('[sudo] password for ' + self.username + ':', '').strip()
