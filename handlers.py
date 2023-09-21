import dataclasses
import paramiko

from targets.ssh import SSHHostConn

def handle_cmd(conn, input):
    cmd = cmd_output_fixer(input)
    result, gotRoot = conn.run(cmd)
    return cmd, result, gotRoot


def handle_ssh(target, input):
    cmd_parts = input.split(" ")
    assert(cmd_parts[0] == "test_credentials")

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
    

def remove_wrapping_characters(cmd, wrappers):
    if cmd[0] == cmd[-1] and cmd[0] in wrappers:
        print("will remove a wrapper from: " + cmd)
        return remove_wrapping_characters(cmd[1:-1], wrappers)
    return cmd

# often the LLM produces a wrapped command
def cmd_output_fixer(cmd):
    cmd = remove_wrapping_characters(cmd, "`'\"")

    if cmd.startswith("$ "):
        cmd = cmd[2:]
    
    return cmd