from typing import Dict, List, Union

from targets.ssh import SSHHostConn

# run a command on a remote host over SSH
class SshCmdRunCapability:
    # NOTE: hopefully two hierarchy levels are enough for config
    def __init__(self, config: Dict[str, Union[str, Dict[str, str]]]):
        self.config = config
        self.conn = SSHHostConn(config)

    def name(self) -> str:
        return "ssh_run_cmd"

    # provide customized description
    def describe(self) -> str:
        return f"Execute a command on the remote host {self.config["host"]} as user {self.config["username"]} over SSH. You can give it an command and will retrieve the result of that command when executed on the remote host."

    # open the remote connection
    def configure(self):
        self.conn.connect()

    # execute the task
    # TODO: introduce a return type
    def execute(self, arg: str) -> List[str]:
        result, gotRoot = sonn.run(arg)
        return result, gotRoot