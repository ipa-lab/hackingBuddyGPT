from dataclasses import dataclass
from typing import Tuple

from pypsexec.client import Client

from hackingBuddyGPT.utils.configurable import configurable


@configurable("psexec", "connects to a remote host via PSExec")
@dataclass
class PSExecConnection:
    host: str
    hostname: str
    username: str
    password: str
    port: int = 445

    _conn: Client = None

    def init(self):
        self._conn = Client(self.host, username=self.username, password=self.password, port=self.port)
        self._conn.connect()
        self._conn.create_service()

    def new_with(self, *, host=None, hostname=None, username=None, password=None, port=None) -> "PSExecConnection":
        return PSExecConnection(
            host=host or self.host,
            hostname=hostname or self.hostname,
            username=username or self.username,
            password=password or self.password,
            port=port or self.port,
        )

    def run(self, cmd) -> Tuple[str, str, int]:
        stdout, stderr, rc = self._conn.run_executable("cmd.exe", arguments=f"/c {cmd}", timeout_seconds=2)
        return str(stdout), str(stderr), rc
