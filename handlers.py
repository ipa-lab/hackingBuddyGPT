import config
import paramiko

from targets.ssh import SSHHostConn

def handle_cmd(conn, input):
    result, gotRoot = conn.run(input["cmd"])
    return input["cmd"], result, gotRoot


def handle_ssh(input):
    user = input["username"]
    password = input["password"]

    cmd = "tried ssh with username " + user + " and password " + password

    test = SSHHostConn(config.target_ip(), user, password)
    try:
        test.connect()
        user = test.run("whoami")

        if user == "root":
            return cmd, "Login as root was successful"
        else:
            return cmd, "Authentication successful, but user is not root"

    except paramiko.ssh_exception.AuthenticationException:
        return cmd, "Authentication error, credentials are wrong"