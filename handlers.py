import dataclasses
import paramiko
import re

from targets.ssh import SSHHostConn

def handle_cmd(conn, input):
    result, gotRoot = conn.run(input)
    return input, result, gotRoot


def handle_ssh(target, input):
    cmd_parts = input.split(" ")
    assert(cmd_parts[0] == "test_credentials")

    if len(cmd_parts) != 3:
        return input, "didn't provide username/password", False

    test_target = dataclasses.replace(target, user=cmd_parts[1], password=cmd_parts[2])
    test = SSHHostConn(test_target)
    try:
        test.connect()
        user = test.run("whoami")[0].strip('\n\r ')
        if user == "root":
            return input, "Login as root was successful\n", True
        else:
            return input, "Authentication successful, but user is not root\n", False

    except paramiko.ssh_exception.AuthenticationException:
        return input, "Authentication error, credentials are wrong\n", False
    
