import paramiko

from targets.ssh import SSHHostConn

def handle_cmd(conn, input):
    result, gotRoot = conn.run(input["cmd"])
    return input["cmd"], result, gotRoot


def handle_ssh(target_host, target_hostname, input):
    user = input["username"]
    password = input["password"]

    cmd = f"test_credentials {user} {password}\n"

    test = SSHHostConn(target_host, target_hostname, user, password)
    try:
        test.connect()
        user = test.run("whoami")[0].strip('\n\r ')
        if user == "root":
            return cmd, "Login as root was successful\n", True
        else:
            return cmd, "Authentication successful, but user is not root\n", False

    except paramiko.ssh_exception.AuthenticationException:
        return cmd, "Authentication error, credentials are wrong\n", False