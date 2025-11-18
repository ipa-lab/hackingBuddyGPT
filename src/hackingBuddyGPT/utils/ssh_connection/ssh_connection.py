from dataclasses import dataclass
from typing import Optional, Tuple

import invoke
from fabric import Connection

from hackingBuddyGPT.utils.configurable import configurable, parameter


@configurable("ssh", "connects to a remote host via SSH")
@dataclass
class SSHConnection:
    host: str
    username: str
    password: str
    hostname: str = ""
    keyfilename: str = ""
    port: int = 22

    _conn: Connection = None
    banner: str = ""

    def init(self):
        # create the SSH Connection
        if self.keyfilename == "":
            conn = Connection(
                f"{self.username}@{self.host}:{self.port}",
                connect_kwargs={"password": self.password, "look_for_keys": False, "allow_agent": False},
            )
        else:
            conn = Connection(
                f"{self.username}@{self.host}:{self.port}",
                connect_kwargs={
                    "password": self.password,
                    "key_filename": self.keyfilename,
                    "look_for_keys": False,
                    "allow_agent": False,
                },
            )
        self._conn = conn
        self._conn.open()

        if self.banner == "":
            try:
                t = self._conn.transport
                b = t.get_banner() if t else None
                if not b and t:
                    b = getattr(t, "remote_version", "") or ""
                if isinstance(b, bytes):
                    b = b.decode("utf-8", "ignore")
                self.banner = b or ""
            except Exception:
                pass

    def new_with(
        self, *, host=None, hostname=None, username=None, password=None, keyfilename=None, port=None
    ) -> "SSHConnection":
        return SSHConnection(
            host=host or self.host,
            hostname=hostname or self.hostname,
            username=username or self.username,
            password=password or self.password,
            keyfilename=keyfilename or self.keyfilename,
            port=port or self.port,
        )

    def run(self, cmd, *args, **kwargs) -> Tuple[str, str, int]:
        res: Optional[invoke.Result] = self._conn.run(cmd, *args, **kwargs)
        return res.stdout, res.stderr, res.return_code
