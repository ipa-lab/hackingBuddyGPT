from pypsexec.client import Client

def get_smb_connection(ip, hostname, username, password):
    return SMBHostConn(ip, hostname, username, password)

# read https://pypi.org/project/pypsexec/
#  - TODO: why is timeout not working?
class SMBHostConn:

    def __init__(self, host, hostname, username, password):
        self.host = host
        self.hostname = hostname
        self.username = username
        self.password = password

    def connect(self):
        self.client = Client(self.host, username=self.username, password=self.password)
        self.client.connect()
        self.client.create_service()

    def run(self, cmd):
        stdout, stderr, rc = self.client.run_executable("cmd.exe",
                                          arguments=f"/c {cmd}", timeout_seconds=2)
        return str(stdout), False