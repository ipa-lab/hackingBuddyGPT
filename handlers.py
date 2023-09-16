import paramiko

from targets.ssh import SSHHostConn

def handle_cmd(conn, input):
    result, gotRoot = conn.run(input["cmd"])
    return input["cmd"], result, gotRoot


def handle_ssh(target_host, target_hostname, input):
    user = input["username"]
    password = input["password"]

    cmd = f"tried ssh with username {user} and password {password}\n"

    test = SSHHostConn(target_host, target_hostname, user, password)
    try:
        test.connect()
        user = test.run("whoami")

        if user == "root":
            return cmd, "Login as root was successful\n"
        else:
            return cmd, "Authentication successful, but user is not root\n"

    except paramiko.ssh_exception.AuthenticationException:
        return cmd, "Authentication error, credentials are wrong\n"