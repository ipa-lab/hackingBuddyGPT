from targets.ssh import get_ssh_connection
from targets.psexec import get_smb_connection

def create_target_connection(args):
    if args.target_os == 'linux':
        # open SSH connection to target
        conn = get_ssh_connection(args.target_ip, args.target_hostname, args.target_user, args.target_password)
        conn.connect()
    else:
        conn = get_smb_connection(args.target_ip, args.target_hostname, args.target_user, args.target_password)
        conn.connect()
    return conn