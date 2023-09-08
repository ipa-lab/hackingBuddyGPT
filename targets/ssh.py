from fabric import Connection
from invoke import Responder

def get_ssh_connection(ip, user, password):

    if ip != '' and user != '' and password != '':
        return SSHHostConn(ip, user, password)
    else:
        raise Exception("Please configure SSH through environment variables (TARGET_IP, TARGET_USER, TARGET_PASSWORD)")

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
        self.conn.open()

    def run(self, cmd):
        gotRoot = False
        sudopass = Responder(
            pattern=r'\[sudo\] password for ' + self.username + ':',
            response=self.password + '\n',
        )
        rootdetected = Responder(
            pattern=r'^# ',
            response="hostname;id;exit; echo #IamRoot\n"
        )
        resp = self.conn.run(cmd, pty=True, warn=True, watchers=[sudopass,rootdetected])
        tmp = resp.stdout
        if 'IamRoot' in tmp:
            gotRoot = True
        return tmp.replace('[sudo] password for ' + self.username + ':', '').strip(), gotRoot
