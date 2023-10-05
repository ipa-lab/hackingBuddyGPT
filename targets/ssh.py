import re

from args import ConfigTarget
from fabric import Connection
from invoke import Responder
from io import StringIO

GOT_ROOT_REXEXPs = [
    re.compile("^# $"),
    re.compile("^bash-[0-9]+.[0-9]# $")
]

class SSHHostConn:

    def __init__(self, target):
        self.host = target.ip
        self.hostname = target.hostname
        self.username = target.user
        self.password = target.password

    def connect(self):
        # create the SSH Connection
        conn = Connection(
            "{username}@{ip}:{port}".format(
                username=self.username,
                ip=self.host,
                port=22),
            connect_kwargs={"password": self.password, "look_for_keys": False, "allow_agent": False},
        )
        self.conn=conn
        self.conn.open()

    def run(self, cmd):
        gotRoot = False
        sudopass = Responder(
            pattern=r'\[sudo\] password for ' + self.username + ':',
            response=self.password + '\n',
        )
        
        out = StringIO()
        try:
            resp = self.conn.run(cmd, pty=True, warn=True, out_stream=out, watchers=[sudopass], timeout=10)
        except Exception as e:
            print("TIMEOUT! Could we have become root?")
        out.seek(0)
        tmp = ""
        lastline = ""
        for line in out.readlines():
            if not line.startswith('[sudo] password for ' + self.username + ':'):
                line = line.replace("\r", "")
                lastline = line
                tmp = tmp + line

        # remove ansi shell codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        lastline = ansi_escape.sub('', lastline)

        for i in GOT_ROOT_REXEXPs:
            if i.fullmatch(lastline):
                gotRoot = True
        if lastline.startswith(f'root@{self.hostname}:'):
            gotRoot = True
        return tmp, gotRoot

def get_ssh_connection(target:ConfigTarget) -> SSHHostConn:

    if target.ip != '' and target.user != '' and target.password != '' and target.hostname != '':
        return SSHHostConn(target)
    else:
        raise Exception("Please configure SSH through environment variables (TARGET_IP, TARGET_USER, TARGET_PASSWORD)")
