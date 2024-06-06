import invoke
from dataclasses import dataclass
from fabric import Connection
from typing import Optional, Tuple

from hackingBuddyGPT.utils.configurable import configurable


@configurable("ssh", "connects to a remote host via SSH")
@dataclass
class SSHConnection:
    host: str
    hostname: str
    username: str
    password: str
    port: int = 22

    _conn: Connection = None

    def init(self):
        # create the SSH Connection
        conn = Connection(
            f"{self.username}@{self.host}:{self.port}",
            connect_kwargs={"password": self.password, "look_for_keys": False, "allow_agent": False},
        )
        self._conn = conn
        self._conn.open()

    def new_with(self, *, host=None, hostname=None, username=None, password=None, port=None) -> "SSHConnection":
        return SSHConnection(
            host=host or self.host,
            hostname=hostname or self.hostname,
            username=username or self.username,
            password=password or self.password,
            port=port or self.port,
        )

    def run(self, cmd, *args, **kwargs) -> Tuple[str, str, int]:
        res: Optional[invoke.Result] = self._conn.run(cmd, *args, **kwargs)
        return res.stdout, res.stderr, res.return_code
