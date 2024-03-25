import dataclasses
import paramiko
from typing import Dict, List, Union

from targets.ssh import SSHHostConn

# run a command on a remote host over SSH
class SshQueryCredentialsCapability:
    # NOTE: hopefully two hierarchy levels are enough for config
    def __init__(self, config: Dict[str, Union[str, Dict[str, str]]]):
        self.config = config
        self.conn = SSHHostConn(config)

    def name(self) -> str:
        return "ssh_query_credentials"

    # provide customized description
    def describe(self) -> str:
        return f"verify user credentials on host {self.config["hostname"]}. To perform this, give credentials to be tested by stating `{self.name()} username password`" 

    # open the remote connection
    def configure(self):
        pass

    # execute the task
    # TODO: introduce a return type
    def execute(self, input: str) -> List[str]:

        cmd_parts = input.split(" ")
        assert(cmd_parts[0] == self.name())

        if len(cmd_parts) != 3:
            return input, "didn't provide username/password", False

        test_target = dataclasses.replace(self.conn, user=cmd_parts[1], password=cmd_parts[2])
        test = SSHHostConn(test_target)
        try:
            test.connect()
            user = test.run("whoami")[0].strip('\n\r ')
            if user == "root":
                return input, "Login as root was successful\n"
            else:
                return input, "Authentication successful, but user is not root\n"

        except paramiko.ssh_exception.AuthenticationException:
            return input, "Authentication error, credentials are wrong\n", False