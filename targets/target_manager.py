from args import ConfigTarget
from targets.ssh import get_ssh_connection
from targets.psexec import get_smb_connection

def create_target_connection(target:ConfigTarget):
    if target.os == 'linux':
        conn = get_ssh_connection(target)
        conn.connect()
    else:
        conn = get_smb_connection(target)
        conn.connect()
    return conn